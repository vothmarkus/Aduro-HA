"""The Aduro Hybrid integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .api import AduroClient
from .const import CONF_PIN, CONF_SERIAL
from .coordinator import AduroCoordinator

PLATFORMS: tuple[Platform, ...] = (
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SENSOR,
)


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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Aduro Hybrid config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
