"""Base entity for Aduro Hybrid."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AduroCoordinator


class AduroEntity(CoordinatorEntity[AduroCoordinator]):
    """Common identity and device data for all Aduro entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AduroCoordinator, key: str) -> None:
        super().__init__(coordinator)
        serial = coordinator.client.serial
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer="Aduro",
            model="Hybrid H2 (NBE)",
            name=coordinator.config_entry.title,
            serial_number=serial,
        )

    def section_available(self, section: str) -> bool:
        """Return whether one optional section was refreshed successfully."""
        return super().available and section not in self.coordinator.data.stale_sections
