"""Sensor platform for Aduro Hybrid."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STATE_OPTIONS
from .coordinator import AduroCoordinator
from .entity import AduroEntity
from .model import AduroData, as_float, as_int, stove_state_key

PARALLEL_UPDATES = 0

SensorValueFn = Callable[[AduroData], str | int | float | None]


@dataclass(frozen=True, kw_only=True)
class AduroSensorDescription(SensorEntityDescription):
    """Describe an Aduro sensor."""

    value_fn: SensorValueFn
    source_section: str = "status"


SENSORS: tuple[AduroSensorDescription, ...] = (
    AduroSensorDescription(
        key="stove_state",
        translation_key="stove_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(STATE_OPTIONS),
        icon="mdi:fire",
        value_fn=stove_state_key,
    ),
    AduroSensorDescription(
        key="room_temperature",
        translation_key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_float(data.status.get("boiler_temp")),
    ),
    AduroSensorDescription(
        key="smoke_temperature",
        translation_key="smoke_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: as_float(data.status.get("smoke_temp")),
    ),
    AduroSensorDescription(
        key="shaft_temperature",
        translation_key="shaft_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_float(data.status.get("shaft_temp")),
    ),
    AduroSensorDescription(
        key="oxygen",
        translation_key="oxygen",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:molecule",
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_float(data.status.get("oxygen")),
    ),
    AduroSensorDescription(
        key="power_percentage",
        translation_key="power_percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:fire-circle",
        value_fn=lambda data: as_float(data.status.get("power_pct")),
    ),
    AduroSensorDescription(
        key="carbon_monoxide",
        translation_key="carbon_monoxide",
        device_class=SensorDeviceClass.CO,
        native_unit_of_measurement="ppm",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: as_float(data.status.get("drift.co")),
    ),
    AduroSensorDescription(
        key="total_hours",
        translation_key="total_hours",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        source_section="consumption_counter",
        value_fn=lambda data: (
            data.consumption_counter[0] if data.consumption_counter else None
        ),
    ),
    AduroSensorDescription(
        key="state_number",
        translation_key="state_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_int(data.status.get("state")),
    ),
    AduroSensorDescription(
        key="substate_number",
        translation_key="substate_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_int(data.status.get("substate")),
    ),
    AduroSensorDescription(
        key="state_time",
        translation_key="state_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: as_float(data.status.get("state_sec")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aduro sensors."""
    coordinator: AduroCoordinator = entry.runtime_data
    async_add_entities(AduroSensor(coordinator, description) for description in SENSORS)


class AduroSensor(AduroEntity, SensorEntity):
    """A sensor backed by the shared Aduro snapshot."""

    entity_description: AduroSensorDescription

    def __init__(
        self, coordinator: AduroCoordinator, description: AduroSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.entity_description.source_section
            not in self.coordinator.data.stale_sections
            and self.native_value is not None
        )

    @property
    def native_value(self) -> str | int | float | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "stove_state":
            return None
        return {
            "state_code": as_int(self.coordinator.data.status.get("state")),
            "substate_code": as_int(self.coordinator.data.status.get("substate")),
        }
