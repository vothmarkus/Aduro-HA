"""The Aduro Hybrid integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .api import AduroClient
from .const import CONF_PIN, CONF_SERIAL
from .coordinator import AduroCoordinator

PLATFORMS: tuple[Platform, ...] = (
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
)

_REMOVED_ENTITY_KEYS = frozenset({"exhaust_speed", "fixed_power", "heating"})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aduro Hybrid from a config entry."""
    client = AduroClient(
        host=entry.data[CONF_HOST],
        serial=entry.data[CONF_SERIAL],
        pin=entry.data[CONF_PIN],
    )
    coordinator = AduroCoordinator(hass, entry, client)
    entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()
    _async_remove_old_entities(hass, entry, client.serial)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Aduro Hybrid config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _async_remove_old_entities(
    hass: HomeAssistant, entry: ConfigEntry, serial: str
) -> None:
    """Remove entities replaced during the pre-1.0 climate consolidation."""
    registry = er.async_get(hass)
    removed_unique_ids = {f"{serial}_{key}" for key in _REMOVED_ENTITY_KEYS}
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.unique_id in removed_unique_ids:
            registry.async_remove(registry_entry.entity_id)
