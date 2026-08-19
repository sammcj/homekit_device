"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_CURRENT_TEMP,
    CONF_STATUS_SENSOR,
    CONF_COUNTDOWN,
    CONF_FAULT,
    CONF_WATER_LEVEL,
    CONF_AIR_QUALITY,
    CONF_FILTER_LIFE,
    CONF_PM25,
    CONF_VOC,
    CONF_CURRENT_HUMIDITY,
)
from .entity import HomeKitDeviceSensor

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device sensors."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    base_name = config_entry.data.get(CONF_NAME, "Smart Device")
    entities = []

    # Common sensors
    if status_sensor := config_entry.data.get(CONF_STATUS_SENSOR):
        entities.append(
            HomeKitDeviceSensor(
                hass,
                config_entry.entry_id,
                f"{base_name} Status",
                status_sensor,
                diagnostic=True,
            )
        )

    # Device-specific sensors
    if device_type == "kettle":
        if current_temp := config_entry.data.get(CONF_CURRENT_TEMP):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Temperature",
                    current_temp,
                    "°C",
                    # The thermostat already carries this reading; keeping it
                    # diagnostic groups it in HA without a duplicate HomeKit tile.
                    diagnostic=True,
                )
            )
        if countdown := config_entry.data.get(CONF_COUNTDOWN):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Countdown",
                    countdown,
                    "min",
                    diagnostic=True,
                )
            )
        if fault := config_entry.data.get(CONF_FAULT):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Fault",
                    fault,
                    diagnostic=True,
                )
            )

    elif device_type == "humidifier":
        if current_humidity := config_entry.data.get(CONF_CURRENT_HUMIDITY):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Humidity",
                    current_humidity,
                    "%",
                )
            )
        if water_level := config_entry.data.get(CONF_WATER_LEVEL):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Water Level",
                    water_level,
                    "%",
                )
            )

    elif device_type == "air_purifier":
        if air_quality := config_entry.data.get(CONF_AIR_QUALITY):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Air Quality",
                    air_quality,
                )
            )
        if filter_life := config_entry.data.get(CONF_FILTER_LIFE):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Filter Life",
                    filter_life,
                    "%",
                )
            )
        if pm25 := config_entry.data.get(CONF_PM25):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} PM2.5",
                    pm25,
                    "µg/m³",
                )
            )
        if voc := config_entry.data.get(CONF_VOC):
            entities.append(
                HomeKitDeviceSensor(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} VOC",
                    voc,
                    "ppb",
                )
            )

    if entities:
        async_add_entities(entities)
