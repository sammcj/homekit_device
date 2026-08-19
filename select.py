"""Platform for select integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_DIRECTION,
)
from .entity import HomeKitDeviceSelect

FAN_DIRECTION_OPTIONS = ["Forward", "Reverse"]

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device selects."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    base_name = config_entry.data.get(CONF_NAME, "Smart Device")
    entities = []

    # Device-specific select controls
    if device_type == "fan":
        if direction := config_entry.data.get(CONF_DIRECTION):
            entities.append(
                HomeKitDeviceSelect(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Direction",
                    direction,
                    FAN_DIRECTION_OPTIONS,
                )
            )

    if entities:
        async_add_entities(entities)
