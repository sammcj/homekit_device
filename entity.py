"""Platform entities for HomeKit Device Aggregator."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_ON,
    STATE_OPENING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, CONF_NAME

class HomeKitDeviceEntity:
    """Representation of a HomeKit Device entity."""

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, entity_id: str) -> None:
        """Initialize the entity."""
        self.hass = hass
        self._entry_id = entry_id
        self._name = name
        self._source_entity = entity_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{entity_id}"
        self._attr_name = name
        self._attr_has_entity_name = True
        self.device_type = self.hass.data[DOMAIN][entry_id]["device_type"]
        device_name = self.hass.data[DOMAIN][entry_id]["config"][CONF_NAME]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{DOMAIN}_{entry_id}")},
            name=device_name,
            manufacturer="HomeKit Device Aggregator",
            model=self.device_type.title(),
            suggested_area="Kitchen" if self.device_type == "kettle" else None,
            via_device=(DOMAIN, f"{DOMAIN}_{entry_id}"),
        )
        self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to register update signal handler."""
        async def _handle_state_change(event: Event[EventStateChangedData]) -> None:
            new_state = event.data["new_state"]
            if new_state is None:
                return
            await self.async_update_from_source(new_state)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity],
                _handle_state_change,
            )
        )

        # Set initial state
        if state := self.hass.states.get(self._source_entity):
            await self.async_update_from_source(state)

    async def async_update_from_source(self, state) -> None:
        """Update the entity from the source entity state."""
        raise NotImplementedError

# Two-option selects are a common way for a device to expose a boolean. The
# labels vary by vendor, so match against the source's own options rather than
# assuming any particular pair.
TRUTHY_OPTIONS = {"true", "on", "yes", "enable", "enabled", "1"}
FALSEY_OPTIONS = {"false", "off", "no", "disable", "disabled", "0"}
SELECT_DOMAINS = ("select", "input_select")

class HomeKitDeviceSwitch(HomeKitDeviceEntity, SwitchEntity):
    """A switch proxy over a switch, input_boolean or two-option select source."""

    _attr_device_class = "switch"

    def __init__(
        self, hass: HomeAssistant, entry_id: str, name: str, entity_id: str
    ) -> None:
        """Initialize the switch."""
        super().__init__(hass, entry_id, name, entity_id)
        self._source_domain = entity_id.split(".")[0]
        self._on_option: str | None = None
        self._off_option: str | None = None

    @property
    def _source_is_select(self) -> bool:
        return self._source_domain in SELECT_DOMAINS

    def _read_options(self, state) -> None:
        """Work out which of the source's options mean on and off."""
        options = state.attributes.get("options") or []
        if len(options) < 2:
            return
        on = next((o for o in options if o.strip().casefold() in TRUTHY_OPTIONS), None)
        off = next((o for o in options if o.strip().casefold() in FALSEY_OPTIONS), None)
        if on is None and off is None:
            # Nothing recognised. Selects conventionally list the off state
            # first, so fall back to the ends rather than refusing to work.
            off, on = options[0], options[-1]
        elif on is None:
            on = next((o for o in reversed(options) if o != off), None)
        elif off is None:
            off = next((o for o in options if o != on), None)
        self._on_option, self._off_option = on, off

    async def _select_option(self, turn_on: bool) -> None:
        """Forward the on or off option to a select-backed source."""
        if self._on_option is None or self._off_option is None:
            # Options weren't readable when the state was last seen; try again
            # rather than silently dropping the command.
            if state := self.hass.states.get(self._source_entity):
                self._read_options(state)
        option = self._on_option if turn_on else self._off_option
        if option is None:
            return
        await self.hass.services.async_call(
            self._source_domain,
            "select_option",
            {"entity_id": self._source_entity, "option": option},
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        if self._source_is_select:
            await self._select_option(True)
            return
        # Generic service so a switch, input_boolean or light source all work.
        await self.hass.services.async_call(
            "homeassistant", "turn_on", {"entity_id": self._source_entity}
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        if self._source_is_select:
            await self._select_option(False)
            return
        await self.hass.services.async_call(
            "homeassistant", "turn_off", {"entity_id": self._source_entity}
        )

    async def async_update_from_source(self, state) -> None:
        """Update the entity from the source entity state."""
        if state.state == STATE_UNAVAILABLE:
            self._attr_available = False
            self.async_write_ha_state()
            return

        self._attr_available = True
        if self._source_is_select:
            self._read_options(state)
            # Compare against the on option, so an unknown state reads as off
            # rather than as "anything that isn't off".
            self._attr_is_on = (
                self._on_option is not None
                and state.state.casefold() == self._on_option.casefold()
            )
        else:
            self._attr_is_on = state.state == STATE_ON
        self.async_write_ha_state()

class HomeKitDeviceSensor(HomeKitDeviceEntity, SensorEntity):
    """Representation of a HomeKit Device sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        entity_id: str,
        unit: str | None = None,
        diagnostic: bool = False,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, entry_id, name, entity_id)
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = "temperature" if unit == UnitOfTemperature.CELSIUS else None
        # Diagnostic readouts are not controls. HA's HomeKit bridge skips any
        # entity with a category set, which also keeps them out of the Home app.
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_update_from_source(self, state) -> None:
        """Update the entity from the source entity state."""
        self._attr_native_value = state.state
        self.async_write_ha_state()

class HomeKitDeviceSelect(HomeKitDeviceEntity, SelectEntity):
    """Representation of a HomeKit Device select."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        entity_id: str,
        options: list[str],
    ) -> None:
        """Initialize the select."""
        super().__init__(hass, entry_id, name, entity_id)
        self._attr_options = options

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        await self.hass.services.async_call(
            "select", "select_option",
            {"entity_id": self._source_entity, "option": option}
        )

    async def async_update_from_source(self, state) -> None:
        """Update the entity from the source entity state."""
        self._attr_current_option = state.state
        self.async_write_ha_state()

class HomeKitDeviceFan(HomeKitDeviceEntity, FanEntity):
    """Representation of a HomeKit Device fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn the fan on."""
        data: dict[str, object] = {"entity_id": self._source_entity}
        if percentage is not None:
            data["percentage"] = percentage
        await self.hass.services.async_call("fan", "turn_on", data)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.hass.services.async_call(
            "fan", "turn_off", {"entity_id": self._source_entity}
        )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed percentage."""
        await self.hass.services.async_call(
            "fan",
            "set_percentage",
            {"entity_id": self._source_entity, "percentage": percentage},
        )

    async def async_update_from_source(self, state) -> None:
        """Update the entity from the source entity state."""
        self._attr_is_on = state.state == STATE_ON
        if (percentage := state.attributes.get("percentage")) is not None:
            self._attr_percentage = percentage
        self.async_write_ha_state()

LIFT_FEATURES = (
    CoverEntityFeature.OPEN
    | CoverEntityFeature.CLOSE
    | CoverEntityFeature.STOP
    | CoverEntityFeature.SET_POSITION
)

TILT_FEATURES = (
    CoverEntityFeature.OPEN_TILT
    | CoverEntityFeature.CLOSE_TILT
    | CoverEntityFeature.STOP_TILT
    | CoverEntityFeature.SET_TILT_POSITION
)

# A tilt source without its own tilt characteristics is driven through its lift
# services instead, so its lift features become our tilt features.
LIFT_TO_TILT_FEATURE = {
    CoverEntityFeature.OPEN: CoverEntityFeature.OPEN_TILT,
    CoverEntityFeature.CLOSE: CoverEntityFeature.CLOSE_TILT,
    CoverEntityFeature.STOP: CoverEntityFeature.STOP_TILT,
    CoverEntityFeature.SET_POSITION: CoverEntityFeature.SET_TILT_POSITION,
}

UNREADABLE_STATES = (STATE_UNAVAILABLE, STATE_UNKNOWN)

class HomeKitDeviceCover(HomeKitDeviceEntity, CoverEntity):
    """A cover that merges a separate lift entity and tilt entity into one."""

    _attr_device_class = CoverDeviceClass.SHUTTER

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        lift_entity: str,
        tilt_entity: str | None = None,
    ) -> None:
        """Initialize the cover."""
        super().__init__(hass, entry_id, name, lift_entity)
        self._tilt_entity = tilt_entity
        # The cover is the device's only entity, so it takes the device's name.
        self._attr_name = None

        # Optimistic defaults; replaced by whatever the sources actually
        # support as soon as their states can be read.
        self._lift_features = LIFT_FEATURES
        self._tilt_features = TILT_FEATURES if tilt_entity else CoverEntityFeature(0)
        self._update_features()

        # True when the tilt source has its own tilt characteristics; false when
        # it is a second cover whose lift position actually drives the slats.
        self._tilt_is_native = False

    def _update_features(self) -> None:
        """Recompute supported features from both sources."""
        self._attr_supported_features = self._lift_features | self._tilt_features

    async def async_added_to_hass(self) -> None:
        """Track both source entities."""
        # Seed tilt first so the state write in the base class carries it.
        if self._tilt_entity and (state := self.hass.states.get(self._tilt_entity)):
            self._read_tilt(state)

        await super().async_added_to_hass()

        if not self._tilt_entity:
            return

        async def _handle_tilt_change(event: Event[EventStateChangedData]) -> None:
            new_state = event.data["new_state"]
            if new_state is None:
                return
            self._read_tilt(new_state)
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._tilt_entity],
                _handle_tilt_change,
            )
        )

    def _read_tilt(self, state) -> None:
        """Read the tilt position and capabilities from the tilt source state."""
        if state.state in UNREADABLE_STATES:
            # Keep the last known good values rather than flipping the routing.
            return

        features = CoverEntityFeature(state.attributes.get(ATTR_SUPPORTED_FEATURES, 0))
        self._tilt_is_native = bool(features & CoverEntityFeature.SET_TILT_POSITION)

        if self._tilt_is_native:
            self._tilt_features = features & TILT_FEATURES
            self._attr_current_cover_tilt_position = state.attributes.get(
                ATTR_CURRENT_TILT_POSITION
            )
        else:
            self._tilt_features = CoverEntityFeature(0)
            for lift_feature, tilt_feature in LIFT_TO_TILT_FEATURE.items():
                if features & lift_feature:
                    self._tilt_features |= tilt_feature
            self._attr_current_cover_tilt_position = state.attributes.get(
                ATTR_CURRENT_POSITION
            )

        self._update_features()

    async def _call_lift(self, service: str, **data) -> None:
        await self.hass.services.async_call(
            "cover", service, {"entity_id": self._source_entity, **data}
        )

    async def _call_tilt(self, native_service: str, lift_service: str, **data) -> None:
        """Call the tilt source, falling back to lift services when it has no tilt."""
        if not self._tilt_entity:
            return
        if self._tilt_is_native:
            service, payload = native_service, data
        else:
            service = lift_service
            payload = (
                {ATTR_POSITION: data[ATTR_TILT_POSITION]}
                if ATTR_TILT_POSITION in data
                else {}
            )
        await self.hass.services.async_call(
            "cover", service, {"entity_id": self._tilt_entity, **payload}
        )

    async def async_open_cover(self, **kwargs) -> None:
        """Open the cover."""
        await self._call_lift("open_cover")

    async def async_close_cover(self, **kwargs) -> None:
        """Close the cover."""
        await self._call_lift("close_cover")

    async def async_stop_cover(self, **kwargs) -> None:
        """Stop the cover."""
        await self._call_lift("stop_cover")

    async def async_set_cover_position(self, **kwargs) -> None:
        """Set the cover position."""
        await self._call_lift("set_cover_position", position=kwargs[ATTR_POSITION])

    async def async_open_cover_tilt(self, **kwargs) -> None:
        """Open the tilt."""
        await self._call_tilt("open_cover_tilt", "open_cover")

    async def async_close_cover_tilt(self, **kwargs) -> None:
        """Close the tilt."""
        await self._call_tilt("close_cover_tilt", "close_cover")

    async def async_stop_cover_tilt(self, **kwargs) -> None:
        """Stop the tilt."""
        await self._call_tilt("stop_cover_tilt", "stop_cover")

    async def async_set_cover_tilt_position(self, **kwargs) -> None:
        """Set the tilt position."""
        await self._call_tilt(
            "set_cover_tilt_position",
            "set_cover_position",
            tilt_position=kwargs[ATTR_TILT_POSITION],
        )

    async def async_update_from_source(self, state) -> None:
        """Update the lift half from the source entity state."""
        if state.state in UNREADABLE_STATES:
            # Reporting a stale position as "open" would be worse than nothing.
            self._attr_available = False
            self._attr_is_closed = None
            self.async_write_ha_state()
            return

        self._attr_available = True
        self._lift_features = (
            CoverEntityFeature(state.attributes.get(ATTR_SUPPORTED_FEATURES, 0))
            & LIFT_FEATURES
        )
        self._update_features()

        self._attr_current_cover_position = state.attributes.get(ATTR_CURRENT_POSITION)
        self._attr_is_closed = state.state == STATE_CLOSED
        self._attr_is_opening = state.state == STATE_OPENING
        self._attr_is_closing = state.state == STATE_CLOSING
        self.async_write_ha_state()
