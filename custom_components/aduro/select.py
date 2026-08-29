"""Select platform for Aduro Hybrid."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AduroCoordinator
from .entity import AduroEntity
from .model import as_float, values_equal

PARALLEL_UPDATES = 0
POWER_OPTIONS = ("10", "50", "100")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aduro selects."""
    async_add_entities([AduroFixedPowerSelect(entry.runtime_data)])


class AduroFixedPowerSelect(AduroEntity, SelectEntity):
    """Select the fixed pellet power percentage."""

    _attr_translation_key = "fixed_power"
    _attr_icon = "mdi:fire"
    _attr_options: ClassVar[list[str]] = list(POWER_OPTIONS)

    def __init__(self, coordinator: AduroCoordinator) -> None:
        super().__init__(coordinator, "fixed_power")

    @property
    def available(self) -> bool:
        return self.section_available("regulation")

    @property
    def current_option(self) -> str | None:
        value = as_float(self.coordinator.data.setting("regulation", "fixed_power"))
        if value is None:
            return None
        option = str(int(value))
        return option if option in POWER_OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        if option not in POWER_OPTIONS:
            raise ValueError(f"Unsupported fixed power value: {option}")
        value = int(option)
        await self.coordinator.async_command(
            "regulation.fixed_power",
            value,
            verify=lambda data: values_equal(
                data.setting("regulation", "fixed_power"), value
            ),
        )
