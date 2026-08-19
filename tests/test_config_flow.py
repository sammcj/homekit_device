"""Tests for the config flow.

Two things matter here. A shutter has no power entity, so it must skip the base
schema that makes power_switch a required field. And one cover entity may be
chosen for both the lift and the tilt half, but only when it actually exposes
its own tilt services - otherwise both halves would drive the same motor.
"""
from __future__ import annotations

import pytest
import voluptuous as vol
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homekit_device.const import (
    CONF_DEVICE_TYPE,
    CONF_LIFT_COVER,
    CONF_NAME,
    CONF_POWER_SWITCH,
    CONF_TILT_COVER,
    DOMAIN,
)

COVER = "cover.combined_shutter"


def schema_keys(result) -> set[str]:
    """The field names the form is asking for."""
    return {str(marker.schema) for marker in result["data_schema"].schema}


def suggested_values(result) -> dict:
    """The values the redisplayed form has pre-filled for the user."""
    return {
        str(marker.schema): marker.description["suggested_value"]
        for marker in result["data_schema"].schema
        if isinstance(marker, vol.Marker)
        and marker.description
        and "suggested_value" in marker.description
    }


async def start_flow(hass, device_type: str, name: str = "Test Device"):
    """Walk the first step and stop on the device config form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: name, CONF_DEVICE_TYPE: device_type}
    )
    assert result["step_id"] == "device_config"
    return result


def set_cover(hass, features: int, entity_id: str = COVER) -> None:
    """Publish a cover source the flow can inspect."""
    hass.states.async_set(entity_id, "open", {ATTR_SUPPORTED_FEATURES: int(features)})


async def test_shutter_skips_the_base_schema(hass):
    """A shutter must not be forced to nominate a power switch it does not have."""
    result = await start_flow(hass, "shutter", "Test Shutter")

    assert schema_keys(result) == {CONF_LIFT_COVER, CONF_TILT_COVER}
    assert CONF_POWER_SWITCH not in schema_keys(result)


async def test_shutter_needs_only_a_lift_cover(hass):
    """Tilt is optional, so a lift-only shutter has to be creatable."""
    result = await start_flow(hass, "shutter", "Test Shutter")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LIFT_COVER: "cover.lift"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LIFT_COVER] == "cover.lift"
    assert CONF_POWER_SWITCH not in result["data"]


async def test_other_device_types_keep_the_base_schema(hass):
    """The skip is specific to shutters, not a hole in every schema."""
    result = await start_flow(hass, "kettle", "Test Kettle")

    assert CONF_POWER_SWITCH in schema_keys(result)


async def test_same_entity_for_lift_and_tilt_is_rejected_without_tilt_support(hass):
    """One position-only cover cannot be both halves - it is one motor."""
    set_cover(hass, CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE)
    result = await start_flow(hass, "shutter", "Test Shutter")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LIFT_COVER: COVER, CONF_TILT_COVER: COVER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TILT_COVER: "tilt_same_as_lift"}


async def test_same_entity_for_lift_and_tilt_is_allowed_with_tilt_support(hass):
    """A cover with its own tilt services genuinely is both halves."""
    set_cover(
        hass,
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.SET_TILT_POSITION,
    )
    result = await start_flow(hass, "shutter", "Test Shutter")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LIFT_COVER: COVER, CONF_TILT_COVER: COVER}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LIFT_COVER] == COVER
    assert result["data"][CONF_TILT_COVER] == COVER


async def test_rejection_preserves_the_users_selections(hass):
    """Redisplaying an empty form would make the user pick everything again."""
    set_cover(hass, CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE)
    result = await start_flow(hass, "shutter", "Test Shutter")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LIFT_COVER: COVER, CONF_TILT_COVER: COVER}
    )

    assert suggested_values(result) == {
        CONF_LIFT_COVER: COVER,
        CONF_TILT_COVER: COVER,
    }


async def test_a_missing_tilt_entity_is_treated_as_unsupported(hass):
    """No state at all means no evidence of tilt support, so reject the pair."""
    result = await start_flow(hass, "shutter", "Test Shutter")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_LIFT_COVER: "cover.absent", CONF_TILT_COVER: "cover.absent"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TILT_COVER: "tilt_same_as_lift"}


@pytest.mark.parametrize(
    "user_input",
    [
        pytest.param(
            {CONF_LIFT_COVER: "cover.lift", CONF_TILT_COVER: "cover.tilt"},
            id="different-entities",
        ),
        pytest.param({CONF_LIFT_COVER: "cover.lift"}, id="no-tilt"),
    ],
)
async def test_distinct_or_absent_tilt_is_never_rejected(hass, user_input):
    """The check only fires on the one-entity-for-both case."""
    result = await start_flow(hass, "shutter", "Test Shutter")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
