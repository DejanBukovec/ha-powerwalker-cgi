from homeassistant.components.sensor import SensorEntity
import requests
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    host = config_entry.data["host"]
    auth = (config_entry.data.get("username"), config_entry.data.get("password", ""))
    
    # Mapping based on your JS code: (Name, Index, Unit, Scale)
    sensor_map = [
        ("Status Mode", 0, None, 1),
        ("Internal Temperature", 1, "°C", 0.1),
        ("Fault Type", 7, None, 1),
        ("Warning", 8, None, 1),
        ("Battery Voltage", 9, "V", 0.1),
        ("Battery Capacity", 10, "%", 1),
        ("Remaining Backup Time", 11, "min", 1),
        ("Input Frequency", 12, "Hz", 0.1),
        ("Input Voltage", 13, "V", 0.1),
        ("Output Frequency", 15, "Hz", 0.1),
        ("Output Voltage", 16, "V", 0.1),
        ("Load Level", 18, "%", 1),
        ("Output Current", 36, "A", 0.1),
        ("Output Active Power", 47, "W", 1),
    ]
    
    async_add_entities([PWSensor(host, auth, *s) for s in sensor_map])

class PWSensor(SensorEntity):
    def __init__(self, host, auth, name, index, unit, scale):
        self._host, self._auth = host, auth
        self._attr_name = f"UPS {name}"
        self._index = index
        self._attr_native_unit_of_measurement = unit
        self._scale = scale

    def update(self):
        try:
            r = requests.get(f"http://{self._host}/cgi-bin/realInfo.cgi", auth=self._auth, timeout=5)
            lines = r.text.split('\n')
            val = lines[self._index].strip()
            
            if val == "---":
                self._attr_native_value = None
            elif self._attr_native_unit_of_measurement is not None:
                self._attr_native_value = round(float(val) * self._scale, 1)
            else:
                self._attr_native_value = val # String values (Mode/Fault)
        except Exception as e:
            _LOGGER.error("Update failed for %s: %s", self._attr_name, e)