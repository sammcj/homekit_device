"""Config flow for HomeKit Device Aggregator integration."""
from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_DEVICE_TYPE,
    CONF_POWER_SWITCH,
    CONF_TEMP_SENSORS,
    CONF_TARGET_TEMP,
    CONF_CURRENT_TEMP,
    CONF_STATUS_SENSOR,
    CONF_COUNTDOWN,
    CONF_FAULT,
    CONF_KEEP_WARM,
    CONF_SPEED_CONTROL,
    CONF_OSCILLATION,
    CONF_DIRECTION,
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_RGB_CONTROL,
    CONF_CURRENT_HUMIDITY,
    CONF_TARGET_HUMIDITY,
    CONF_WATER_LEVEL,
    CONF_AIR_QUALITY,
    CONF_FILTER_LIFE,
    CONF_PM25,
    CONF_VOC,
    CONF_DOOR_POSITION,
    CONF_OBSTRUCTION,
    CONF_MOTION,
    CONF_LIGHT_SWITCH,
    CONF_ALARM_STATE,
    CONF_SENSORS,
    CONF_SIREN,
    CONF_LASER_LIGHT,
    CONF_BACKGROUND_LIGHT,
    CONF_ROTATION_FAN,
    CONF_CHILD_LOCK,
    CONF_DISPLAY_SWITCH,
    CONF_ZONE_BODY,
    CONF_ZONE_FEET,
    CONF_BODY_TIMER,
    CONF_FEET_TIMER,
    CONF_LIFT_COVER,
    CONF_TILT_COVER,
    DEVICE_TYPES,
    DEFAULT_NAME,
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeKit Device Aggregator."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._data: Dict[str, Any] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_device_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_DEVICE_TYPE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(DEVICE_TYPES.keys()),
                            translation_key="device_type",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_device_config(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle device specific configuration."""
        errors = {}

        if user_input is not None:
            if self._invalid_tilt_cover(user_input):
                errors[CONF_TILT_COVER] = "tilt_same_as_lift"
            else:
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data[CONF_NAME],
                    data=self._data,
                )

        schema = self._get_device_schema()
        return self.async_show_form(
            step_id="device_config",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), user_input or {}
            ),
            errors=errors,
        )

    def _invalid_tilt_cover(self, user_input: Dict[str, Any]) -> bool:
        """Reject one entity used for both halves unless it has its own tilt."""
        tilt = user_input.get(CONF_TILT_COVER)
        if not tilt or tilt != user_input.get(CONF_LIFT_COVER):
            return False
        state = self.hass.states.get(tilt)
        features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0) if state else 0
        return not features & CoverEntityFeature.SET_TILT_POSITION

    def _get_device_schema(self) -> dict:
        """Get the configuration schema for the selected device type."""
        device_type = self._data[CONF_DEVICE_TYPE]
        base_schema = {
            vol.Required(CONF_POWER_SWITCH): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "fan"])
            ),
            vol.Optional(CONF_STATUS_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        }

        device_schemas = {
            "kettle": {
                vol.Optional(CONF_CURRENT_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_TARGET_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="input_number")
                ),
                vol.Optional(CONF_COUNTDOWN): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_FAULT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_KEEP_WARM): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
            },
            "thermostat": {
                vol.Required(CONF_CURRENT_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_TARGET_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Optional(CONF_TEMP_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=True,
                    )
                ),
            },
            "fan": {
                vol.Optional(CONF_SPEED_CONTROL): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Optional(CONF_OSCILLATION): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(CONF_DIRECTION): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="select")
                ),
            },
            "light": {
                vol.Optional(CONF_BRIGHTNESS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Optional(CONF_COLOR_TEMP): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Optional(CONF_RGB_CONTROL): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="text")
                ),
            },
            "humidifier": {
                vol.Required(CONF_CURRENT_HUMIDITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_TARGET_HUMIDITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Optional(CONF_WATER_LEVEL): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            },
            "air_purifier": {
                vol.Optional(CONF_AIR_QUALITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_FILTER_LIFE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_PM25): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_VOC): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_CHILD_LOCK): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(CONF_DISPLAY_SWITCH): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
            },
            "garage_door": {
                vol.Required(CONF_DOOR_POSITION): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="cover")
                ),
                vol.Optional(CONF_OBSTRUCTION): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(CONF_MOTION): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional(CONF_LIGHT_SWITCH): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light")
                ),
            },
            "security_system": {
                vol.Required(CONF_ALARM_STATE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="alarm_control_panel")
                ),
                vol.Optional(CONF_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        multiple=True,
                    )
                ),
                vol.Optional(CONF_SIREN): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
            },
            "star_projector": {
                vol.Optional(CONF_LASER_LIGHT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light")
                ),
                vol.Optional(CONF_BACKGROUND_LIGHT): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light")
                ),
                vol.Optional(CONF_ROTATION_FAN): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="fan")
                ),
            },
            "shutter": {
                vol.Required(CONF_LIFT_COVER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="cover")
                ),
                vol.Optional(CONF_TILT_COVER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="cover")
                ),
            },
            "electric_blanket": {
                vol.Required(CONF_ZONE_BODY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="select")
                ),
                vol.Optional(CONF_ZONE_FEET): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="select")
                ),
                vol.Optional(CONF_BODY_TIMER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="select")
                ),
                vol.Optional(CONF_FEET_TIMER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="select")
                ),
            },
        }

        # Shutters have no power entity - the cover entities are the whole device.
        schema = {} if device_type == "shutter" else base_schema.copy()
        if device_type in device_schemas:
            schema.update(device_schemas[device_type])

        return schema
