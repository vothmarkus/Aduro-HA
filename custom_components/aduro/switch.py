"""Switch platform for Aduro Hybrid."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AduroCoordinator
from .entity import AduroEntity
from .model import is_heating

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aduro switches."""
    async_add_entities([AduroHeatingSwitch(entry.runtime_data)])


class AduroHeatingSwitch(AduroEntity, SwitchEntity):
    """Start or stop pellet heating."""

    _attr_translation_key = "heating"
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator: AduroCoordinator) -> None:
        super().__init__(coordinator, "heating")

    @property
    def available(self) -> bool:
        return super().available and is_heating(self.coordinator.data) is not None

    @property
    def is_on(self) -> bool | None:
        return is_heating(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Start/stop are pulse commands. The accepted NBE response is checked,
        # then the actual status is fetched without optimistic state changes.
        await self.coordinator.async_command("misc.start", 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_command("misc.stop", 1)
