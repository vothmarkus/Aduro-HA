"""Constants for the Aduro Hybrid integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "aduro"

CONF_SERIAL: Final = "serial"
CONF_PIN: Final = "pin"

DEFAULT_NAME: Final = "Aduro H2"
DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 15
MAX_SCAN_INTERVAL: Final = 300

COMMAND_REFRESH_DELAYS: Final = (0.6, 1.5)

# Kept identical to the proven Aduro2mqtt add-on behavior. The controller
# reports these states as not heating, even if some are fault/door states.
OFF_STATE_CODES: Final = frozenset({13, 14, 20, 28})

STATE_OPTIONS: Final = (
    "off",
    "stopping",
    "ignition",
    "extended_ignition",
    "heating_up",
    "running",
    "waiting",
    "temperature_reached",
    "wood_burning",
    "flame_out",
    "ignition_failed",
    "door_open",
    "pellet_air_intake_closed",
    "unknown",
)

WRITABLE_PATHS: Final = frozenset(
    {
        "misc.start",
        "misc.stop",
        "regulation.operation_mode",
        "regulation.fixed_power",
        "boiler.temp",
        "auger.forced_run",
    }
)
