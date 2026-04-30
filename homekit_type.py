"""HomeKit device type definitions."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import UnitOfTemperature

# HomeKit Categories (from HAP-python)
CATEGORY_KETTLE = 27
CATEGORY_FAN = 3
CATEGORY_LIGHTBULB = 5

# HomeKit Characteristic UUIDs (from HAP-python)
CHAR_ON = "00000025-0000-1000-8000-0026BB765291"
CHAR_CURRENT_TEMPERATURE = "00000011-0000-1000-8000-0026BB765291"
CHAR_TARGET_TEMPERATURE = "00000035-0000-1000-8000-0026BB765291"
CHAR_HEATING_COOLING_CURRENT = "0000000F-0000-1000-8000-0026BB765291"
CHAR_HEATING_COOLING_TARGET = "00000033-0000-1000-8000-0026BB765291"

# HomeKit Service UUIDs (from HAP-python)
SERVICE_THERMOSTAT = "0000004A-0000-1000-8000-0026BB765291"
SERVICE_SWITCH = "00000049-0000-1000-8000-0026BB765291"

KETTLE_DEVICE_TYPE = {
    "category": CATEGORY_KETTLE,
    "services": [
        {
            "name": "Kettle",
            "service": SERVICE_THERMOSTAT,
            "primary": True,
            "chars": [
                {
                    "name": "Current Temperature",
                    "char": CHAR_CURRENT_TEMPERATURE,
                    "unit": UnitOfTemperature.CELSIUS,
                    "device_class": "temperature",
                    "min_value": 0,
                    "max_value": 100,
                },
                {
                    "name": "Target Temperature",
                    "char": CHAR_TARGET_TEMPERATURE,
                    "unit": UnitOfTemperature.CELSIUS,
                    "min_value": 0,
                    "max_value": 100,
                    "step_value": 1,
                },
                {
                    "name": "Current Operation",
                    "char": CHAR_HEATING_COOLING_CURRENT,
                    "valid_values": [0, 1],  # 0: Off, 1: Heat
                },
                {
                    "name": "Target Operation",
                    "char": CHAR_HEATING_COOLING_TARGET,
                    "valid_values": [0, 1],  # 0: Off, 1: Heat
                },
            ],
        },
        {
            "name": "Power",
            "service": SERVICE_SWITCH,
            "linked": True,
            "chars": [
                {
                    "name": "Power State",
                    "char": CHAR_ON,
                    "device_class": BinarySensorDeviceClass.POWER,
                },
            ],
        },
    ],
}

# HomeKit Service UUIDs for additional services used by other device types
SERVICE_LIGHTBULB = "00000043-0000-1000-8000-0026BB765291"
SERVICE_FANV2 = "000000B7-0000-1000-8000-0026BB765291"

# HomeKit Characteristic UUIDs for additional characteristics
CHAR_BRIGHTNESS = "00000008-0000-1000-8000-0026BB765291"
CHAR_HUE = "00000013-0000-1000-8000-0026BB765291"
CHAR_SATURATION = "0000002F-0000-1000-8000-0026BB765291"
CHAR_ROTATION_SPEED = "00000029-0000-1000-8000-0026BB765291"
CHAR_ACTIVE = "000000B0-0000-1000-8000-0026BB765291"

STAR_PROJECTOR_DEVICE_TYPE = {
    "category": CATEGORY_FAN,
    "services": [
        {
            "name": "Master",
            "service": SERVICE_SWITCH,
            "primary": True,
            "chars": [
                {
                    "name": "Power State",
                    "char": CHAR_ON,
                    "device_class": BinarySensorDeviceClass.POWER,
                },
            ],
        },
        {
            "name": "Rotation",
            "service": SERVICE_FANV2,
            "linked": True,
            "chars": [
                {
                    "name": "Active",
                    "char": CHAR_ACTIVE,
                },
                {
                    "name": "Rotation Speed",
                    "char": CHAR_ROTATION_SPEED,
                    "min_value": 0,
                    "max_value": 100,
                    "step_value": 1,
                },
            ],
        },
        {
            "name": "Laser",
            "service": SERVICE_LIGHTBULB,
            "linked": True,
            "chars": [
                {
                    "name": "On",
                    "char": CHAR_ON,
                },
                {
                    "name": "Brightness",
                    "char": CHAR_BRIGHTNESS,
                    "min_value": 0,
                    "max_value": 100,
                    "step_value": 1,
                },
            ],
        },
        {
            "name": "Background",
            "service": SERVICE_LIGHTBULB,
            "linked": True,
            "chars": [
                {
                    "name": "On",
                    "char": CHAR_ON,
                },
                {
                    "name": "Brightness",
                    "char": CHAR_BRIGHTNESS,
                    "min_value": 0,
                    "max_value": 100,
                    "step_value": 1,
                },
                {
                    "name": "Hue",
                    "char": CHAR_HUE,
                    "min_value": 0,
                    "max_value": 360,
                    "step_value": 1,
                },
                {
                    "name": "Saturation",
                    "char": CHAR_SATURATION,
                    "min_value": 0,
                    "max_value": 100,
                    "step_value": 1,
                },
            ],
        },
    ],
}

DEVICE_TYPES = {
    "kettle": KETTLE_DEVICE_TYPE,
    "star_projector": STAR_PROJECTOR_DEVICE_TYPE,
}

def get_device_type(device_type: str) -> dict:
    """Get the HomeKit device type configuration."""
    return DEVICE_TYPES.get(device_type, {})
