"""Platform for climate integration."""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_ZONE_BODY,
    CONF_ZONE_FEET,
)
from .entity import HomeKitDeviceEntity

# localtuya presents friendly options; index 0 ("Off") maps to the raw level_1.
DEFAULT_OPTIONS = ["Off", "1", "2", "3", "4", "5", "6"]
OFF_OPTION = "Off"
UNAVAILABLE_STATES = (None, "unknown", "unavailable")

class HomeKitDeviceClimate(HomeKitDeviceEntity, ClimateEntity):
    """Climate proxy mapping a heat-level select onto a HomeKit heater.

    A zone select like ['Off','1'..'6'] is presented as Off/Heat with a
    0-6 target temperature slider, which the HomeKit bridge exposes as a
    Heater/HeaterCooler service.
    """

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_target_temperature_step = 1
    _attr_min_temp = 0
    _attr_max_temp = 6
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        entity_id: str,
    ) -> None:
        """Initialize the climate proxy."""
        super().__init__(hass, entry_id, name, entity_id)
        self._options = DEFAULT_OPTIONS
        self._last_heat_level = "1"
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 0
        self._attr_current_temperature = 0

    async def async_added_to_hass(self) -> None:
        """Size the level slider from the source select's option list."""
        if (state := self.hass.states.get(self._source_entity)) is not None:
            if options := state.attributes.get("options"):
                self._options = list(options)
                # Heat levels are the options excluding "Off"; map to a 0..N
                # slider so blankets with fewer/more levels adapt automatically.
                self._attr_max_temp = max(1, len(self._options) - 1)
        await super().async_added_to_hass()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the heat level from the HomeKit temperature slider."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        level = int(temp)
        await self._select_option(OFF_OPTION if level <= 0 else str(level))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Map Off/Heat onto the source select."""
        if hvac_mode == HVACMode.OFF:
            await self._select_option(OFF_OPTION)
        else:
            await self._select_option(self._last_heat_level)

    async def _select_option(self, option: str) -> None:
        """Forward a friendly option to the source select."""
        await self.hass.services.async_call(
            "select", "select_option",
            {"entity_id": self._source_entity, "option": option},
        )

    async def async_update_from_source(self, state) -> None:
        """Map the source select state to hvac_mode and target temperature."""
        option = state.state
        if option == OFF_OPTION or option in UNAVAILABLE_STATES:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_target_temperature = 0
        else:
            self._attr_hvac_mode = HVACMode.HEAT
            try:
                self._attr_target_temperature = int(option)
                self._last_heat_level = option
            except (ValueError, TypeError):
                self._attr_target_temperature = 0
        self._attr_current_temperature = self._attr_target_temperature
        self.async_write_ha_state()

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device climate proxies."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    base_name = config_entry.data.get(CONF_NAME, "Smart Device")
    entities = []

    if device_type == "electric_blanket":
        for conf_key, label in ((CONF_ZONE_BODY, "Body"), (CONF_ZONE_FEET, "Feet")):
            if zone := config_entry.data.get(conf_key):
                entities.append(
                    HomeKitDeviceClimate(
                        hass,
                        config_entry.entry_id,
                        f"{base_name} {label}",
                        zone,
                    )
                )

    if entities:
        async_add_entities(entities)
