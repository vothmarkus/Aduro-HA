"""Climate platform for Aduro Hybrid."""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AduroCoordinator
from .entity import AduroEntity
from .model import as_float, as_int, is_heating, values_equal

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
    _attr_hvac_modes: ClassVar[list[HVACMode]] = [HVACMode.AUTO, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
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
    def hvac_mode(self) -> HVACMode:
        # Aduro H2 temperature mode is fixed at operation_mode=1. No extra
        # configurable mode value is intentionally introduced.
        if as_int(self.coordinator.data.setting("regulation", "operation_mode")) == 1:
            return HVACMode.AUTO
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        power = as_float(self.coordinator.data.status.get("power_pct"))
        if power is not None:
            return HVACAction.OFF if power == 0 else HVACAction.HEATING
        return (
            HVACAction.HEATING if is_heating(self.coordinator.data) else HVACAction.OFF
        )

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
        value = 1 if hvac_mode == HVACMode.AUTO else 0
        await self.coordinator.async_command(
            "regulation.operation_mode",
            value,
            verify=lambda data: values_equal(
                data.setting("regulation", "operation_mode"), value
            ),
        )
