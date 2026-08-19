"""Tests for which platforms build which entities.

The bridge builds one accessory per entity, so an extra proxy is not a harmless
duplicate - it is a second tile in the Home app for something the aggregated
entity already carries. The kettle's power switch has to be suppressed in both
switch.py and fan.py, because a kettle's power entity can live in either
domain and the fan-domain guard was missed the first time round.
"""
from __future__ import annotations

import pytest
from homeassistant.components.climate import HVACMode

KEEP_WARM = "switch.kettle_keep_warm"


async def test_kettle_produces_a_thermostat_and_a_keep_warm_switch(
    hass, setup_device, created_entities
):
    """One climate tile carrying power and temperature, plus keep warm."""
    entry = await setup_device(
        "kettle",
        "Test Kettle",
        power_switch="switch.kettle_power",
        current_temperature="sensor.kettle_temp",
        target_temperature="input_number.kettle_target",
        keep_warm_mode=KEEP_WARM,
    )

    assert len(created_entities(entry, "climate")) == 1
    assert len(created_entities(entry, "switch")) == 1


@pytest.mark.parametrize(
    ("power", "platform"),
    [
        pytest.param("switch.kettle_power", "switch", id="switch-domain-power"),
        pytest.param("fan.kettle_power", "fan", id="fan-domain-power"),
    ],
)
async def test_kettle_never_gets_a_standalone_power_proxy(
    hass, setup_device, created_entities, power, platform
):
    """Power belongs to the thermostat's Off/Heat mode, not to its own tile."""
    entry = await setup_device("kettle", "Test Kettle", power_switch=power)

    assert created_entities(entry, platform) == []
    assert len(created_entities(entry, "climate")) == 1


@pytest.mark.parametrize(
    ("power", "platform"),
    [
        pytest.param("switch.purifier_power", "switch", id="switch-domain-power"),
        pytest.param("fan.purifier_power", "fan", id="fan-domain-power"),
    ],
)
async def test_other_device_types_still_get_their_power_proxy(
    hass, setup_device, created_entities, power, platform
):
    """The suppression is specific to the aggregating types, not global."""
    entry = await setup_device("air_purifier", "Test Purifier", power_switch=power)

    assert len(created_entities(entry, platform)) == 1


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("switch.keep_warm", id="switch-source"),
        pytest.param("input_boolean.keep_warm", id="input-boolean-source"),
    ],
)
async def test_keep_warm_works_from_either_source_domain(
    hass, setup_device, created_entities, source
):
    """Keep warm is an input_boolean as often as it is a switch."""
    entry = await setup_device(
        "kettle",
        "Test Kettle",
        power_switch="switch.kettle_power",
        keep_warm_mode=source,
    )

    assert len(created_entities(entry, "switch")) == 1


async def test_kettle_without_a_power_entity_builds_no_thermostat(
    hass, setup_device, created_entities
):
    """Power is the kettle's own source entity, so there is nothing to proxy."""
    entry = await setup_device("kettle", "Test Kettle")

    assert created_entities(entry, "climate") == []


async def test_electric_blanket_is_unaffected_by_the_kettle_branch(
    hass, setup_device, created_entities
):
    """Both device types share async_setup_entry, so pin the blanket's shape.

    One climate per zone, and no standalone power switch - the zones drive the
    master power between them.
    """
    entry = await setup_device(
        "electric_blanket",
        "Test Blanket",
        power_switch="switch.blanket_power",
        zone_body="select.blanket_body",
        zone_feet="select.blanket_feet",
    )

    assert len(created_entities(entry, "climate")) == 2
    assert created_entities(entry, "switch") == []


async def test_electric_blanket_sizes_its_slider_from_the_zone_options(
    hass, setup_device, created_entities
):
    """A blanket with four levels must not advertise six."""
    hass.states.async_set(
        "select.blanket_body", "Off", {"options": ["Off", "1", "2", "3", "4"]}
    )
    entry = await setup_device(
        "electric_blanket",
        "Test Blanket",
        power_switch="switch.blanket_power",
        zone_body="select.blanket_body",
    )
    zone = created_entities(entry, "climate")[0]
    await hass.async_block_till_done()

    state = hass.states.get(zone)
    assert state.attributes["max_temp"] == 4
    assert state.state == HVACMode.OFF


async def test_shutter_produces_only_a_cover(hass, setup_device, created_entities):
    """A shutter has no power entity, so no other platform may claim one."""
    entry = await setup_device(
        "shutter",
        "Test Shutter",
        lift_cover="cover.lift",
        tilt_cover="cover.tilt",
    )

    assert len(created_entities(entry, "cover")) == 1
    assert created_entities(entry, "switch") == []
    assert created_entities(entry, "fan") == []
