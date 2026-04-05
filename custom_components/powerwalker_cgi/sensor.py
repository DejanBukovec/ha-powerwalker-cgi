"""
PowerWalker CGI — Sensor platform.

All sensors are CoordinatorEntity instances — they read from coordinator.data
and never make their own HTTP requests.

Index mapping verified against the actual raw response of PowerWalker VFI 2000
(newline-separated, one value per line):

  [0]  "Line Mode"  → Status (text)
  [1]  "249"        → Internal Temperature  (÷10 → °C)
  [2]   auto-reboot flag
  [3]   converter mode flag
  [4]   eco mode flag
  [5]   bypass-off flag
  [6]   bypass-not-allowed flag
  [7]  "547"        → Battery Voltage        (÷10 → V)
  [8]  "100"        → Battery Capacity       (%)
  [9]  "87"         → Remaining Backup Time  (min)
  [10] "500"        → Input Frequency        (÷10 → Hz)
  [11] "2327"       → Input Voltage          (÷10 → V)
  [12]  input voltage L1-L2
  [13] "499"        → Output Frequency       (÷10 → Hz)
  [14] "2296"       → Output Voltage         (÷10 → V)
  [15]  output voltage L1-L2
  [16] "18"         → Load Level             (%)
  [17]  bypass frequency
  [18]  bypass voltage
  [19–33] multi-phase / bypass fields (not present on single-phase)
  [34] "16"         → Output Current         (÷10 → A)
  [35–48] zeros / firmware artifacts

Notes:
  - "Fault Type" and "Warning" fields from the generic JS (r_v[7], r_v[8])
    do not exist as separate lines in the VFI 2000 condensed CGI response.
    The UPS leaves them blank when healthy — confirmed by the HTML page showing
    empty spans. These sensors have been removed to avoid permanent unavailability.

  - "Output Active Power" is not reliably provided by this firmware (index 48
    is a firmware artifact, not real watts). It is instead calculated as
    Output Voltage × Output Current, which matches real-world measurements.
"""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

_NOT_PRESENT = "999999999"

# (friendly name, token index, unit, scale factor)
# Index None = calculated field, handled separately
SENSOR_DEFINITIONS = [
    ("Status Mode",           0,  None,  1   ),
    ("Internal Temperature",  1,  "°C",  0.1 ),
    ("Battery Voltage",       7,  "V",   0.1 ),
    ("Battery Capacity",      8,  "%",   1   ),
    ("Remaining Backup Time", 9,  "min", 1   ),
    ("Input Frequency",       10, "Hz",  0.1 ),
    ("Input Voltage",         11, "V",   0.1 ),
    ("Output Frequency",      13, "Hz",  0.1 ),
    ("Output Voltage",        14, "V",   0.1 ),
    ("Load Level",            16, "%",   1   ),
    ("Output Current",        34, "A",   0.1 ),
]

# Indices used for the calculated power sensor
_IDX_OUTPUT_VOLTAGE  = 14
_IDX_OUTPUT_CURRENT  = 34
_SCALE_VOLTAGE       = 0.1
_SCALE_CURRENT       = 0.1


async def async_setup_entry(hass, config_entry, async_add_entities):
    entry_data  = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    host        = entry_data["host"]

    sensors = [
        PWSensor(coordinator, host, name, index, unit, scale)
        for name, index, unit, scale in SENSOR_DEFINITIONS
    ]
    # Add the calculated power sensor
    sensors.append(PWCalculatedPowerSensor(coordinator, host))

    async_add_entities(sensors)


def _safe_token(tokens: list[str], index: int) -> str | None:
    """Return a token by index, or None if out of range / sentinel / empty."""
    if index >= len(tokens):
        return None
    raw = tokens[index].strip()
    if not raw or raw == _NOT_PRESENT or "---" in raw:
        return None
    return raw


class PWSensor(CoordinatorEntity, SensorEntity):
    """A sensor entity backed by the shared coordinator — no individual HTTP calls."""

    def __init__(self, coordinator, host, name, index, unit, scale):
        super().__init__(coordinator)
        self._index = index
        self._scale = scale
        self._attr_name                       = f"UPS {name}"
        self._attr_native_unit_of_measurement = unit
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

        # Text / status fields — return as-is
        if self._attr_native_unit_of_measurement is None:
            return raw

        try:
            return round(float(raw) * self._scale, 1)
        except ValueError:
            _LOGGER.warning(
                "%s: cannot parse token[%d]=%r as float",
                self._attr_name, self._index, raw,
            )
            return None


class PWCalculatedPowerSensor(CoordinatorEntity, SensorEntity):
    """
    Output Active Power calculated as Voltage × Current.
    The firmware does not provide a reliable active power value for this model.
    Result is rounded to the nearest watt.
    """

    def __init__(self, coordinator, host):
        super().__init__(coordinator)
        self._attr_name                       = "UPS Output Active Power"
        self._attr_native_unit_of_measurement = "W"
        self._attr_unique_id                  = f"pw_{host}_output_active_power"
        self._attr_icon                       = "mdi:lightning-bolt"
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
            voltage = float(raw_v) * _SCALE_VOLTAGE   # e.g. 2296 → 229.6 V
            current = float(raw_i) * _SCALE_CURRENT   # e.g. 16   →   1.6 A
            return round(voltage * current)            # e.g. 229.6 × 1.6 = 367 W
        except ValueError:
            return None