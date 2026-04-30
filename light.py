"""Platform for light integration."""
from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_LIGHT_SWITCH,
    CONF_LASER_LIGHT,
    CONF_BACKGROUND_LIGHT,
)
from .entity import HomeKitDeviceEntity

class HomeKitDeviceLight(HomeKitDeviceEntity, LightEntity):
    """Representation of a HomeKit Device light."""

    async def async_added_to_hass(self) -> None:
        """Mirror the source entity's supported color modes once it is known."""
        modes: set[ColorMode] = {ColorMode.ONOFF}
        if (state := self.hass.states.get(self._source_entity)) is not None:
            source_modes = state.attributes.get("supported_color_modes") or ()
            parsed: set[ColorMode] = set()
            for raw in source_modes:
                try:
                    parsed.add(ColorMode(raw))
                except ValueError:
                    continue
            if parsed:
                modes = parsed
        self._attr_supported_color_modes = modes
        if self._attr_color_mode is None:
            self._attr_color_mode = next(iter(modes))
        await super().async_added_to_hass()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        await self.hass.services.async_call(
            "light", "turn_on",
            {"entity_id": self._source_entity, **kwargs}
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        await self.hass.services.async_call(
            "light", "turn_off",
            {"entity_id": self._source_entity}
        )

    async def async_update_from_source(self, state) -> None:
        """Update the entity from the source entity state."""
        self._attr_is_on = state.state == "on"
        attrs = state.attributes
        if (brightness := attrs.get("brightness")) is not None:
            self._attr_brightness = brightness
        if (kelvin := attrs.get("color_temp_kelvin")) is not None:
            self._attr_color_temp_kelvin = kelvin
        if (rgb := attrs.get("rgb_color")) is not None:
            self._attr_rgb_color = rgb
        if (hs := attrs.get("hs_color")) is not None:
            self._attr_hs_color = hs
        if (raw_mode := attrs.get("color_mode")) is not None:
            try:
                self._attr_color_mode = ColorMode(raw_mode)
            except ValueError:
                pass
        self.async_write_ha_state()

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device lights."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    base_name = config_entry.data.get(CONF_NAME, "Smart Device")
    entities = []

    # Device-specific lights
    if device_type == "garage_door":
        if light_switch := config_entry.data.get(CONF_LIGHT_SWITCH):
            entities.append(
                HomeKitDeviceLight(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Light",
                    light_switch,
                )
            )

    elif device_type == "star_projector":
        if laser_light := config_entry.data.get(CONF_LASER_LIGHT):
            entities.append(
                HomeKitDeviceLight(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Laser",
                    laser_light,
                )
            )
        if background_light := config_entry.data.get(CONF_BACKGROUND_LIGHT):
            entities.append(
                HomeKitDeviceLight(
                    hass,
                    config_entry.entry_id,
                    f"{base_name} Background",
                    background_light,
                )
            )

    if entities:
        async_add_entities(entities)
