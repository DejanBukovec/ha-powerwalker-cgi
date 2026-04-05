import logging
import aiohttp
import async_timeout
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    protocol = "https" if data.get("use_https") else "http"
    base_url = f"{protocol}://{data['host']}:{data['port']}"
    auth = (data.get("username"), data.get("password", ""))
    scan_interval = timedelta(seconds=data.get("scan_interval", 30))

    sensor_definitions = [
        ("Status Mode",           0,  None,  1),
        ("Internal Temperature",  1,  "°C",  0.1),
        ("Fault Type",            7,  None,  1),
        ("Warning",               8,  None,  1),
        ("Battery Voltage",       9,  "V",   0.1),
        ("Battery Capacity",      10, "%",   1),
        ("Remaining Backup Time", 11, "min", 1),
        ("Input Frequency",       12, "Hz",  0.1),
        ("Input Voltage",         13, "V",   0.1),
        ("Output Frequency",      15, "Hz",  0.1),
        ("Output Voltage",        16, "V",   0.1),
        ("Load Level",            18, "%",   1),
        ("Output Current",        36, "A",   0.1),
        ("Output Active Power",   47, "W",   1),
    ]

    sensors = [
        PWSensor(base_url, auth, data["host"], scan_interval, *s)
        for s in sensor_definitions
    ]
    async_add_entities(sensors, update_before_add=True)

class PWSensor(SensorEntity):
    def __init__(self, base_url, auth, host, scan_interval, name, index, unit, scale):
        self._base_url  = base_url
        self._auth      = auth
        self._index     = index
        self._scale     = scale
        self._attr_name = f"UPS {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(
            identifiers={("powerwalker_cgi", host)},
            name="PowerWalker UPS",
            manufacturer="BlueWalker",
            model="VFI Series",
        )
        # ✅ This is what actually tells HA how often to poll this entity
        self._attr_should_poll = True
        self._scan_interval = scan_interval

    @property
    def scan_interval(self) -> timedelta:
        return self._scan_interval

    async def async_update(self):
        url = f"{self._base_url}/cgi-bin/realInfo.cgi"
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        auth=aiohttp.BasicAuth(self._auth[0], self._auth[1]),
                        ssl=False,
                    ) as resp:
                        lines = (await resp.text()).split("\n")
                        val = lines[self._index].strip()
                        if val == "---":
                            self._attr_native_value = None
                        elif self._attr_native_unit_of_measurement:
                            self._attr_native_value = round(float(val) * self._scale, 1)
                        else:
                            self._attr_native_value = val
        except Exception as e:
            _LOGGER.error("Update failed for %s: %s", self._attr_name, e)