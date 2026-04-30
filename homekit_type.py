"""HomeKit device type definitions."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import UnitOfTemperature

# HomeKit Categories (from HAP-python)
CATEGORY_KETTLE = 27

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

DEVICE_TYPES = {
    "kettle": KETTLE_DEVICE_TYPE,
}

def get_device_type(device_type: str) -> dict:
    """Get the HomeKit device type configuration."""
    return DEVICE_TYPES.get(device_type, {})
