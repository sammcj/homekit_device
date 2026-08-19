"""Tests for the kettle thermostat proxy.

The kettle folds power, current temperature and target temperature into one
climate entity so the bridge builds one accessory instead of three. The traps
are all in how the target temperature helper's range is read: the bridge caches
min/max at the moment it builds the accessory, so getting the range wrong once
at startup freezes the slider for the whole session.
"""
from __future__ import annotations

import pytest
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_STEP,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    EVENT_STATE_CHANGED,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import callback

from custom_components.homekit_device.climate import (
    KETTLE_DEFAULT_MAX_TEMP,
    KETTLE_DEFAULT_MIN_TEMP,
    _as_float,
)

POWER = "switch.kettle_power"
CURRENT = "sensor.kettle_temperature"
TARGET = "input_number.kettle_target"


@pytest.fixture
def kettle(hass, setup_device, created_entities):
    """Set up a kettle and hand back its climate entity id."""

    async def _setup(**options):
        config = {
            "power_switch": POWER,
            "current_temperature": CURRENT,
            "target_temperature": TARGET,
            **options,
        }
        entry = await setup_device("kettle", "Test Kettle", **config)
        climates = created_entities(entry, "climate")
        assert len(climates) == 1, f"expected one thermostat, got {climates}"
        return climates[0]

    return _setup


def set_target_helper(hass, state="80", **attributes):
    """Publish a target temperature helper state."""
    hass.states.async_set(TARGET, state, attributes)


# _as_float


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(42, 42.0, id="int"),
        pytest.param("42.5", 42.5, id="numeric-string"),
        pytest.param(None, 7.0, id="none"),
        pytest.param("", 7.0, id="empty-string"),
        pytest.param("unknown", 7.0, id="junk-string"),
        pytest.param([], 7.0, id="wrong-type"),
    ],
)
def test_as_float_never_raises(value, expected):
    """A present-but-None attribute must fall back, not raise.

    _read_target_temp runs inside a state change listener; an exception there
    escapes the callback and the update is lost rather than logged usefully.
    """
    assert _as_float(value, 7.0) == expected


# Range handling


async def test_range_is_read_from_an_unavailable_helper(hass, kettle):
    """min/max/step are taken from the helper's attributes even when it is down.

    localtuya helpers come back unavailable for a moment after a restart, which
    is exactly when the bridge is building the accessory and caching the range.
    """
    set_target_helper(hass, STATE_UNAVAILABLE, min=55, max=95, step=5)
    entity_id = await kettle()
    await hass.async_block_till_done()

    attributes = hass.states.get(entity_id).attributes
    assert attributes[ATTR_MIN_TEMP] == 55
    assert attributes[ATTR_MAX_TEMP] == 95
    assert attributes[ATTR_TARGET_TEMP_STEP] == 5


async def test_none_valued_attributes_fall_back_to_defaults(hass, kettle):
    """Attribute keys present with a None value must not lose the update."""
    set_target_helper(hass, "70", min=None, max=None, step=None)
    entity_id = await kettle()
    await hass.async_block_till_done()

    attributes = hass.states.get(entity_id).attributes
    assert attributes[ATTR_MIN_TEMP] == KETTLE_DEFAULT_MIN_TEMP
    assert attributes[ATTR_MAX_TEMP] == KETTLE_DEFAULT_MAX_TEMP
    assert attributes[ATTR_TEMPERATURE] == 70


async def test_inverted_range_is_rejected(hass, kettle):
    """max <= min would give the bridge a nonsensical slider, so keep defaults."""
    set_target_helper(hass, "70", min=90, max=50)
    entity_id = await kettle()
    await hass.async_block_till_done()

    attributes = hass.states.get(entity_id).attributes
    assert attributes[ATTR_MIN_TEMP] == KETTLE_DEFAULT_MIN_TEMP
    assert attributes[ATTR_MAX_TEMP] == KETTLE_DEFAULT_MAX_TEMP


async def test_equal_min_and_max_is_rejected(hass, kettle):
    """A degenerate range is no more usable than an inverted one."""
    set_target_helper(hass, "70", min=60, max=60)
    entity_id = await kettle()
    await hass.async_block_till_done()

    attributes = hass.states.get(entity_id).attributes
    assert attributes[ATTR_MIN_TEMP] == KETTLE_DEFAULT_MIN_TEMP
    assert attributes[ATTR_MAX_TEMP] == KETTLE_DEFAULT_MAX_TEMP


async def test_zero_minimum_is_clamped_to_one(hass, kettle):
    """The bridge reads a min of 0 as "unset" and substitutes its own default."""
    set_target_helper(hass, "40", min=0, max=100)
    entity_id = await kettle()
    await hass.async_block_till_done()

    attributes = hass.states.get(entity_id).attributes
    assert attributes[ATTR_MIN_TEMP] == 1
    assert attributes[ATTR_MAX_TEMP] == 100


async def test_zero_step_is_ignored(hass, kettle):
    """A step of 0 would make the slider unusable, so keep the default."""
    set_target_helper(hass, "70", min=40, max=100, step=0)
    entity_id = await kettle()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).attributes[ATTR_TARGET_TEMP_STEP] == 1


# Setpoints


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        pytest.param(150, 95.0, id="above-max"),
        pytest.param(10, 55.0, id="below-min"),
        pytest.param(80, 80.0, id="in-range"),
    ],
)
async def test_setpoint_is_clamped_before_the_write(
    hass, kettle, get_entity, service_calls, stub_service, requested, expected
):
    """input_number rejects an out-of-range value outright, so clamp first.

    Called on the entity rather than through climate.set_temperature, because
    HA's own service validation rejects an out-of-range value before the entity
    ever sees it. The clamp guards the path where the helper narrows its range
    after the bridge has already cached the wider one.
    """
    stub_service("input_number", "set_value")
    set_target_helper(hass, "80", min=55, max=95)
    entity_id = await kettle()
    await hass.async_block_till_done()

    await get_entity(entity_id).async_set_temperature(temperature=requested)
    await hass.async_block_till_done()

    writes = [
        call.data
        for call in service_calls
        if call.data.get(ATTR_ENTITY_ID) == TARGET and call.service == "set_value"
    ]
    assert writes == [{ATTR_ENTITY_ID: TARGET, "value": expected}]


async def test_setpoint_without_a_temperature_is_ignored(
    hass, kettle, get_entity, service_calls, stub_service
):
    """A set_temperature call carrying no temperature must not write anything."""
    stub_service("input_number", "set_value")
    set_target_helper(hass, "80", min=55, max=95)
    entity_id = await kettle()
    await hass.async_block_till_done()

    await get_entity(entity_id).async_set_temperature(hvac_mode=HVACMode.HEAT)
    await hass.async_block_till_done()

    assert [call for call in service_calls if call.service == "set_value"] == []


async def test_setpoint_is_written_to_the_helpers_own_domain(
    hass, setup_device, created_entities, service_calls, stub_service
):
    """A number.* helper gets number.set_value, not input_number.set_value."""
    target = "number.kettle_target"
    hass.states.async_set(target, "80", {"min": 40, "max": 100})
    entry = await setup_device(
        "kettle", "Test Kettle", power_switch=POWER, target_temperature=target
    )
    entity_id = created_entities(entry, "climate")[0]
    await hass.async_block_till_done()

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {ATTR_ENTITY_ID: entity_id, ATTR_TEMPERATURE: 90},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert [
        (call.domain, call.service)
        for call in service_calls
        if call.data.get(ATTR_ENTITY_ID) == target
    ] == [("number", "set_value")]


async def test_no_target_helper_means_no_temperature_control(
    hass, setup_device, created_entities
):
    """Without a setpoint helper the accessory must not offer a slider."""
    entry = await setup_device("kettle", "Test Kettle", power_switch=POWER)
    entity_id = created_entities(entry, "climate")[0]

    features = hass.states.get(entity_id).attributes[ATTR_SUPPORTED_FEATURES]
    assert not features & ClimateEntityFeature.TARGET_TEMPERATURE
    assert features & ClimateEntityFeature.TURN_ON


# Power


@pytest.mark.parametrize(
    ("mode", "expected_service"),
    [
        pytest.param(HVACMode.HEAT, "turn_on", id="heat"),
        pytest.param(HVACMode.OFF, "turn_off", id="off"),
    ],
)
async def test_hvac_mode_drives_the_power_entity_generically(
    hass, kettle, service_calls, stub_service, mode, expected_service
):
    """Power is switched with homeassistant.turn_on/off so any domain works."""
    stub_service("homeassistant", "turn_on", "turn_off")
    set_target_helper(hass)
    entity_id = await kettle()
    await hass.async_block_till_done()

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {ATTR_ENTITY_ID: entity_id, ATTR_HVAC_MODE: mode},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert [
        (call.domain, call.service)
        for call in service_calls
        if call.data.get(ATTR_ENTITY_ID) == POWER
    ] == [("homeassistant", expected_service)]


@pytest.mark.parametrize(
    ("power_state", "mode", "action"),
    [
        pytest.param(STATE_ON, HVACMode.HEAT, HVACAction.HEATING, id="on"),
        pytest.param(STATE_OFF, HVACMode.OFF, HVACAction.OFF, id="off"),
    ],
)
async def test_power_state_maps_to_mode_and_action(
    hass, kettle, power_state, mode, action
):
    """hvac_action is what the Home app shows as "Heating" under the tile."""
    set_target_helper(hass)
    entity_id = await kettle()
    hass.states.async_set(POWER, power_state)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == mode
    assert state.attributes[ATTR_HVAC_ACTION] == action


async def test_unavailable_power_entity_makes_the_kettle_unavailable(hass, kettle):
    """A kettle whose power entity is down must not report a stale mode."""
    set_target_helper(hass)
    entity_id = await kettle()
    hass.states.async_set(POWER, STATE_ON)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == HVACMode.HEAT

    hass.states.async_set(POWER, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


# Seeding order


async def test_temperatures_are_seeded_before_the_first_state_write(hass, kettle):
    """The very first state written must already carry both temperatures.

    The base class writes state from inside async_added_to_hass, so reading the
    temperature sources after calling super() would publish a thermostat with no
    temperatures at all - and that first write is what the bridge sees.
    """
    hass.states.async_set(POWER, STATE_ON)
    hass.states.async_set(CURRENT, "63.5")
    set_target_helper(hass, "88", min=40, max=100)

    writes: list = []

    @callback
    def _record(event) -> None:
        if event.data["new_state"] is not None and event.data["entity_id"].startswith(
            "climate."
        ):
            writes.append(event.data["new_state"])

    hass.bus.async_listen(EVENT_STATE_CHANGED, _record)

    await kettle()
    await hass.async_block_till_done()

    assert writes, "the thermostat never wrote a state"
    first = writes[0]
    assert first.attributes[ATTR_CURRENT_TEMPERATURE] == 63.5
    assert first.attributes[ATTR_TEMPERATURE] == 88
    assert first.state == HVACMode.HEAT


async def test_current_temperature_follows_the_sensor(hass, kettle):
    """Later sensor updates reach the thermostat."""
    hass.states.async_set(CURRENT, "20")
    set_target_helper(hass)
    entity_id = await kettle()
    await hass.async_block_till_done()

    hass.states.async_set(CURRENT, "97.2")
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).attributes[ATTR_CURRENT_TEMPERATURE] == 97.2


async def test_junk_sensor_readings_are_ignored(hass, kettle):
    """A sensor that goes unknown must not wipe the last good reading."""
    hass.states.async_set(CURRENT, "55")
    set_target_helper(hass)
    entity_id = await kettle()
    await hass.async_block_till_done()

    hass.states.async_set(CURRENT, "unknown")
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).attributes[ATTR_CURRENT_TEMPERATURE] == 55
