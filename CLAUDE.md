# Architecture

A Home Assistant custom integration that builds proxy entities over a user's existing entities so the HomeKit Bridge exposes them well.

The one fact that drives every design decision here: the bridge allocates one accessory per **entity** and never merges entities because they share a device. Grouping entities under one HA device does not produce one tile in the Home app. To get one accessory you must produce one richer entity whose type carries the parts as characteristics (`climate` for the kettle, `cover` for the shutter).

The repo root is the component itself, with no `custom_components/` wrapper. It is installed by copying the directory to `/config/custom_components/homekit_device/`.

# Conventions

Proxy entities subclass `HomeKitDeviceEntity` in `entity.py`, which tracks exactly one source entity. An entity merging several sources overrides `async_added_to_hass` to register the extra listeners, and seeds them before calling `super()` so the first state write is complete.

Mirror capabilities from the source entity's `supported_features` rather than asserting them. HA registers services with `required_features`, so advertising a capability the source lacks gives HomeKit a control that raises `ServiceNotSupported` on every use.

Forward commands with the generic `homeassistant.turn_on` / `turn_off` rather than a hardcoded domain, so a `switch`, `input_boolean` or `fan` source all work.

# Gotchas

A config key existing in `config_flow.py` does not mean a platform reads it. Ten options are collected from the user and used by nothing. Check the platform's `async_setup_entry` before believing the flow or the README. Only `kettle`, `shutter` and `electric_blanket` collapse their sources into an aggregated entity; the rest just group.

Setting `entity_category` is the lever for keeping an entity out of HomeKit. The bridge skips categorised entities unless they are listed individually in its included entities.

Attributes like `_attr_homekit_char` do nothing. The bridge works from `State` objects and the entity registry, so it cannot see arbitrary attributes on the entity object. An earlier version of this repo carried a whole module of them.

Verify claims about bridge behaviour against `home-assistant/core` under `homeassistant/components/homekit/`, not from memory. Several long-standing README claims turned out to be false.

# Testing

There is no test suite and no CI. Changes are verified with `ruff check .` and by reading HA source. Nothing runs against a live Home Assistant, so state any change as unverified until it has been smoke tested on a real instance.

# Releasing

After a PR merges, `manifest.json`'s `version` must match the git tag and GitHub release, which use a `v` prefix (`"version": "2.0.0"` goes with tag `v2.0.0`). HACS reads the manifest, so a stale version means users get no update prompt. The manifest has drifted behind a release before; check it as part of merging, not afterwards.
