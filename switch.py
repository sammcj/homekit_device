"""Platform for switch integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_POWER_SWITCH,
    CONF_OSCILLATION,
    CONF_SIREN,
    CONF_KEEP_WARM,
    CONF_CHILD_LOCK,
    CONF_DISPLAY_SWITCH,
)
from .entity import HomeKitDeviceSwitch

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device switches."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    base_name = config_entry.data.get(CONF_NAME, "Smart Device")
    entities = []

    # Common power switch for all device types
    power_switch = config_entry.data.get(CONF_POWER_SWITCH)
    if power_switch:
        entities.append(
            HomeKitDeviceSwitch(
                hass,
                config_entry.entry_id,
                f"{base_name} Power",
                power_switch,
            )
        )

    # Device-specific switches
    if device_type == "fan":
        if oscillation := config_entry.data.get(CONF_OSCILLATION):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Oscillation",
                    oscillation,
                )
            )

    elif device_type == "security_system":
        if siren := config_entry.data.get(CONF_SIREN):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Siren",
                    siren,
                )
            )

    elif device_type == "air_purifier":
        if child_lock := config_entry.data.get(CONF_CHILD_LOCK):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Child Lock",
                    child_lock,
                )
            )
        if display_switch := config_entry.data.get(CONF_DISPLAY_SWITCH):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Display",
                    display_switch,
                )
            )

    if entities:
        async_add_entities(entities)
