"""Platform for climate integration."""
from __future__ import annotations

import asyncio

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, STATE_ON, UnitOfTemperature
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_CURRENT_TEMP,
    CONF_POWER_SWITCH,
    CONF_TARGET_TEMP,
    CONF_ZONE_BODY,
    CONF_ZONE_FEET,
)
from .entity import HomeKitDeviceEntity

# localtuya presents friendly options; index 0 ("Off") maps to the raw level_1.
DEFAULT_OPTIONS = ["Off", "1", "2", "3", "4", "5", "6"]
OFF_OPTION = "Off"
UNAVAILABLE_STATES = (None, "unknown", "unavailable")
# Coalesce rapid HomeKit slider changes: only the latest value is pushed to the
# device after this quiet period, so a quick drag doesn't queue a run of writes.
DEBOUNCE_SECONDS = 0.5

class HomeKitDeviceClimate(HomeKitDeviceEntity, ClimateEntity):
    """Climate proxy mapping a heat-level select onto a HomeKit heater.

    A zone select like ['Off','1'..'6'] is presented as Off/Heat with a
    0-6 target temperature slider, which the HomeKit bridge exposes as a
    Heater/HeaterCooler service.
    """

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_target_temperature_step = 1
    # Min must be >= 1: HA's HomeKit bridge treats a min of 0 as "unset" and
    # substitutes its own default (~7°C), which collides with max and produces a
    # broken range. Heat levels are 1-6; "off" is the on/off state, not level 0.
    _attr_min_temp = 1
    _attr_max_temp = 6
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    # On a cold power-on the blanket briefly resets its zones to Off; wait this
    # long before sending the level so that reset can't clobber it. Only applies
    # when powering on from cold (skipped if already on). Commands are
    # serialized by _cmd_lock, so this wait never causes a race.
    _power_on_settle = 1.5

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        entity_id: str,
        power_entity: str | None = None,
        all_zones: list[str] | None = None,
    ) -> None:
        """Initialize the climate proxy."""
        super().__init__(hass, entry_id, name, entity_id)
        self._power_entity = power_entity
        self._all_zones = all_zones or []
        # Serialize commands so a quick on-then-change can't race (the later
        # command always wins instead of a delayed earlier one clobbering it).
        self._cmd_lock = asyncio.Lock()
        self._options = DEFAULT_OPTIONS
        self._last_heat_level = "1"
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 1
        self._attr_current_temperature = 1
        self._desired_level = 1
        self._apply_cancel = None

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
        self._queue_desired(int(temp))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Map Off/Heat from HomeKit onto the source select."""
        self._queue_desired(0 if hvac_mode == HVACMode.OFF else int(self._last_heat_level))

    def _queue_desired(self, level: int) -> None:
        """Record the latest intent, reflect it immediately, debounce the write.

        HomeKit can fire several rapid changes during a slider drag. We show the
        user's value right away so the slider doesn't snap back to a lagging
        device value, and only push the final value to the device after a short
        quiet period.
        """
        self._desired_level = level
        if level <= 0:
            self._attr_hvac_mode = HVACMode.OFF
        else:
            self._attr_hvac_mode = HVACMode.HEAT
            self._attr_target_temperature = level
            self._last_heat_level = str(level)
        self.async_write_ha_state()
        if self._apply_cancel is not None:
            self._apply_cancel()
        self._apply_cancel = async_call_later(
            self.hass, DEBOUNCE_SECONDS, self._apply_desired
        )

    async def _apply_desired(self, _now) -> None:
        """Push the latest desired level to the device after the debounce."""
        self._apply_cancel = None
        level = self._desired_level
        async with self._cmd_lock:
            if level <= 0:
                await self._select_option(OFF_OPTION)
                await self._maybe_power_off()
            else:
                # Blanket only accepts a heat level while powered on, so turn
                # master power on first, then set the zone level.
                await self._power_on()
                await self._select_option(str(level))

    async def async_will_remove_from_hass(self) -> None:
        """Cancel any pending debounced write on removal."""
        if self._apply_cancel is not None:
            self._apply_cancel()
            self._apply_cancel = None
        await super().async_will_remove_from_hass()

    async def _maybe_power_off(self) -> None:
        """Turn master power off once every zone on the blanket is Off.

        Only called from the user's own Off command (never from device state
        updates), so it can't be triggered by transient device chatter.
        """
        if not self._power_entity:
            return
        for zone in self._all_zones:
            if zone == self._source_entity:
                continue
            state = self.hass.states.get(zone)
            if state is not None and state.state not in (OFF_OPTION, *UNAVAILABLE_STATES):
                return  # another zone is still heating; leave power on
        await self.hass.services.async_call(
            "switch", "turn_off",
            {"entity_id": self._power_entity}, blocking=True,
        )

    async def _power_on(self) -> None:
        """Ensure master power is on before setting a level.

        Skips entirely if power is already on (so mid-use adjustments are
        instant). On a cold start it powers on then waits `_power_on_settle`
        for the device's power-on zone reset to finish before the level is sent.
        """
        if not self._power_entity:
            return
        state = self.hass.states.get(self._power_entity)
        if state is not None and state.state == "on":
            return
        await self.hass.services.async_call(
            "switch", "turn_on",
            {"entity_id": self._power_entity}, blocking=True,
        )
        await asyncio.sleep(self._power_on_settle)

    async def _select_option(self, option: str) -> None:
        """Forward a friendly option to the source select."""
        await self.hass.services.async_call(
            "select", "select_option",
            {"entity_id": self._source_entity, "option": option},
        )

    async def async_update_from_source(self, state) -> None:
        """Map the source select state to hvac_mode and target temperature."""
        # While a user adjustment is still being debounced, don't let the
        # (lagging) device value override what the user just set.
        if self._apply_cancel is not None:
            return
        option = state.state
        if option == OFF_OPTION or option in UNAVAILABLE_STATES:
            self._attr_hvac_mode = HVACMode.OFF
            # Keep the setpoint at the last heat level (in range 1-6) rather
            # than 0, so HomeKit shows where it'll resume and stays in range.
            self._attr_target_temperature = int(self._last_heat_level)
        else:
            self._attr_hvac_mode = HVACMode.HEAT
            try:
                self._attr_target_temperature = int(option)
                self._last_heat_level = option
            except (ValueError, TypeError):
                self._attr_target_temperature = int(self._last_heat_level)
        self._attr_current_temperature = self._attr_target_temperature
        self.async_write_ha_state()

# Kettles run well above HomeKit's usual thermostat range; these are only used
# when the target temperature helper doesn't declare its own min/max.
KETTLE_DEFAULT_MIN_TEMP = 40
KETTLE_DEFAULT_MAX_TEMP = 100

def _as_float(value, fallback: float) -> float:
    """Coerce a state attribute to a float, falling back when it's missing or junk."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback

class HomeKitKettleClimate(HomeKitDeviceEntity, ClimateEntity):
    """Climate proxy presenting a kettle as a single HomeKit thermostat.

    The HomeKit bridge allocates one accessory per entity, so exposing power,
    current temperature and target temperature as three proxy entities gives
    three tiles in the Home app. Folding them into one climate entity gives one
    tile carrying all three as characteristics.
    """

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_target_temperature_step = 1
    _attr_icon = "mdi:kettle"

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        power_entity: str,
        current_temp_entity: str | None = None,
        target_temp_entity: str | None = None,
    ) -> None:
        """Initialize the kettle proxy."""
        super().__init__(hass, entry_id, "Kettle", power_entity)
        # The kettle's primary entity, so it takes the device's name.
        self._attr_name = None
        self._current_temp_entity = current_temp_entity
        self._target_temp_entity = target_temp_entity

        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if target_temp_entity:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_supported_features = features

        self._attr_min_temp = KETTLE_DEFAULT_MIN_TEMP
        self._attr_max_temp = KETTLE_DEFAULT_MAX_TEMP
        self._attr_hvac_mode = HVACMode.OFF

    async def async_added_to_hass(self) -> None:
        """Track the temperature entities alongside the power entity."""
        # Seed both before the base class writes state, so the first write is
        # complete rather than a thermostat with no temperatures.
        for entity_id, reader in self._extra_sources():
            if state := self.hass.states.get(entity_id):
                reader(state)

        await super().async_added_to_hass()

        for entity_id, reader in self._extra_sources():
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [entity_id], self._make_handler(reader)
                )
            )

    def _extra_sources(self):
        """Yield the (entity_id, reader) pairs beyond the power entity."""
        for entity_id, reader in (
            (self._current_temp_entity, self._read_current_temp),
            (self._target_temp_entity, self._read_target_temp),
        ):
            if entity_id:
                yield entity_id, reader

    def _make_handler(self, reader):
        """Build a state change handler that runs `reader` then writes state."""
        async def _handle(event: Event[EventStateChangedData]) -> None:
            new_state = event.data["new_state"]
            if new_state is None:
                return
            reader(new_state)
            self.async_write_ha_state()

        return _handle

    def _read_current_temp(self, state) -> None:
        """Read the measured water temperature."""
        if state.state in UNAVAILABLE_STATES:
            return
        try:
            self._attr_current_temperature = float(state.state)
        except (ValueError, TypeError):
            pass

    def _clamp(self, temp: float) -> float:
        """Hold a setpoint inside the helper's own range."""
        return min(max(temp, self._attr_min_temp), self._attr_max_temp)

    def _read_target_temp(self, state) -> None:
        """Read the setpoint and the range the helper allows."""
        # Range first, even when the state itself is unreadable: HA's HomeKit
        # bridge caches min/max when it builds the accessory, so a helper that
        # is briefly unavailable at startup must not leave the slider stuck on
        # the defaults for the rest of the session.
        attrs = state.attributes
        # A min of 0 is treated as "unset" by the bridge, which then substitutes
        # its own default and produces a broken range.
        min_temp = max(1, _as_float(attrs.get("min"), KETTLE_DEFAULT_MIN_TEMP))
        max_temp = _as_float(attrs.get("max"), KETTLE_DEFAULT_MAX_TEMP)
        if max_temp > min_temp:
            self._attr_min_temp = min_temp
            self._attr_max_temp = max_temp
        if (step := _as_float(attrs.get("step"), 0)) > 0:
            self._attr_target_temperature_step = step

        if state.state in UNAVAILABLE_STATES:
            return
        try:
            self._attr_target_temperature = self._clamp(float(state.state))
        except (ValueError, TypeError):
            pass

    async def async_set_temperature(self, **kwargs) -> None:
        """Push the setpoint to the target temperature helper."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None or not self._target_temp_entity:
            return
        # input_number and number both expose set_value(value), and both reject
        # an out-of-range value outright, so clamp rather than lose the write.
        await self.hass.services.async_call(
            self._target_temp_entity.split(".")[0],
            "set_value",
            {"entity_id": self._target_temp_entity, "value": self._clamp(temp)},
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Map Off/Heat onto the power entity."""
        # Generic turn_on/turn_off so a switch, input_boolean or fan all work.
        await self.hass.services.async_call(
            "homeassistant",
            "turn_off" if hvac_mode == HVACMode.OFF else "turn_on",
            {"entity_id": self._source_entity},
        )

    async def async_update_from_source(self, state) -> None:
        """Map the power entity state onto hvac mode and action."""
        if state.state in UNAVAILABLE_STATES:
            self._attr_available = False
            self.async_write_ha_state()
            return

        self._attr_available = True
        heating = state.state == STATE_ON
        self._attr_hvac_mode = HVACMode.HEAT if heating else HVACMode.OFF
        self._attr_hvac_action = HVACAction.HEATING if heating else HVACAction.OFF
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit Device climate proxies."""
    device_type = hass.data[DOMAIN][config_entry.entry_id]["device_type"]
    entities = []

    if device_type == "kettle":
        if power := config_entry.data.get(CONF_POWER_SWITCH):
            entities.append(
                HomeKitKettleClimate(
                    hass,
                    config_entry.entry_id,
                    power,
                    config_entry.data.get(CONF_CURRENT_TEMP),
                    config_entry.data.get(CONF_TARGET_TEMP),
                )
            )

    elif device_type == "electric_blanket":
        power = config_entry.data.get(CONF_POWER_SWITCH)
        zones = [z for z in (config_entry.data.get(CONF_ZONE_BODY),
                             config_entry.data.get(CONF_ZONE_FEET)) if z]
        for conf_key, label in ((CONF_ZONE_BODY, "Body"), (CONF_ZONE_FEET, "Feet")):
            if zone := config_entry.data.get(conf_key):
                entities.append(
                    HomeKitDeviceClimate(
                        hass,
                        config_entry.entry_id,
                        label,
                        zone,
                        power,
                        zones,
                    )
                )

    if entities:
        async_add_entities(entities)
