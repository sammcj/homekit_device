# HomeKit Device Aggregator for Home Assistant

This custom integration for Home Assistant allows you to combine multiple entities into a single HomeKit device. This solves the common issue where multiple related entities appear as separate devices in HomeKit.

## Features

- Combine multiple Home Assistant entities into a single HomeKit device
- Configure through the Home Assistant UI
- Real-time state synchronisation between Home Assistant and HomeKit
- Supports multiple device types with specific HomeKit characteristics

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

### Smart Kettle

Combines all kettle controls and sensors into a single HomeKit kettle device.

#### Setup Steps

1. First, create the required helpers in Home Assistant:
   - Go to Settings > Devices & Services > Helpers
   - Click "+ Create Helper"
   - Create an "Input Number" helper for target temperature:
     * Name: "Kettle Target Temperature"
     * Minimum value: 0
     * Maximum value: 100
     * Step size: 1
     * Unit of measurement: °C
     * Icon: mdi:thermometer
   - Create a "Switch" helper for keep warm mode:
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
     * Keep Warm: input_boolean.kettle_keep_warm

3. Configure the HomeKit Bridge:
   - Go to Settings > Devices & Services
   - Find "HomeKit Bridge" and click "Configure"
   - Add a new bridge configuration
   - Include these domains:
     * switch
     * sensor
     * input_number
     * input_boolean
   - The kettle will appear in HomeKit as a single device with:
     * Power toggle
     * Temperature display
     * Temperature control slider
     * Keep warm mode toggle

- Required:
  - Power Switch (switch.kettle)
  - Current Temperature (sensor.kettle_temperature)
  - Target Temperature (input_number helper)
  - Keep Warm Mode (input_boolean helper)
### Multi-Sensor Thermostat

Creates a thermostat with multiple temperature sensors and controls.

- Required:
  - Power Switch
  - Current Temperature Sensor
  - Target Temperature Control
- Optional:
  - Additional Temperature Sensors
  - Status Sensor

### Multi-Control Fan

Combines fan controls into a single device.

- Required:
  - Power Switch
- Optional:
  - Speed Control
  - Oscillation Control
  - Direction Control
  - Status Sensor

### Multi-Control Light

Aggregates light controls into a single light device.

- Required:
  - Power Switch
- Optional:
  - Brightness Control
  - Colour Temperature Control
  - RGB Colour Control
  - Status Sensor

### Smart Humidifier

Combines humidity sensing and control into a smart humidifier.

- Required:
  - Power Switch
  - Current Humidity Sensor
  - Target Humidity Control
- Optional:
  - Water Level Sensor
  - Status Sensor

### Air Purifier

Creates an air purifier with air quality monitoring.

- Required:
  - Power Switch
  - Air Quality Sensor
- Optional:
  - Filter Life Sensor
  - PM2.5 Sensor
  - VOC Sensor
  - Child Lock Switch
  - Display On/Off Switch
  - Status Sensor

### Garage Door

Combines door controls and sensors into a garage door opener.

- Required:
  - Power Switch
  - Door Position Control
- Optional:
  - Obstruction Sensor
  - Motion Sensor
  - Light Control
  - Status Sensor

### Security System

Creates a security system from multiple sensors and controls.

- Required:
  - Alarm State Control
- Optional:
  - Security Sensors (multiple)
  - Siren Control
  - Status Sensor

### Star Projector

Combines a master switch, rotation fan, and laser/background lights into a single star projector device. Useful for child night lights such as Tuya/local-tuya based projectors that expose multiple entities (e.g. `switch.star_projector_master`, `fan.star_projector_rotation`, `light.star_projector_laser`, `light.star_projector_background`).

- Required:
  - Power Switch (master switch)
- Optional:
  - Laser Light (light entity)
  - Background/Nebula Light (light entity)
  - Rotation Fan (fan entity)
  - Status Sensor

## HomeKit Integration

This integration works alongside the Home Assistant HomeKit Bridge. After configuring your aggregated device, it will appear in the Home app as a single device with all its capabilities, rather than multiple separate accessories.

### How it Works

1. The integration creates a single device in Home Assistant that groups all related entities
2. When exposed through the HomeKit Bridge, it appears as a single accessory in HomeKit
3. The integration maps Home Assistant entities to appropriate HomeKit characteristics:
   - Switches become binary controls
   - Sensors become read-only characteristics
   - Input numbers become sliders
   - Input booleans become toggles

### Kettle Features in HomeKit

When you open the Home app, your kettle will appear as a single device with:
- Power on/off
- Current temperature display (in °C)
- Temperature control slider (0-100°C)
- Keep warm mode toggle (On/Off)
- All controls are accessible from the same device card

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
