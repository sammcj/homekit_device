"""Tests for the shutter proxy, which merges a lift cover and a tilt cover.

Every case here is a trap the shutter implementation has to avoid rather than a
happy path: mirroring the sources' capabilities instead of asserting them, and
not letting an unavailable source silently reroute a command to the wrong axis.
"""
from __future__ import annotations

import pytest
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntityFeature,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_CLOSED,
    STATE_OPEN,
    STATE_UNAVAILABLE,
)

LIFT = "cover.source_lift"
TILT = "cover.source_tilt"

LIFT_FULL = (
    CoverEntityFeature.OPEN
    | CoverEntityFeature.CLOSE
    | CoverEntityFeature.STOP
    | CoverEntityFeature.SET_POSITION
)
TILT_FULL = (
    CoverEntityFeature.OPEN_TILT
    | CoverEntityFeature.CLOSE_TILT
    | CoverEntityFeature.STOP_TILT
    | CoverEntityFeature.SET_TILT_POSITION
)


@pytest.fixture
def shutter(hass, setup_device, created_entities):
    """Set up a shutter and hand back its single cover entity id."""

    async def _setup(*, tilt: str | None = TILT):
        options = {"lift_cover": LIFT}
        if tilt:
            options["tilt_cover"] = tilt
        entry = await setup_device("shutter", "Test Shutter", **options)
        covers = created_entities(entry, "cover")
        assert len(covers) == 1, f"expected one merged cover, got {covers}"
        return covers[0]

    return _setup


def set_lift(hass, state=STATE_OPEN, features=LIFT_FULL, position=50):
    """Publish a lift source state."""
    attributes = {ATTR_SUPPORTED_FEATURES: int(features)}
    if position is not None:
        attributes[ATTR_CURRENT_POSITION] = position
    hass.states.async_set(LIFT, state, attributes)


def set_tilt(hass, state=STATE_OPEN, features=TILT_FULL, **attributes):
    """Publish a tilt source state."""
    hass.states.async_set(
        TILT, state, {ATTR_SUPPORTED_FEATURES: int(features), **attributes}
    )


def calls_to(service_calls, entity_id):
    """The (domain, service, data) triples aimed at one entity."""
    return [
        (call.domain, call.service, call.data)
        for call in service_calls
        if call.data.get(ATTR_ENTITY_ID) == entity_id
    ]


async def test_optimistic_features_before_any_source_state(hass, shutter):
    """A shutter set up before its sources exist must still produce an entity.

    Home Assistant restores integrations in a non-deterministic order, so the
    lift source is routinely missing at the moment the proxy is added. The
    entity has to survive that first state write and advertise the optimistic
    defaults until the sources can be read.
    """
    entity_id = await shutter()

    state = hass.states.get(entity_id)
    assert state is not None, "the cover never made it into the state machine"
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == int(LIFT_FULL | TILT_FULL)


async def test_lift_features_are_mirrored_not_asserted(hass, shutter):
    """A lift source without SET_POSITION must not advertise a position slider.

    HA registers cover.set_cover_position with required_features, so claiming
    the capability makes every drag of the HomeKit slider raise
    ServiceNotSupported against the source.
    """
    set_lift(
        hass,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        position=None,
    )
    entity_id = await shutter(tilt=None)
    await hass.async_block_till_done()

    features = hass.states.get(entity_id).attributes[ATTR_SUPPORTED_FEATURES]
    assert not features & CoverEntityFeature.SET_POSITION
    assert features & CoverEntityFeature.OPEN
    assert features & CoverEntityFeature.CLOSE


async def test_tilt_features_are_mirrored_from_the_tilt_source(hass, shutter):
    """A tilt source that cannot stop must not advertise STOP_TILT."""
    set_lift(hass)
    set_tilt(
        hass,
        features=(
            CoverEntityFeature.OPEN_TILT
            | CoverEntityFeature.CLOSE_TILT
            | CoverEntityFeature.SET_TILT_POSITION
        ),
        current_tilt_position=20,
    )
    entity_id = await shutter()
    await hass.async_block_till_done()

    features = hass.states.get(entity_id).attributes[ATTR_SUPPORTED_FEATURES]
    assert not features & CoverEntityFeature.STOP_TILT
    assert features & CoverEntityFeature.SET_TILT_POSITION


async def test_tilt_native_detection_uses_the_feature_bit(
    hass, shutter, get_entity, service_calls
):
    """Tilt routing keys off SET_TILT_POSITION, not a stray tilt attribute.

    A cover can report current_tilt_position while offering no tilt services at
    all; treating that attribute as proof of tilt support sends every tilt
    command to a service the source does not implement.
    """
    set_lift(hass)
    set_tilt(
        hass,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        current_tilt_position=42,
        current_position=17,
    )
    entity_id = await shutter()
    await hass.async_block_till_done()

    entity = get_entity(entity_id)
    assert entity._tilt_is_native is False
    # Non-native tilt reads the lift position of the tilt source, not the
    # decorative current_tilt_position attribute.
    assert hass.states.get(entity_id).attributes[ATTR_CURRENT_TILT_POSITION] == 17


async def test_native_tilt_routes_to_tilt_services(hass, shutter, service_calls):
    """A tilt-capable source is driven through cover.set_cover_tilt_position."""
    set_lift(hass)
    set_tilt(hass, current_tilt_position=30)
    entity_id = await shutter()
    await hass.async_block_till_done()

    await hass.services.async_call(
        "cover",
        "set_cover_tilt_position",
        {ATTR_ENTITY_ID: entity_id, ATTR_TILT_POSITION: 70},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert calls_to(service_calls, TILT) == [
        ("cover", "set_cover_tilt_position", {ATTR_ENTITY_ID: TILT, ATTR_TILT_POSITION: 70})
    ]


async def test_non_native_tilt_routes_to_lift_services(hass, shutter, service_calls):
    """A position-only second cover is driven through cover.set_cover_position.

    Slat angle on this hardware is a second motor with no tilt services, so the
    tilt half of the accessory has to be translated back onto lift services and
    ATTR_POSITION, aimed at the tilt entity rather than the lift entity.
    """
    set_lift(hass)
    set_tilt(
        hass,
        features=(
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        ),
        current_position=25,
    )
    entity_id = await shutter()
    await hass.async_block_till_done()

    await hass.services.async_call(
        "cover",
        "set_cover_tilt_position",
        {ATTR_ENTITY_ID: entity_id, ATTR_TILT_POSITION: 70},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert calls_to(service_calls, TILT) == [
        ("cover", "set_cover_position", {ATTR_ENTITY_ID: TILT, ATTR_POSITION: 70})
    ]
    assert calls_to(service_calls, LIFT) == []


async def test_non_native_tilt_open_close_route_to_lift_services(
    hass, shutter, service_calls
):
    """Open/close tilt on a position-only source use open_cover/close_cover."""
    set_lift(hass)
    set_tilt(
        hass,
        features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        current_position=25,
    )
    entity_id = await shutter()
    await hass.async_block_till_done()

    await hass.services.async_call(
        "cover", "open_cover_tilt", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert calls_to(service_calls, TILT) == [
        ("cover", "open_cover", {ATTR_ENTITY_ID: TILT})
    ]


async def test_unavailable_tilt_source_latches_and_keeps_routing(
    hass, shutter, get_entity, service_calls
):
    """An unavailable tilt source must not flip the routing to the lift axis.

    Reading supported_features off an unavailable state yields 0, which reads
    as "not tilt native" and would send the next tilt command down the lift
    services of the tilt entity - the wrong motor.
    """
    set_lift(hass)
    set_tilt(hass, current_tilt_position=30)
    entity_id = await shutter()
    await hass.async_block_till_done()

    set_tilt(hass, state=STATE_UNAVAILABLE, features=0)
    await hass.async_block_till_done()

    entity = get_entity(entity_id)
    assert entity._tilt_is_native is True
    assert hass.states.get(entity_id).attributes[ATTR_CURRENT_TILT_POSITION] == 30
    assert hass.states.get(entity_id).attributes[ATTR_SUPPORTED_FEATURES] & (
        CoverEntityFeature.SET_TILT_POSITION
    )

    await hass.services.async_call(
        "cover",
        "set_cover_tilt_position",
        {ATTR_ENTITY_ID: entity_id, ATTR_TILT_POSITION: 70},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert calls_to(service_calls, TILT) == [
        ("cover", "set_cover_tilt_position", {ATTR_ENTITY_ID: TILT, ATTR_TILT_POSITION: 70})
    ]


async def test_unavailable_lift_source_is_not_reported_as_open(
    hass, shutter, get_entity
):
    """An unreadable lift source gives is_closed = None and available = False.

    is_closed is asserted on the entity rather than through the state machine,
    because available = False masks the state either way - a stale is_closed of
    False would survive unnoticed and then be published the moment the source
    came back available without having republished its position.
    """
    set_lift(hass, state=STATE_CLOSED, position=0)
    entity_id = await shutter(tilt=None)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_CLOSED
    assert get_entity(entity_id).is_closed is True

    set_lift(hass, state=STATE_UNAVAILABLE, position=None)
    await hass.async_block_till_done()

    entity = get_entity(entity_id)
    assert entity.is_closed is None
    assert entity.available is False
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


async def test_lift_commands_target_the_lift_entity(hass, shutter, service_calls):
    """Lift commands go to the lift source and never to the tilt source."""
    set_lift(hass)
    set_tilt(hass, current_tilt_position=30)
    entity_id = await shutter()
    await hass.async_block_till_done()

    await hass.services.async_call(
        "cover",
        "set_cover_position",
        {ATTR_ENTITY_ID: entity_id, ATTR_POSITION: 80},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert calls_to(service_calls, LIFT) == [
        ("cover", "set_cover_position", {ATTR_ENTITY_ID: LIFT, ATTR_POSITION: 80})
    ]
    assert calls_to(service_calls, TILT) == []


async def test_the_cover_takes_the_device_name(hass, shutter):
    """The cover is the device's only entity, so it must not double up its name.

    Leaving _attr_name set would give "Test Shutter Test Shutter" in the Home
    app, since has_entity_name already prefixes the device name.
    """
    set_lift(hass)
    entity_id = await shutter(tilt=None)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).attributes["friendly_name"] == "Test Shutter"


async def test_no_tilt_source_advertises_no_tilt_features(hass, shutter):
    """Without a tilt entity the accessory must not offer a tilt control."""
    set_lift(hass)
    entity_id = await shutter(tilt=None)
    await hass.async_block_till_done()

    features = hass.states.get(entity_id).attributes[ATTR_SUPPORTED_FEATURES]
    assert not features & TILT_FULL
