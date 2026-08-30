"""Climate platform for Aduro Hybrid."""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.climate import (
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AduroCoordinator
from .entity import AduroEntity
from .model import (
    as_float,
    as_int,
    climate_mode_commands,
    climate_mode_key,
    fixed_power_for_preset,
    fixed_power_preset,
    is_heating,
    values_equal,
)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aduro climate entity."""
    async_add_entities([AduroClimate(entry.runtime_data)])


class AduroClimate(AduroEntity, ClimateEntity):
    """Aduro temperature/fixed-power operating mode controller."""

    _attr_name = None
    _attr_hvac_modes: ClassVar[list[HVACMode]] = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.HEAT,
    ]
    _attr_preset_modes: ClassVar[list[str]] = [
        PRESET_ECO,
        PRESET_COMFORT,
        PRESET_BOOST,
    ]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5
    _attr_max_temp = 35
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: AduroCoordinator) -> None:
        super().__init__(coordinator, "climate")

    @property
    def available(self) -> bool:
        return (
            super().available
            and "boiler" not in self.coordinator.data.stale_sections
            and "regulation" not in self.coordinator.data.stale_sections
            and self.current_temperature is not None
            and self.target_temperature is not None
            and climate_mode_key(self.coordinator.data) is not None
        )

    @property
    def current_temperature(self) -> float | None:
        return as_float(
            self.coordinator.data.status.get(
                "room_temp", self.coordinator.data.status.get("boiler_temp")
            )
        )

    @property
    def target_temperature(self) -> float | None:
        return as_float(self.coordinator.data.setting("boiler", "temp"))

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return Off from actual state, otherwise the configured regulation."""
        mode = climate_mode_key(self.coordinator.data)
        return HVACMode(mode) if mode is not None else None

    @property
    def hvac_action(self) -> HVACAction:
        if is_heating(self.coordinator.data) is not True:
            return HVACAction.OFF

        power = as_float(self.coordinator.data.status.get("power_pct"))
        if power is not None:
            return HVACAction.IDLE if power == 0 else HVACAction.HEATING
        return HVACAction.HEATING

    @property
    def preset_mode(self) -> str | None:
        """Return the active 10/50/100 percent fixed-power level."""
        return fixed_power_preset(self.coordinator.data)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.async_command(
            "boiler.temp",
            float(temperature),
            verify=lambda data: values_equal(
                data.setting("boiler", "temp"), temperature
            ),
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in self._attr_hvac_modes:
            raise ValueError(f"Unsupported Aduro HVAC mode: {hvac_mode}")

        commands = climate_mode_commands(self.coordinator.data, hvac_mode.value)
        if commands is None:
            raise HomeAssistantError("The Aduro operating state is unavailable")

        for path, value in commands:
            if path == "regulation.operation_mode":
                # Confirm the desired regulation before starting a stopped stove.
                await self.coordinator.async_command(
                    path,
                    value,
                    verify=lambda data, expected=value: values_equal(
                        data.setting("regulation", "operation_mode"), expected
                    ),
                )
                continue

            expected_on = path == "misc.start"
            await self.coordinator.async_command(
                path,
                value,
                verify=lambda data, expected=expected_on: is_heating(data) is expected,
                strict_verify=False,
            )

    async def async_turn_on(self) -> None:
        """Start the stove in its already configured Auto/Heat mode."""
        operation_mode = as_int(
            self.coordinator.data.setting("regulation", "operation_mode")
        )
        if operation_mode not in (0, 1):
            raise HomeAssistantError("The Aduro regulation mode is unavailable")
        await self.async_set_hvac_mode(
            HVACMode.AUTO if operation_mode == 1 else HVACMode.HEAT
        )

    async def async_turn_off(self) -> None:
        """Stop the stove without changing its stored regulation mode."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set Eco/Comfort/Boost and activate fixed-power heating."""
        value = fixed_power_for_preset(preset_mode)
        if value is None:
            raise ValueError(f"Unsupported Aduro preset mode: {preset_mode}")

        # Store the power before entering fixed-power mode so the stove cannot
        # briefly start at a previously selected level.
        await self.coordinator.async_command(
            "regulation.fixed_power",
            value,
            verify=lambda data: values_equal(
                data.setting("regulation", "fixed_power"), value
            ),
        )
        if self.hvac_mode != HVACMode.HEAT:
            await self.async_set_hvac_mode(HVACMode.HEAT)
