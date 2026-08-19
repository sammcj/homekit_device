"""Platform for switch integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
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
    entities = []

    # Common power entity — only wrap if it's a switch domain entity. Fan
    # domain power entities are wrapped by fan.py instead. Electric blankets
    # manage power implicitly (the climate zones drive the master power) and
    # kettles carry power as their thermostat's Off/Heat mode, so neither
    # exposes a standalone power switch.
    power = config_entry.data.get(CONF_POWER_SWITCH)
    if power and power.startswith("switch.") and device_type not in ("electric_blanket", "kettle"):
        entities.append(
            HomeKitDeviceSwitch(
                hass,
                config_entry.entry_id,
                "Power",
                power,
            )
        )

    # Device-specific switches
    if device_type == "kettle":
        if keep_warm := config_entry.data.get(CONF_KEEP_WARM):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    "Keep Warm",
                    keep_warm,
                )
            )

    elif device_type == "fan":
        if oscillation := config_entry.data.get(CONF_OSCILLATION):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    "Oscillation",
                    oscillation,
                )
            )

    elif device_type == "security_system":
        if siren := config_entry.data.get(CONF_SIREN):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    "Siren",
                    siren,
                )
            )

    elif device_type == "air_purifier":
        if child_lock := config_entry.data.get(CONF_CHILD_LOCK):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    "Child Lock",
                    child_lock,
                )
            )
        if display_switch := config_entry.data.get(CONF_DISPLAY_SWITCH):
            entities.append(
                HomeKitDeviceSwitch(
                    hass,
                    config_entry.entry_id,
                    "Display",
                    display_switch,
                )
            )

    if entities:
        async_add_entities(entities)
