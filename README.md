# HomeKit Device Aggregator for Home Assistant

This custom integration for Home Assistant combines several related entities into one proxy entity, so the HomeKit Bridge exposes them as one accessory with several characteristics instead of one tile per entity.

## Features

- Collapse related entities into a single richer entity - a kettle's power, current and target temperature become one thermostat; a shutter's lift and tilt become one window covering (kettle, electric blanket and shutter only)
- Group the remaining entities under one Home Assistant device
- Configure through the Home Assistant UI
- Real-time state synchronisation between Home Assistant and HomeKit

## Installation

1. Copy this directory to your Home Assistant custom_components directory:
   ```bash
   cp -r homekit_device /config/custom_components/
   ```
2. Restart Home Assistant
3. Go to Configuration -> Integrations
4. Click the "+ ADD INTEGRATION" button
5. Search for "HomeKit Device Aggregator"
6. Follow the configuration steps

## Supported Device Types

Three types currently collapse their sources into a single richer entity, which is what produces one HomeKit accessory: **Smart Kettle**, **Electric Blanket** and **Shutter**. The rest only group their entities under one Home Assistant device - each still becomes its own HomeKit tile, and several of their configuration options are collected but not yet acted on. Each section below says which.

### Smart Kettle

Combines the kettle's power, current temperature and target temperature into a single HomeKit thermostat accessory. Keep warm and the diagnostic sensors stay separate - see [Kettle Features in HomeKit](#kettle-features-in-homekit).

#### Setup Steps

1. First, create the required helpers in Home Assistant:
   - Go to Settings > Devices & Services > Helpers
   - Click "+ Create Helper"
   - Create an "Input Number" helper for target temperature:
     * Name: "Kettle Target Temperature"
     * Minimum value: 40 (a minimum of 0 is raised to 1 - the bridge treats 0 as "unset" and builds a broken range)
     * Maximum value: 100
     * Step size: 1
     * Unit of measurement: °C
     * Icon: mdi:thermometer
   - Create a "Toggle" helper for keep warm mode:
     * Name: "Kettle Keep Warm"
     * Icon: mdi:kettle-steam

2. Add the HomeKit Device Aggregator:
   - Go to Settings > Devices & Services
   - Click "+ Add Integration"
   - Search for "HomeKit Device Aggregator"
   - Select "kettle" as the device type
   - Configure the following:
     * Name: "Smart Kettle"
     * Power Switch: Your kettle's power switch
     * Current Temperature: Your kettle's temperature sensor
     * Target Temperature: input_number.kettle_target_temperature
     * Keep Warm: input_boolean.kettle_keep_warm (a switch entity also works)

3. Configure the HomeKit Bridge:
   - Go to Settings > Devices & Services
   - Find "HomeKit Bridge" and click "Configure"
   - Add a new bridge configuration
   - Include these domains:
     * climate (the aggregated kettle thermostat)
     * switch (for the keep warm toggle)
   - The kettle appears in HomeKit as one thermostat (power, current temperature, target temperature) plus a separate keep warm switch

- Required:
  - Power Switch (`switch.kettle`)
- Optional:
  - Current Temperature (`sensor.kettle_temperature`)
  - Target Temperature (`input_number` helper)
  - Keep Warm Mode (`input_boolean` or `switch`)
  - Countdown Timer, Fault Status, Status Sensor

### Multi-Sensor Thermostat

Grouping only. No climate entity is created for this type - the current temperature, target temperature and additional sensor options are collected but not yet wired up. What you get is a power switch proxy and a status sensor grouped under one device.

- Required by the form:
  - Power Switch, Current Temperature Sensor, Target Temperature Control
- Optional:
  - Status Sensor, Additional Temperature Sensors
- Collected but not yet used: Current Temperature Sensor, Target Temperature Control, Additional Temperature Sensors

### Multi-Control Fan

Groups fan controls under one device. A single HomeKit fan accessory with a speed slider only appears when the power entity is itself a `fan.*` entity; oscillation and direction become their own entities, and so their own tiles.

- Required:
  - Power Entity (switch or fan)
- Optional:
  - Oscillation Control, Direction Control, Status Sensor
- Collected but not yet used: Speed Control

### Multi-Control Light

Grouping only. No light entity is created for this type - use Home Assistant's own light grouping or a template light instead.

- Required:
  - Power Switch
- Optional:
  - Status Sensor
- Collected but not yet used: Brightness Control, Colour Temperature Control, RGB Colour Control

### Smart Humidifier

Grouping only. No humidifier entity is created for this type; the humidity and water level readings become sensor entities grouped under one device.

- Required by the form:
  - Power Switch, Current Humidity Sensor, Target Humidity Control
- Optional:
  - Water Level Sensor, Status Sensor
- Collected but not yet used: Target Humidity Control

### Air Purifier

Groups an air purifier's controls and air quality readings under one device. Each becomes its own entity, so each becomes its own HomeKit tile.

- Required:
  - Power Entity (switch or fan)
- Optional:
  - Air Quality Sensor
  - Filter Life Sensor
  - PM2.5 Sensor
  - VOC Sensor
  - Child Lock Switch
  - Display On/Off Switch
  - Status Sensor

### Garage Door

Grouping only. No garage door accessory is created - expose your original `cover` entity to the bridge for that. The obstruction, motion and light options become their own grouped entities.

- Required by the form:
  - Power Switch, Door Position Control
- Optional:
  - Obstruction Sensor, Motion Sensor, Light Control, Status Sensor
- Collected but not yet used: Door Position Control

### Security System

Grouping only. No alarm panel accessory is created - expose your original `alarm_control_panel` entity to the bridge for that.

- Required by the form:
  - Power Switch, Alarm State Control
- Optional:
  - Security Sensors (multiple), Siren Control, Status Sensor
- Collected but not yet used: Alarm State Control

### Star Projector

Groups a master switch, rotation fan and laser/background lights under one device. Each stays its own entity, so HomeKit shows one tile per control rather than a single projector accessory. Useful for child night lights such as Tuya/local-tuya based projectors that expose multiple entities (e.g. `switch.star_projector_master`, `fan.star_projector_rotation`, `light.star_projector_laser`, `light.star_projector_background`).

- Required:
  - Power Switch (master switch)
- Optional:
  - Laser Light (light entity)
  - Background/Nebula Light (light entity)
  - Rotation Fan (fan entity)
  - Status Sensor

### Electric Blanket

Combines a power switch and per-zone heat-level selects into a single multi-zone electric blanket. Each zone is exposed to HomeKit as a Heater (Off/Heat) with a 0-6 level slider, via a `climate` proxy.

- Required:
  - Power Entity (switch or fan)
  - Body Zone Heat Level (a `select` with options like `['Off','1'..'6']`)
- Optional:
  - Feet Zone Heat Level (`select`)
  - Status Sensor
- Collected but not yet used: Body Zone Timer, Feet Zone Timer

When exposing through the HomeKit Bridge, include the `climate` and `switch` domains. The zone selects operate on their friendly option strings (`Off`, `1`..`6`); for localtuya blankets these map to the underlying `level_1..level_7` raw values automatically (`level_1` == Off).

### Shutter (lift + tilt)

Combines two separate cover entities - one that raises/lowers the shutter and one that angles the slats - into a single HomeKit window covering with both a position slider and a tilt slider.

- Required:
  - Lift Cover (up/down `cover` entity)
- Optional:
  - Tilt Cover (`cover` entity controlling slat angle)

If the tilt entity supports setting a tilt position (`SET_TILT_POSITION`), it is driven through its tilt services. Otherwise - the common case where a shutter's tilt is exposed as a second position-only cover - its lift position drives the tilt slider instead.

Only the controls the source entities actually support are exposed. A shutter with open/close but no position support is bridged as `WindowCoveringBasic`, so HomeKit still shows a slider but it snaps to fully open or fully closed. The same entity can be used for both halves only if it supports tilt itself.

When exposing through the HomeKit Bridge, include the `cover` domain and exclude the two original cover entities so only the aggregated shutter appears.

## HomeKit Integration

This integration works alongside the Home Assistant HomeKit Bridge.

### How it Works

The HomeKit Bridge allocates one accessory per **entity**, not per Home Assistant device, and never merges two accessories because their entities share a device. Grouping entities under one device tidies the Home Assistant UI but does not, on its own, produce one tile in the Home app.

So the aggregation has to happen at the entity level, and that is what this integration does:

1. Related source entities are collapsed into a single proxy entity of a type that carries all of them as characteristics - `climate` for the kettle, `cover` for the shutter
2. That one entity becomes one HomeKit accessory with power, current temperature, setpoint and so on all on the same card
3. Controls that have no home on that accessory (a keep-warm switch, a projector's separate lights) stay as their own entities, and so get their own tiles - this is a HomeKit limitation, not something the integration can hide
4. Readouts already carried by the primary accessory (temperature, status, countdown, fault) are marked as diagnostic entities. The bridge skips entities that carry a category, so they stay grouped in Home Assistant and out of the Home app - unless you list them individually in the bridge's included entities, which overrides the skip

There is a narrow exception where the device grouping does help. The bridge auto-links a few sibling entities from the same device onto an accessory as extra characteristics, gated on the accessory entity's own domain:

- battery level and battery charging - any domain
- motion - camera accessories only
- doorbell - camera and lock accessories only
- humidity, PM2.5 and temperature - fan accessories only

So for the accessories this integration produces, only the battery pair applies, plus the fan-gated three when the power entity is a `fan.*`. Every other `linked_*` option (obstruction, filter life, valve timing) is manual YAML only and is never auto-populated.

### Kettle Features in HomeKit

The kettle is exposed as a single thermostat accessory carrying:
- Power on/off (Off/Heat)
- Current water temperature
- Target temperature slider, ranged from the target temperature helper's own min/max

Keep warm remains a separate switch entity and appears as its own tile.

The kettle no longer creates a separate power switch entity - power is the thermostat's Off/Heat mode. The temperature, countdown, fault and status readouts are still created and grouped under the device, but marked as diagnostic so the bridge skips them. The target temperature number is kept for use in Home Assistant; the bridge does not support the `number` domain, so it never reaches HomeKit either.

**Breaking change:** if you configured a kettle before this, the `switch.<name>_power` proxy is gone. Point any automations at the new `climate.<name>` entity (or at your original power switch), and delete the now-unavailable old entity from the entity registry.

## Troubleshooting

1. If a device doesn't appear in HomeKit:
   - Ensure all required entities are correctly configured
   - Check that the HomeKit Bridge is running
   - Restart Home Assistant
    - Verify that all required domains are included in the HomeKit Bridge configuration
    - Check that helpers (input_number, input_boolean) are properly set up
    - Make sure the device appears correctly in Home Assistant before exposing to HomeKit
    - Try removing and re-adding the device in the Home app

2. If states aren't updating:
   - Verify that all entities are working in Home Assistant
   - Check the Home Assistant logs for any errors

## Contributing

Feel free to submit issues and pull requests for:

- New device type support
- Bug fixes
- Feature enhancements

## License

MIT License - See LICENSE file for details
