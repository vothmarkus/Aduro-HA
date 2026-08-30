"""Update coordinator and confirmed command handling for Aduro Hybrid."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AduroClient, AduroError
from .const import COMMAND_REFRESH_DELAYS, DEFAULT_SCAN_INTERVAL, DOMAIN
from .model import AduroData

_LOGGER = logging.getLogger(__name__)

VerifyCallback = Callable[[AduroData], bool]


class AduroCoordinator(DataUpdateCoordinator[AduroData]):
    """Coordinate polling and serialize state confirmation after writes."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: AduroClient
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{client.serial}",
            update_interval=timedelta(
                seconds=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            always_update=False,
        )
        self.client = client

    async def _async_update_data(self) -> AduroData:
        previous = getattr(self, "data", None)
        try:
            return await self.hass.async_add_executor_job(
                self.client.fetch_data, previous
            )
        except AduroError as err:
            raise UpdateFailed(f"Error communicating with Aduro stove: {err}") from err

    async def async_command(
        self,
        path: str,
        value: str | float,
        verify: VerifyCallback | None = None,
        *,
        strict_verify: bool = True,
    ) -> None:
        """Send a command, refresh, and optionally require confirmed read-back."""
        try:
            await self.hass.async_add_executor_job(self.client.set_value, path, value)
        except AduroError as err:
            raise HomeAssistantError(f"Aduro command was rejected: {err}") from err

        last_data: AduroData | None = None
        for delay in COMMAND_REFRESH_DELAYS:
            await asyncio.sleep(delay)
            await self.async_refresh()
            if not self.last_update_success:
                continue

            last_data = self.data
            if verify is None or verify(last_data):
                return

        if last_data is None:
            raise HomeAssistantError(
                "The stove accepted the command, but Home Assistant could not "
                "refresh its state. Check the current stove state before retrying."
            )

        if not strict_verify:
            return

        raise HomeAssistantError(
            "The stove accepted the command, but its read-back value did not match "
            "the requested value. The actual stove value is shown in Home Assistant."
        )
