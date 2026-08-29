"""Number platform for Aduro Hybrid."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AduroCoordinator
from .entity import AduroEntity
from .model import as_float

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aduro number entities."""
    async_add_entities([AduroForceAugerNumber(entry.runtime_data)])


class AduroForceAugerNumber(AduroEntity, NumberEntity):
    """Run the pellet auger for a requested number of seconds."""

    _attr_translation_key = "force_auger"
    _attr_icon = "mdi:screw-machine-flat-top"
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_step = 5
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "s"

    def __init__(self, coordinator: AduroCoordinator) -> None:
        super().__init__(coordinator, "force_auger")

    @property
    def available(self) -> bool:
        return self.section_available("auger")

    @property
    def native_value(self) -> float | None:
        return as_float(self.coordinator.data.setting("auger", "forced_run"))

    async def async_set_native_value(self, value: float) -> None:
        # forced_run can count down before read-back, so the direct success
        # response is validated but equality with the requested duration is not.
        await self.coordinator.async_command("auger.forced_run", int(value))
