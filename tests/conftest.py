"""Shared test scaffolding for the HomeKit Device Aggregator integration.

The repo root *is* the component: there is no ``custom_components/`` wrapper,
because the integration is installed by copying this directory to
``/config/custom_components/homekit_device/``. Home Assistant's loader finds
custom integrations by importing a top-level ``custom_components`` package and
walking its ``__path__``, so build that package in a temp dir and point it back
at the repo root rather than restructuring the repo and breaking every existing
install path.
"""
from __future__ import annotations

import atexit
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import ServiceCall, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_component import DATA_INSTANCES

COMPONENT_ROOT = Path(__file__).resolve().parent.parent
DOMAIN = "homekit_device"


def _build_loader_shim() -> str:
    """Create a throwaway ``custom_components`` package holding the component."""
    shim = Path(tempfile.mkdtemp(prefix="homekit_device_tests_"))
    atexit.register(shutil.rmtree, shim, ignore_errors=True)
    package = shim / "custom_components"
    package.mkdir()
    (package / "__init__.py").write_text('"""Test-only custom_components package."""\n')
    (package / DOMAIN).symlink_to(COMPONENT_ROOT, target_is_directory=True)
    return str(shim)


sys.path.insert(0, _build_loader_shim())

pytest_plugins = ["pytest_homeassistant_custom_component"]

# Import only after the shim is on sys.path.
from custom_components.homekit_device.const import (  # noqa: E402
    CONF_DEVICE_TYPE,
    CONF_NAME,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the component under test in every test."""
    return


@pytest.fixture
def setup_device(hass):
    """Set up a config entry of a given device type and return it."""

    async def _setup(device_type: str, name: str = "Test Device", **options):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=name,
            data={CONF_NAME: name, CONF_DEVICE_TYPE: device_type, **options},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup


@pytest.fixture
def service_calls(hass):
    """Record every service call made during the test.

    Listening on the bus rather than replacing the services keeps the real
    ``cover.*`` and ``switch.*`` services registered, which matters because the
    proxies live in those same domains as the services they forward to.
    """
    recorded: list[ServiceCall] = []

    @callback
    def _record(event) -> None:
        recorded.append(
            ServiceCall(
                hass,
                event.data["domain"],
                event.data["service"],
                event.data.get("service_data", {}),
            )
        )

    hass.bus.async_listen(EVENT_CALL_SERVICE, _record)
    return recorded


@pytest.fixture
def stub_service(hass):
    """Register a no-op service so a forwarded call has somewhere to land."""

    def _stub(domain: str, *services: str) -> None:
        for service in services:
            if not hass.services.has_service(domain, service):
                hass.services.async_register(domain, service, lambda call: None)

    return _stub


@pytest.fixture
def get_entity(hass):
    """Fetch a live entity object by entity id."""

    def _get(entity_id: str):
        component = hass.data[DATA_INSTANCES][entity_id.split(".")[0]]
        entity = component.get_entity(entity_id)
        assert entity is not None, f"{entity_id} was never added"
        return entity

    return _get


@pytest.fixture
def created_entities(hass):
    """List the entity ids this config entry registered, by platform domain."""

    def _ids(entry, platform_domain: str | None = None) -> list[str]:
        registry = er.async_get(hass)
        return sorted(
            registry_entry.entity_id
            for registry_entry in er.async_entries_for_config_entry(
                registry, entry.entry_id
            )
            if platform_domain is None or registry_entry.domain == platform_domain
        )

    return _ids
