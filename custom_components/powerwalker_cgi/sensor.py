"""
PowerWalker CGI — Sensor platform.

All sensors are CoordinatorEntity instances — they read from coordinator.data
and never make their own HTTP requests. The full update cycle is one GET to
realInfo.cgi (plus one GET to getControl.cgi for switch states), shared across
all entities.

Index mapping verified against the actual raw response of PowerWalker VFI 2000:

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
  [35–36] zeros
  [37] "999999999"  → EMD temperature (not fitted → ignored)
  [38] "999999999"  → Humidity        (not fitted → ignored)
  [39–47] zeros
  [48] "100"        → Output Active Power    (W)
"""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

_NOT_PRESENT = "999999999"

# (friendly name, token index, unit, scale factor)
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
    ("Output Active Power",   48, "W",   1   ),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    entry_data  = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    host        = entry_data["host"]

    async_add_entities(
        PWSensor(coordinator, host, name, index, unit, scale)
        for name, index, unit, scale in SENSOR_DEFINITIONS
    )


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

        tokens: list[str] = data.get("sensors", [])
        if self._index >= len(tokens):
            _LOGGER.debug(
                "%s: index %d out of range (got %d tokens)",
                self._attr_name, self._index, len(tokens),
            )
            return None

        raw = tokens[self._index].strip()

        if not raw or raw == _NOT_PRESENT or "---" in raw:
            return None

        # Text / status field — return as-is
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
