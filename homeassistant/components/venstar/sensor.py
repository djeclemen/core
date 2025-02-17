"""Representation of Venstar sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS, TEMP_FAHRENHEIT, TIME_MINUTES
from homeassistant.helpers.entity import Entity

from . import VenstarDataUpdateCoordinator, VenstarEntity
from .const import DOMAIN

RUNTIME_HEAT1 = "heat1"
RUNTIME_HEAT2 = "heat2"
RUNTIME_COOL1 = "cool1"
RUNTIME_COOL2 = "cool2"
RUNTIME_AUX1 = "aux1"
RUNTIME_AUX2 = "aux2"
RUNTIME_FC = "fc"
RUNTIME_OV = "ov"

RUNTIME_DEVICES = [
    RUNTIME_HEAT1,
    RUNTIME_HEAT2,
    RUNTIME_COOL1,
    RUNTIME_COOL2,
    RUNTIME_AUX1,
    RUNTIME_AUX2,
    RUNTIME_FC,
    RUNTIME_OV,
]

RUNTIME_ATTRIBUTES = {
    RUNTIME_HEAT1: "Heating Stage 1",
    RUNTIME_HEAT2: "Heating Stage 2",
    RUNTIME_COOL1: "Cooling Stage 1",
    RUNTIME_COOL2: "Cooling Stage 2",
    RUNTIME_AUX1: "Aux Stage 1",
    RUNTIME_AUX2: "Aux Stage 2",
    RUNTIME_FC: "Free Cooling",
    RUNTIME_OV: "Override",
}


@dataclass
class VenstarSensorTypeMixin:
    """Mixin for sensor required keys."""

    value_fn: Callable[[Any, Any], Any]
    name_fn: Callable[[Any, Any], str]
    uom_fn: Callable[[Any], str]


@dataclass
class VenstarSensorEntityDescription(SensorEntityDescription, VenstarSensorTypeMixin):
    """Base description of a Sensor entity."""


async def async_setup_entry(hass, config_entry, async_add_entities) -> None:
    """Set up Vensar device binary_sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[Entity] = []

    sensors = coordinator.client.get_sensor_list()
    if not sensors:
        return

    for sensor_name in sensors:
        entities.extend(
            [
                VenstarSensor(coordinator, config_entry, description, sensor_name)
                for description in SENSOR_ENTITIES
                if coordinator.client.get_sensor(sensor_name, description.key)
                is not None
            ]
        )

    runtimes = coordinator.runtimes[-1]
    for sensor_name in runtimes:
        if sensor_name in RUNTIME_DEVICES:
            entities.append(
                VenstarSensor(coordinator, config_entry, RUNTIME_ENTITY, sensor_name)
            )

    async_add_entities(entities)


def temperature_unit(coordinator: VenstarDataUpdateCoordinator) -> str:
    """Return the correct unit for temperature."""
    unit = TEMP_CELSIUS
    if coordinator.client.tempunits == coordinator.client.TEMPUNITS_F:
        unit = TEMP_FAHRENHEIT
    return unit


class VenstarSensor(VenstarEntity, SensorEntity):
    """Base class for a Venstar sensor."""

    entity_description: VenstarSensorEntityDescription

    def __init__(
        self,
        coordinator: VenstarDataUpdateCoordinator,
        config: ConfigEntry,
        entity_description: VenstarSensorEntityDescription,
        sensor_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config)
        self.entity_description = entity_description
        self.sensor_name = sensor_name
        self._config = config

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self._config.entry_id}_{self.sensor_name.replace(' ', '_')}_{self.entity_description.key}"

    @property
    def name(self):
        """Return the name of the device."""
        return self.entity_description.name_fn(self.coordinator, self.sensor_name)

    @property
    def native_value(self) -> int:
        """Return state of the sensor."""
        return self.entity_description.value_fn(self.coordinator, self.sensor_name)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return unit of measurement the value is expressed in."""
        return self.entity_description.uom_fn(self.coordinator)


SENSOR_ENTITIES: tuple[VenstarSensorEntityDescription, ...] = (
    VenstarSensorEntityDescription(
        key="hum",
        device_class=DEVICE_CLASS_HUMIDITY,
        state_class=STATE_CLASS_MEASUREMENT,
        uom_fn=lambda coordinator: PERCENTAGE,
        value_fn=lambda coordinator, sensor_name: coordinator.client.get_sensor(
            sensor_name, "hum"
        ),
        name_fn=lambda coordinator, sensor_name: f"{coordinator.client.name} {sensor_name} Humidity",
    ),
    VenstarSensorEntityDescription(
        key="temp",
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        uom_fn=temperature_unit,
        value_fn=lambda coordinator, sensor_name: round(
            float(coordinator.client.get_sensor(sensor_name, "temp")), 1
        ),
        name_fn=lambda coordinator, sensor_name: f"{coordinator.client.name} {sensor_name.replace(' Temp', '')} Temperature",
    ),
    VenstarSensorEntityDescription(
        key="battery",
        device_class=DEVICE_CLASS_BATTERY,
        state_class=STATE_CLASS_MEASUREMENT,
        uom_fn=lambda coordinator: PERCENTAGE,
        value_fn=lambda coordinator, sensor_name: coordinator.client.get_sensor(
            sensor_name, "battery"
        ),
        name_fn=lambda coordinator, sensor_name: f"{coordinator.client.name} {sensor_name} Battery",
    ),
)

RUNTIME_ENTITY = VenstarSensorEntityDescription(
    key="runtime",
    state_class=STATE_CLASS_MEASUREMENT,
    uom_fn=lambda coordinator: TIME_MINUTES,
    value_fn=lambda coordinator, sensor_name: coordinator.runtimes[-1][sensor_name],
    name_fn=lambda coordinator, sensor_name: f"{coordinator.client.name} {RUNTIME_ATTRIBUTES[sensor_name]} Runtime",
)
