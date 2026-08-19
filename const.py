"""Constants for the HomeKit Device Aggregator integration."""
DOMAIN = "homekit_device"
CONF_ENTITIES = "entities"
CONF_NAME = "name"
CONF_DEVICE_TYPE = "device_type"

# Supported HomeKit device types
DEVICE_TYPES = {
    "kettle": "A kettle exposed as a single thermostat (power, current and target temperature)",
    "thermostat": "Groups temperature sensors and controls under one device",
    "fan": "Groups fan controls (power, oscillation, direction) under one device",
    "light": "Groups light controls under one device",
    "humidifier": "Groups humidity sensing and control under one device",
    "air_purifier": "Groups air purifier controls and air quality sensors under one device",
    "garage_door": "Groups garage door sensors and light under one device",
    "security_system": "Groups security sensors and siren under one device",
    "star_projector": "Groups a star projector's switch, rotation fan and lights under one device",
    "electric_blanket": "A multi-zone electric blanket with power and per-zone heat levels",
    "shutter": "A shutter combining separate lift and tilt cover entities"
}

# Configuration keys for all device types
CONF_POWER_SWITCH = "power_switch"
CONF_STATUS_SENSOR = "status_sensor"

# Kettle specific configs
CONF_CURRENT_TEMP = "current_temperature"
CONF_TARGET_TEMP = "target_temperature"
CONF_COUNTDOWN = "countdown_timer"
CONF_FAULT = "fault_status"
CONF_KEEP_WARM = "keep_warm_mode"
CONF_KEEP_WARM_TIME = "keep_warm_idle_time"

# Temperature related configs
CONF_TEMP_SENSORS = "temperature_sensors"  # For multiple temp sensors

# Fan related configs
CONF_SPEED_CONTROL = "speed_control"
CONF_OSCILLATION = "oscillation"
CONF_DIRECTION = "direction"

# Light related configs
CONF_BRIGHTNESS = "brightness"
CONF_COLOR_TEMP = "color_temperature"
CONF_RGB_CONTROL = "rgb_control"
CONF_EFFECT_LIST = "effect_list"

# Humidifier related configs
CONF_CURRENT_HUMIDITY = "current_humidity"
CONF_TARGET_HUMIDITY = "target_humidity"
CONF_WATER_LEVEL = "water_level"

# Air purifier related configs
CONF_AIR_QUALITY = "air_quality"
CONF_FILTER_LIFE = "filter_life"
CONF_PM25 = "pm25"
CONF_VOC = "voc"
CONF_CHILD_LOCK = "child_lock"
CONF_DISPLAY_SWITCH = "display_switch"

# Garage door related configs
CONF_DOOR_POSITION = "door_position"
CONF_OBSTRUCTION = "obstruction_detected"
CONF_MOTION = "motion_sensor"
CONF_LIGHT_SWITCH = "light_switch"

# Security system related configs
CONF_ALARM_STATE = "alarm_state"
CONF_SENSORS = "sensors"  # List of security sensors
CONF_SIREN = "siren"
CONF_KEYPAD = "keypad"

# Star projector related configs
CONF_LASER_LIGHT = "laser_light"
CONF_BACKGROUND_LIGHT = "background_light"
CONF_ROTATION_FAN = "rotation_fan"

# Electric blanket related configs
CONF_ZONE_BODY = "zone_body"
CONF_ZONE_FEET = "zone_feet"
CONF_BODY_TIMER = "body_timer"
CONF_FEET_TIMER = "feet_timer"

# Shutter related configs
CONF_LIFT_COVER = "lift_cover"
CONF_TILT_COVER = "tilt_cover"

# Default values
DEFAULT_NAME = "Aggregated Device"
