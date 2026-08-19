"""Platform for binary sensor integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_OBSTRUCTION,
    CONF_MOTION,
    CONF_SENSORS,
)
from .entity import HomeKitDeviceEntity

class HomeKitDeviceBinarySensor(HomeKitDeviceEntity, BinarySensorEntity):
    """Representation of a HomeKit Device binary sensor."""

    async def async_update_from_source(self, state) -> None:
        """Update the entity from the source entity state."""
        self._attr_is_on = state.state == "on"
        self.async_write_ha_state()

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device binary sensors."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    entities = []

    # Device-specific binary sensors
    if device_type == "garage_door":
        if obstruction := config_entry.data.get(CONF_OBSTRUCTION):
            entities.append(
                HomeKitDeviceBinarySensor(
                    hass,
                    config_entry.entry_id,
                    "Obstruction",
                    obstruction,
                )
            )
        if motion := config_entry.data.get(CONF_MOTION):
            entities.append(
                HomeKitDeviceBinarySensor(
                    hass,
                    config_entry.entry_id,
                    "Motion",
                    motion,
                )
            )

    elif device_type == "security_system":
        if sensors := config_entry.data.get(CONF_SENSORS):
            for i, sensor in enumerate(sensors, 1):
                entities.append(
                    HomeKitDeviceBinarySensor(
                        hass,
                        config_entry.entry_id,
                        f"Sensor {i}",
                        sensor,
                    )
                )

    if entities:
        async_add_entities(entities)
