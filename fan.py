"""Platform for fan integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_ROTATION_FAN,
)
from .entity import HomeKitDeviceFan

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device fans."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    base_name = config_entry.data.get(CONF_NAME, "Smart Device")
    entities = []

    if device_type == "star_projector":
        if rotation_fan := config_entry.data.get(CONF_ROTATION_FAN):
            entities.append(
                HomeKitDeviceFan(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Rotation",
                    rotation_fan,
                )
            )

    if entities:
        async_add_entities(entities)
