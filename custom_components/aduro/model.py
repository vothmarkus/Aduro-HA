"""Data model and protocol-independent helpers for Aduro Hybrid."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose, isfinite
from typing import Any

from .const import FIXED_POWER_PRESETS, OFF_STATE_CODES

Value = str | int | float | None


@dataclass(frozen=True, slots=True)
class AduroData:
    """A coherent snapshot returned by the stove."""

    status: dict[str, Value] = field(default_factory=dict)
    settings: dict[str, dict[str, Value]] = field(default_factory=dict)
    consumption_counter: tuple[float, ...] = ()
    stale_sections: frozenset[str] = frozenset()

    def setting(self, section: str, key: str) -> Value:
        """Return one setting value."""
        return self.settings.get(section, {}).get(key)


def as_float(value: Any) -> float | None:
    """Return a finite-enough numeric value or None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def as_int(value: Any) -> int | None:
    """Return an integer value or None."""
    number = as_float(value)
    if number is None:
        return None
    return int(number)


def values_equal(actual: Any, expected: Any) -> bool:
    """Compare protocol values without string/float representation surprises."""
    actual_number = as_float(actual)
    expected_number = as_float(expected)
    if actual_number is not None and expected_number is not None:
        return isclose(actual_number, expected_number, rel_tol=0, abs_tol=0.01)
    return str(actual) == str(expected)


def is_heating(data: AduroData) -> bool | None:
    """Return the heating state using the mapping proven by the add-on."""
    state = as_int(data.status.get("state"))
    if state is None:
        return None
    return state not in OFF_STATE_CODES


def fixed_power_preset(data: AduroData) -> str | None:
    """Return the active fixed-power preset, or None in temperature mode."""
    if as_int(data.setting("regulation", "operation_mode")) != 0:
        return None

    power = as_float(data.setting("regulation", "fixed_power"))
    if power is None:
        return None
    if power >= 90:
        return "boost"
    if power >= 40:
        return "comfort"
    return "eco"


def fixed_power_for_preset(preset: str) -> int | None:
    """Return the fixed pellet power for a Home Assistant preset."""
    return FIXED_POWER_PRESETS.get(preset)


def stove_state_key(data: AduroData) -> str:
    """Map Aduro state/substate codes to stable translated state keys."""
    state = as_int(data.status.get("state"))
    substate = as_int(data.status.get("substate"))

    if state == 14:
        if substate == 0:
            return "off"
        if substate == 6:
            return "stopping"
        return "unknown"

    return {
        2: "ignition",
        4: "extended_ignition",
        32: "heating_up",
        5: "running",
        0: "waiting",
        6: "temperature_reached",
        9: "wood_burning",
        20: "flame_out",
        13: "ignition_failed",
        28: "door_open",
        24: "pellet_air_intake_closed",
    }.get(state, "unknown")
