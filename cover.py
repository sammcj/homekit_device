"""Platform for cover integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_LIFT_COVER,
    CONF_TILT_COVER,
)
from .entity import HomeKitDeviceCover

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device covers."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    base_name = config_entry.data.get(CONF_NAME, "Smart Device")

    if device_type != "shutter":
        return

    if not (lift := config_entry.data.get(CONF_LIFT_COVER)):
        return

    async_add_entities(
        [
            HomeKitDeviceCover(
                hass,
                config_entry.entry_id,
                base_name,
                lift,
                config_entry.data.get(CONF_TILT_COVER),
            )
        ]
    )
