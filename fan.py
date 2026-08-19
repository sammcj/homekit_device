"""Platform for fan integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_POWER_SWITCH,
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
    entities = []

    # Power entity that is itself a fan (e.g. an air purifier exposed as a
    # fan with percentage speeds). switch.py skips fan-domain entities.
    # Kettles and electric blankets carry power on their climate entity, so
    # they get no standalone power proxy in either domain.
    power = config_entry.data.get(CONF_POWER_SWITCH)
    if (
        power
        and power.startswith("fan.")
        and device_type not in ("electric_blanket", "kettle")
    ):
        entities.append(
            HomeKitDeviceFan(
                hass,
                config_entry.entry_id,
                "Power",
                power,
            )
        )

    if device_type == "star_projector":
        if rotation_fan := config_entry.data.get(CONF_ROTATION_FAN):
            entities.append(
                HomeKitDeviceFan(
                    hass,
                    config_entry.entry_id,
                    "Rotation",
                    rotation_fan,
                )
            )

    if entities:
        async_add_entities(entities)
