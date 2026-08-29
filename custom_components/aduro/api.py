"""Synchronous, guarded wrapper around the pyduro NBE/UDP client."""

from __future__ import annotations

import io
import logging
import re
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from threading import Lock
from typing import Any

from pyduro.actions import STATUS_PARAMS
from pyduro.actions import get as pyduro_get
from pyduro.actions import raw as pyduro_raw
from pyduro.actions import set as pyduro_set

from .const import WRITABLE_PATHS
from .model import AduroData, Value

_LOGGER = logging.getLogger(__name__)

# pyduro binds a fixed local UDP source port and is not thread-safe. A single
# process-wide lock protects both facts, including installations with >1 entry.
_PYDURO_LOCK = Lock()
_NUMBER_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_SETTING_SECTIONS = ("regulation", "boiler", "auger")
_MIN_STATUS_FIELDS = tuple(STATUS_PARAMS).index("state") + 1


class AduroError(Exception):
    """Base exception for Aduro communication."""


class AduroConnectionError(AduroError):
    """The stove did not answer or the UDP exchange failed."""


class AduroRejectedError(AduroError):
    """The stove returned a non-zero NBE status."""

    def __init__(self, status: int, payload: str) -> None:
        super().__init__(f"Stove rejected the request (NBE status {status}: {payload})")
        self.status = status
        self.payload = payload


class AduroInvalidResponseError(AduroError):
    """The response did not match the request or could not be parsed."""


class AduroClient:
    """Reliable facade for the blocking pyduro library."""

    def __init__(self, host: str, serial: str, pin: str) -> None:
        self.host = host.strip()
        self.serial = normalize_serial(serial)
        self.pin = normalize_pin(pin)
        self._last_partial_errors: tuple[str, ...] = ()

    def validate(self) -> None:
        """Verify that this stove answers a status request."""
        with _PYDURO_LOCK:
            self._status_unlocked()

    def fetch_data(self, previous: AduroData | None = None) -> AduroData:
        """Fetch one coherent snapshot; retain optional sections if unsupported."""
        with _PYDURO_LOCK:
            status = self._status_unlocked()
            settings: dict[str, dict[str, Value]] = {}
            stale_sections: set[str] = set()
            partial_errors: list[str] = []

            for section in _SETTING_SECTIONS:
                try:
                    settings[section] = self._settings_unlocked(section)
                except AduroError as err:
                    partial_errors.append(f"settings/{section}: {err}")
                    stale_sections.add(section)
                    settings[section] = (
                        dict(previous.settings.get(section, {})) if previous else {}
                    )

            try:
                counter = self._consumption_counter_unlocked()
            except AduroError as err:
                partial_errors.append(f"consumption/counter: {err}")
                stale_sections.add("consumption_counter")
                counter = previous.consumption_counter if previous else ()

        self._report_partial_errors(tuple(partial_errors))
        return AduroData(
            status=status,
            settings=settings,
            consumption_counter=counter,
            stale_sections=frozenset(stale_sections),
        )

    def set_value(self, path: str, value: str | float) -> None:
        """Write one allow-listed value and validate the direct NBE response."""
        if path not in WRITABLE_PATHS:
            raise ValueError(f"Unsupported Aduro write path: {path}")

        with _PYDURO_LOCK:
            self._request_unlocked(
                pyduro_set.run,
                self.host,
                self.serial,
                self.pin,
                path,
                value,
                expected_function=2,
            )

    def _status_unlocked(self) -> dict[str, Value]:
        response = self._request_unlocked(
            pyduro_raw.run,
            burner_address=self.host,
            serial=self.serial,
            pin_code=self.pin,
            function_id=11,
            payload="*",
            expected_function=11,
        )
        payload = getattr(response, "payload", None)
        if not isinstance(payload, str) or not payload:
            raise AduroInvalidResponseError("Status response has no payload")

        values = payload.split(",")
        keys = tuple(STATUS_PARAMS)
        if len(values) < _MIN_STATUS_FIELDS:
            raise AduroInvalidResponseError(
                "Status response is incomplete "
                f"({len(values)} fields, expected at least {_MIN_STATUS_FIELDS})"
            )

        if len(values) != len(keys):
            _LOGGER.debug(
                "Aduro status field count differs from pyduro: received %d, known %d",
                len(values),
                len(keys),
            )

        return {
            key: _coerce_value(value) for key, value in zip(keys, values, strict=False)
        }

    def _settings_unlocked(self, section: str) -> dict[str, Value]:
        response = self._request_unlocked(
            pyduro_get.run,
            burner_address=self.host,
            serial=self.serial,
            pin_code=self.pin,
            function_name="settings",
            path=f"{section}.*",
            expected_function=1,
        )
        return _parse_mapping_payload(response, f"settings/{section}")

    def _consumption_counter_unlocked(self) -> tuple[float, ...]:
        response = self._request_unlocked(
            pyduro_get.run,
            burner_address=self.host,
            serial=self.serial,
            pin_code=self.pin,
            function_name="consumption",
            path="counter",
            expected_function=6,
        )
        payload = getattr(response, "payload", None)
        if not isinstance(payload, str) or not payload:
            raise AduroInvalidResponseError("Consumption counter response is empty")

        raw_values = payload.split("=", 1)[-1].strip(";, ").split(",")
        try:
            return tuple(float(value) for value in raw_values if value != "")
        except (TypeError, ValueError) as err:
            raise AduroInvalidResponseError(
                f"Invalid consumption counter payload: {payload!r}"
            ) from err

    def _request_unlocked(
        self,
        function: Callable[..., Any],
        *args: Any,
        expected_function: int,
        **kwargs: Any,
    ) -> Any:
        output = io.StringIO()
        try:
            with redirect_stdout(output), redirect_stderr(output):
                response = function(*args, **kwargs)
        except OSError as err:
            raise AduroConnectionError(
                f"NBE request to {self.host} failed: {type(err).__name__}: {err}"
            ) from err
        except (ValueError, TypeError) as err:
            raise AduroInvalidResponseError(
                f"Could not parse stove response: {type(err).__name__}: {err}"
            ) from err
        except Exception as err:  # pyduro's malformed-frame errors lack good text
            raise AduroInvalidResponseError(
                f"Could not process stove response: {type(err).__name__}: {err}"
            ) from err

        library_output = output.getvalue().strip()
        if library_output:
            _LOGGER.debug("pyduro: %s", library_output)

        if response is None:
            raise AduroConnectionError(f"No response received from {self.host}")

        status = getattr(response, "status", None)
        if not isinstance(status, int):
            raise AduroInvalidResponseError("Stove response has no valid NBE status")
        if status != 0:
            raise AduroRejectedError(status, str(getattr(response, "payload", "")))

        response_serial = str(getattr(response, "serial", ""))
        if response_serial != self.serial:
            raise AduroInvalidResponseError(
                f"Response serial {response_serial!r} does not match {self.serial!r}"
            )
        if getattr(response, "function", None) != expected_function:
            raise AduroInvalidResponseError(
                "Response function does not match the request "
                f"({getattr(response, 'function', None)!r} != {expected_function})"
            )
        if getattr(response, "sequence_number", None) != 0:
            raise AduroInvalidResponseError("Unexpected NBE response sequence number")

        return response

    def _report_partial_errors(self, errors: tuple[str, ...]) -> None:
        if errors == self._last_partial_errors:
            return
        if errors:
            _LOGGER.warning(
                "Aduro status is available, but optional data could not be "
                "refreshed: %s",
                "; ".join(errors),
            )
        elif self._last_partial_errors:
            _LOGGER.info("All optional Aduro data sections are available again")
        self._last_partial_errors = errors


def normalize_serial(serial: str) -> str:
    """Mirror pyduro's documented six-character serial normalization."""
    return f"{str(serial).strip():0>6.6}"


def normalize_pin(pin: str) -> str:
    """Mirror pyduro's documented ten-character PIN normalization."""
    return f"{str(pin).strip():0<10.10}"


def _coerce_value(value: Any) -> Value:
    if value is None or isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not _NUMBER_PATTERN.fullmatch(text):
        return text
    number = float(text)
    return int(number) if number.is_integer() else number


def _parse_mapping_payload(response: Any, label: str) -> dict[str, Value]:
    payload = getattr(response, "payload", None)
    if not isinstance(payload, str) or not payload:
        raise AduroInvalidResponseError(f"{label} response is empty")

    result: dict[str, Value] = {}
    for item in payload.strip(";").split(";"):
        if not item:
            continue
        if "=" not in item:
            raise AduroInvalidResponseError(
                f"Malformed {label} item without '=': {item!r}"
            )
        key, value = item.split("=", 1)
        result[key] = _coerce_value(value)

    if not result:
        raise AduroInvalidResponseError(f"{label} response has no values")
    return result
