"""Tests for the sensor and switch proxies in entity.py.

The diagnostic-category cases are the highest value tests in this suite. The
HomeKit bridge decides whether to build an accessory for an entity by looking at
its entity category, so a diagnostic sensor that loses its category quietly
becomes an extra tile in the Home app - exactly the duplication this
integration exists to remove. An earlier revision reset the category to None
inside the temperature branch, which defeated it for the one sensor that most
needed it.
"""
from __future__ import annotations

import pytest
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.helpers import entity_registry as er

from custom_components.homekit_device.entity import HomeKitDeviceSensor

SOURCE = "sensor.kettle_temp"


@pytest.fixture
async def entry_id(setup_device):
    """A minimal config entry, so the proxies can read their device info."""
    entry = await setup_device("kettle", "Test Kettle", power_switch="switch.kettle")
    return entry.entry_id


@pytest.mark.parametrize(
    "unit",
    [
        pytest.param(UnitOfTemperature.CELSIUS, id="celsius"),
        pytest.param(UnitOfTemperature.FAHRENHEIT, id="fahrenheit"),
        pytest.param("%", id="percent"),
        pytest.param("min", id="minutes"),
        pytest.param(None, id="no-unit"),
    ],
)
async def test_diagnostic_sensor_always_carries_the_category(hass, entry_id, unit):
    """diagnostic=True must set the category for every unit, temperature included."""
    sensor = HomeKitDeviceSensor(
        hass, entry_id, "Temperature", "sensor.source", unit, diagnostic=True
    )

    assert sensor.entity_category is EntityCategory.DIAGNOSTIC


async def test_celsius_sensor_keeps_both_category_and_device_class(hass, entry_id):
    """Setting the temperature device class must not cost the category."""
    sensor = HomeKitDeviceSensor(
        hass,
        entry_id,
        "Temperature",
        "sensor.source",
        UnitOfTemperature.CELSIUS,
        diagnostic=True,
    )

    assert sensor.device_class == "temperature"
    assert sensor.entity_category is EntityCategory.DIAGNOSTIC


async def test_only_celsius_gets_the_temperature_device_class(hass, entry_id):
    """The device class is keyed off °C specifically, so pin the other units."""
    for unit in (UnitOfTemperature.FAHRENHEIT, "%", "min", None):
        sensor = HomeKitDeviceSensor(
            hass, entry_id, "Readout", "sensor.source", unit, diagnostic=True
        )
        assert sensor.device_class is None, f"unexpected device class for {unit}"


async def test_non_diagnostic_sensor_has_no_category(hass, entry_id):
    """A sensor the user does want in HomeKit must stay uncategorised."""
    sensor = HomeKitDeviceSensor(
        hass, entry_id, "Humidity", "sensor.source", "%", diagnostic=False
    )

    assert sensor.entity_category is None


async def test_kettle_temperature_sensor_is_registered_as_diagnostic(
    hass, setup_device
):
    """End to end: the kettle's own °C readout reaches the registry categorised."""
    entry = await setup_device(
        "kettle",
        "Test Kettle",
        power_switch="switch.kettle",
        current_temperature="sensor.kettle_temp",
    )

    registry = er.async_get(hass)
    temperature = next(
        registry_entry
        for registry_entry in er.async_entries_for_config_entry(
            registry, entry.entry_id
        )
        if registry_entry.domain == "sensor"
    )
    assert temperature.entity_category is EntityCategory.DIAGNOSTIC


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("switch.keep_warm", id="switch-source"),
        pytest.param("input_boolean.keep_warm", id="input-boolean-source"),
    ],
)
async def test_switch_forwards_the_generic_homeassistant_services(
    hass, setup_device, created_entities, service_calls, stub_service, source
):
    """The switch proxy must call homeassistant.turn_on, not switch.turn_on.

    Keep warm is routinely an input_boolean rather than a switch, and
    switch.turn_on against an input_boolean does nothing at all.
    """
    stub_service("homeassistant", "turn_on", "turn_off")
    hass.states.async_set(source, STATE_OFF)
    entry = await setup_device(
        "kettle", "Test Kettle", power_switch="switch.kettle", keep_warm_mode=source
    )
    switches = created_entities(entry, "switch")
    assert len(switches) == 1, f"expected only the keep warm switch, got {switches}"
    proxy = switches[0]

    await hass.services.async_call(
        "switch", "turn_on", {ATTR_ENTITY_ID: proxy}, blocking=True
    )
    await hass.services.async_call(
        "switch", "turn_off", {ATTR_ENTITY_ID: proxy}, blocking=True
    )
    await hass.async_block_till_done()

    forwarded = [
        (call.domain, call.service, call.data.get(ATTR_ENTITY_ID))
        for call in service_calls
        if call.data.get(ATTR_ENTITY_ID) == source
    ]
    assert forwarded == [
        ("homeassistant", "turn_on", source),
        ("homeassistant", "turn_off", source),
    ]


async def test_switch_mirrors_the_source_state(
    hass, setup_device, created_entities
):
    """The proxy follows the source rather than its own last command."""
    source = "input_boolean.keep_warm"
    hass.states.async_set(source, STATE_OFF)
    entry = await setup_device(
        "kettle", "Test Kettle", power_switch="switch.kettle", keep_warm_mode=source
    )
    proxy = created_entities(entry, "switch")[0]
    assert hass.states.get(proxy).state == STATE_OFF

    hass.states.async_set(source, STATE_ON)
    await hass.async_block_till_done()

    assert hass.states.get(proxy).state == STATE_ON


@pytest.fixture
async def numeric_sensor(hass, setup_device, created_entities):
    """A kettle temperature proxy, which carries a numeric device class."""

    async def _setup(initial: str = "62.5"):
        hass.states.async_set(SOURCE, initial, {"unit_of_measurement": "°C"})
        entry = await setup_device(
            "kettle",
            "Test Kettle",
            power_switch="switch.kettle",
            current_temperature=SOURCE,
        )
        return created_entities(entry, "sensor")[0]

    return _setup


@pytest.mark.parametrize(
    ("source_state", "expected"),
    [
        pytest.param(STATE_UNKNOWN, STATE_UNKNOWN, id="unknown"),
        pytest.param(STATE_UNAVAILABLE, STATE_UNAVAILABLE, id="unavailable"),
        pytest.param("", STATE_UNKNOWN, id="empty-string"),
        pytest.param("None", STATE_UNKNOWN, id="literal-none"),
        pytest.param("err", STATE_UNKNOWN, id="device-error-text"),
        pytest.param("nan", STATE_UNKNOWN, id="nan"),
        pytest.param("inf", STATE_UNKNOWN, id="inf"),
        pytest.param("-inf", STATE_UNKNOWN, id="negative-inf"),
    ],
)
async def test_non_numeric_source_does_not_break_a_numeric_sensor(
    hass, numeric_sensor, source_state, expected
):
    """A °C proxy must never forward a value HA will reject.

    HA validates the value of any sensor carrying a numeric device class, and
    the ValueError is raised inside the state write: the update is dropped, the
    proxy keeps showing a stale reading, and the log fills up every time the
    source misbehaves. "unknown" is only the most common of these - an empty
    string or a short error string is just as routine.
    """
    proxy = await numeric_sensor()
    assert hass.states.get(proxy).state == "62.5"

    hass.states.async_set(SOURCE, source_state)
    await hass.async_block_till_done()

    assert hass.states.get(proxy).state == expected


async def test_numeric_sensor_forwards_the_reading_verbatim(hass, numeric_sensor):
    """A good reading passes through unchanged, trailing zeros and all."""
    proxy = await numeric_sensor("62")

    assert hass.states.get(proxy).state == "62"


async def test_free_text_sensor_still_forwards_its_string(
    hass, setup_device, created_entities
):
    """The numeric guard must not blank out a status or fault readout."""
    source = "sensor.kettle_fault"
    hass.states.async_set(source, "Lid open")
    entry = await setup_device(
        "kettle", "Test Kettle", power_switch="switch.kettle", fault_status=source
    )
    proxy = created_entities(entry, "sensor")[0]

    assert hass.states.get(proxy).state == "Lid open"

    hass.states.async_set(source, STATE_UNKNOWN)
    await hass.async_block_till_done()

    assert hass.states.get(proxy).state == STATE_UNKNOWN


@pytest.mark.parametrize(
    ("options", "on_option", "off_option"),
    [
        pytest.param(["off", "on"], "on", "off", id="lowercase"),
        pytest.param(["Disabled", "Enabled"], "Enabled", "Disabled", id="enable-words"),
        pytest.param(["False", "True"], "True", "False", id="booleans"),
        pytest.param(["No", "Yes"], "Yes", "No", id="yes-no"),
        pytest.param(["Standby", "Warming"], "Warming", "Standby", id="unrecognised"),
    ],
)
async def test_select_backed_switch_maps_its_own_option_labels(
    hass, setup_device, created_entities, service_calls, options, on_option, off_option
):
    """Keep warm is often a two-option select, and the labels vary by vendor.

    An unrecognised pair falls back to the ends of the list, since selects
    conventionally put the off state first - refusing to work would be worse.
    """
    source = "select.keep_warm"
    hass.states.async_set(source, off_option, {"options": options})
    entry = await setup_device(
        "kettle", "Test Kettle", power_switch="switch.kettle", keep_warm_mode=source
    )
    proxy = created_entities(entry, "switch")[0]
    assert hass.states.get(proxy).state == STATE_OFF

    hass.states.async_set(source, on_option, {"options": options})
    await hass.async_block_till_done()
    assert hass.states.get(proxy).state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {ATTR_ENTITY_ID: proxy}, blocking=True
    )
    await hass.async_block_till_done()

    assert [
        call.data.get("option")
        for call in service_calls
        if call.service == "select_option" and call.data.get(ATTR_ENTITY_ID) == source
    ] == [off_option]


async def test_select_backed_switch_reads_options_late_if_it_has_to(
    hass, setup_device, created_entities, service_calls
):
    """A source with no state at setup must still accept a command later.

    Dropping the command silently would leave the HomeKit toggle flipping back
    with no explanation.
    """
    source = "select.keep_warm"
    entry = await setup_device(
        "kettle", "Test Kettle", power_switch="switch.kettle", keep_warm_mode=source
    )
    proxy = created_entities(entry, "switch")[0]

    hass.states.async_set(source, "Off", {"options": ["Off", "On"]})
    await hass.async_block_till_done()
    await hass.services.async_call(
        "switch", "turn_on", {ATTR_ENTITY_ID: proxy}, blocking=True
    )
    await hass.async_block_till_done()

    assert [
        call.data.get("option")
        for call in service_calls
        if call.service == "select_option" and call.data.get(ATTR_ENTITY_ID) == source
    ] == ["On"]


async def test_select_backed_switch_ignores_an_unusable_option_list(
    hass, setup_device, created_entities, service_calls
):
    """A one-option select cannot express on and off, so send nothing."""
    source = "select.keep_warm"
    hass.states.async_set(source, "Only", {"options": ["Only"]})
    entry = await setup_device(
        "kettle", "Test Kettle", power_switch="switch.kettle", keep_warm_mode=source
    )
    proxy = created_entities(entry, "switch")[0]

    await hass.services.async_call(
        "switch", "turn_on", {ATTR_ENTITY_ID: proxy}, blocking=True
    )
    await hass.async_block_till_done()

    assert [call for call in service_calls if call.service == "select_option"] == []


@pytest.mark.parametrize(
    "source_state",
    [
        pytest.param(STATE_UNKNOWN, id="unknown"),
        pytest.param("", id="empty-string"),
        pytest.param("err", id="device-error-text"),
        pytest.param("nan", id="nan"),
    ],
)
async def test_a_unit_alone_is_enough_to_require_a_number(
    hass, setup_device, created_entities, source_state
):
    """A unit with no device class still makes HA validate the value.

    HA's check is `device class or state class or unit or precision`, so the
    countdown, humidity, water level, filter life, PM2.5 and VOC proxies are
    all validated too even though none of them carries a device class.
    """
    source = "sensor.kettle_countdown"
    hass.states.async_set(source, "5", {"unit_of_measurement": "min"})
    entry = await setup_device(
        "kettle",
        "Test Kettle",
        power_switch="switch.kettle",
        countdown_timer=source,
    )
    proxy = created_entities(entry, "sensor")[0]
    assert hass.states.get(proxy).state == "5"

    hass.states.async_set(source, source_state)
    await hass.async_block_till_done()

    assert hass.states.get(proxy).state == STATE_UNKNOWN
