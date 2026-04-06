"""
PowerWalker CGI — Sensor platform.

All sensors are CoordinatorEntity instances — they read from coordinator.data
and never make their own HTTP requests.

Index mapping verified against actual raw VFI 2000 CGI response (newline-separated):
  [0]  "Line Mode"  → Status
  [1]  "249"        → Internal Temperature  (÷10 → °C)
  [7]  "547"        → Battery Voltage        (÷10 → V)
  [8]  "100"        → Battery Capacity       (%)
  [9]  "87"         → Remaining Backup Time  (min)
  [10] "500"        → Input Frequency        (÷10 → Hz)
  [11] "2327"       → Input Voltage          (÷10 → V)
  [13] "499"        → Output Frequency       (÷10 → Hz)
  [14] "2296"       → Output Voltage         (÷10 → V)
  [16] "18"         → Load Level             (%)
  [34] "16"         → Output Current         (÷10 → A)

Output Active Power is calculated as Voltage × Current (firmware value unreliable).
"""

import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfFrequency,
    UnitOfPower,
    PERCENTAGE,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

_NOT_PRESENT = "999999999"

# (friendly name, token index, unit, scale, icon, device_class, state_class)
SENSOR_DEFINITIONS = [
    (
        "Status Mode", 0, None, 1,
        "mdi:information-outline", None, None,
    ),
    (
        "Internal Temperature", 1, UnitOfTemperature.CELSIUS, 0.1,
        "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT,
    ),
    (
        "Battery Voltage", 7, UnitOfElectricPotential.VOLT, 0.1,
        "mdi:battery", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT,
    ),
    (
        "Battery Capacity", 8, PERCENTAGE, 1,
        "mdi:battery-heart-variant", SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT,
    ),
    (
        "Remaining Backup Time", 9, "min", 1,
        "mdi:timer-outline", None, SensorStateClass.MEASUREMENT,
    ),
    (
        "Input Frequency", 10, UnitOfFrequency.HERTZ, 0.1,
        "mdi:sine-wave", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT,
    ),
    (
        "Input Voltage", 11, UnitOfElectricPotential.VOLT, 0.1,
        "mdi:transmission-tower-import", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT,
    ),
    (
        "Output Frequency", 13, UnitOfFrequency.HERTZ, 0.1,
        "mdi:sine-wave", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT,
    ),
    (
        "Output Voltage", 14, UnitOfElectricPotential.VOLT, 0.1,
        "mdi:transmission-tower-export", SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT,
    ),
    (
        "Load Level", 16, PERCENTAGE, 1,
        "mdi:gauge", None, SensorStateClass.MEASUREMENT,
    ),
    (
        "Output Current", 34, UnitOfElectricCurrent.AMPERE, 0.1,
        "mdi:current-ac", SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT,
    ),
]

_IDX_OUTPUT_VOLTAGE = 14
_IDX_OUTPUT_CURRENT = 34
_SCALE_V = 0.1
_SCALE_I = 0.1


async def async_setup_entry(hass, config_entry, async_add_entities):
    entry_data  = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    host        = entry_data["host"]

    sensors = [
        PWSensor(coordinator, host, name, index, unit, scale, icon, dev_class, state_class)
        for name, index, unit, scale, icon, dev_class, state_class in SENSOR_DEFINITIONS
    ]
    sensors.append(PWCalculatedPowerSensor(coordinator, host))
    async_add_entities(sensors)


def _safe_token(tokens: list[str], index: int) -> str | None:
    if index >= len(tokens):
        return None
    raw = tokens[index].strip()
    if not raw or raw == _NOT_PRESENT or "---" in raw:
        return None
    return raw


class PWSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, host, name, index, unit, scale, icon, dev_class, state_class):
        super().__init__(coordinator)
        self._index = index
        self._scale = scale
        self._attr_name                       = f"UPS {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon                       = icon
        self._attr_device_class               = dev_class
        self._attr_state_class                = state_class
        self._attr_unique_id                  = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info                = DeviceInfo(
            identifiers={("powerwalker_cgi", host)},
            name="PowerWalker UPS",
            manufacturer="BlueWalker",
            model="VFI Series",
        )

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
        raw = _safe_token(data.get("sensors", []), self._index)
        if raw is None:
            return None
        if self._attr_native_unit_of_measurement is None:
            return raw
        try:
            return round(float(raw) * self._scale, 1)
        except ValueError:
            _LOGGER.warning("%s: cannot parse token[%d]=%r", self._attr_name, self._index, raw)
            return None


class PWCalculatedPowerSensor(CoordinatorEntity, SensorEntity):
    """Output Active Power = Output Voltage × Output Current."""

    def __init__(self, coordinator, host):
        super().__init__(coordinator)
        self._attr_name                       = "UPS Output Active Power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_icon                       = "mdi:lightning-bolt"
        self._attr_device_class               = SensorDeviceClass.POWER
        self._attr_state_class                = SensorStateClass.MEASUREMENT
        self._attr_unique_id                  = f"pw_{host}_output_active_power"
        self._attr_device_info                = DeviceInfo(
            identifiers={("powerwalker_cgi", host)},
            name="PowerWalker UPS",
            manufacturer="BlueWalker",
            model="VFI Series",
        )

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data:
            return None
        tokens = data.get("sensors", [])
        raw_v = _safe_token(tokens, _IDX_OUTPUT_VOLTAGE)
        raw_i = _safe_token(tokens, _IDX_OUTPUT_CURRENT)
        if raw_v is None or raw_i is None:
            return None
        try:
            return round(float(raw_v) * _SCALE_V * float(raw_i) * _SCALE_I)
        except ValueError:
            return None