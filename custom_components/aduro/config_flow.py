"""Config flow for Aduro Hybrid."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.helpers import selector

from .api import (
    AduroClient,
    AduroConnectionError,
    AduroInvalidResponseError,
    AduroRejectedError,
    normalize_pin,
    normalize_serial,
)
from .const import (
    CONF_PIN,
    CONF_SERIAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
_SERIAL_PATTERN = re.compile(r"^\d{1,6}$")
_PIN_PATTERN = re.compile(r"^\d{1,10}$")


def _schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=values.get(CONF_HOST, "")): str,
            vol.Required(CONF_SERIAL, default=values.get(CONF_SERIAL, "")): str,
            vol.Required(
                CONF_PIN, default=values.get(CONF_PIN, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=values.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        }
    )


class AduroConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle an Aduro Hybrid config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup."""
        return await self._async_handle_form("user", user_input, {})

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow host, credentials, and polling interval to be changed."""
        entry = self._get_reconfigure_entry()
        return await self._async_handle_form("reconfigure", user_input, entry.data)

    async def _async_handle_form(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
        defaults: Mapping[str, Any],
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            serial_input = str(user_input[CONF_SERIAL]).strip()
            pin_input = str(user_input[CONF_PIN]).strip()

            if not host:
                errors[CONF_HOST] = "invalid_host"
            if not _SERIAL_PATTERN.fullmatch(serial_input):
                errors[CONF_SERIAL] = "invalid_serial"
            if not _PIN_PATTERN.fullmatch(pin_input):
                errors[CONF_PIN] = "invalid_pin"

            if not errors:
                normalized = {
                    CONF_HOST: host,
                    CONF_SERIAL: normalize_serial(serial_input),
                    CONF_PIN: normalize_pin(pin_input),
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                }
                client = AduroClient(host, serial_input, pin_input)
                try:
                    await self.hass.async_add_executor_job(client.validate)
                except AduroRejectedError:
                    errors["base"] = "invalid_auth"
                except AduroConnectionError:
                    errors["base"] = "cannot_connect"
                except AduroInvalidResponseError:
                    errors["base"] = "invalid_response"
                except Exception:  # defensive config-flow boundary
                    _LOGGER.exception("Unexpected error while validating Aduro stove")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(normalized[CONF_SERIAL])
                    if step_id == "reconfigure":
                        self._abort_if_unique_id_mismatch()
                        return self.async_update_reload_and_abort(
                            self._get_reconfigure_entry(), data_updates=normalized
                        )

                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=DEFAULT_NAME, data=normalized)

        schema_defaults = user_input if user_input is not None else defaults
        return self.async_show_form(
            step_id=step_id,
            data_schema=_schema(schema_defaults),
            errors=errors,
        )
