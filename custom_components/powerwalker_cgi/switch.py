import aiohttp
import logging
import random
import asyncio
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    protocol = "https" if data.get("use_https") else "http"
    base_url = f"{protocol}://{data['host']}:{data['port']}"
    password = data.get("password", "")
    host = data["host"]

    async_add_entities([
        PWSwitch(base_url, password, host, "System Power",  "UPSOnOff",   "On",  "Off",  "mdi:power"),
        PWSwitch(base_url, password, host, "Alarm Control", "AlarmOnOff", "1",   "2",    "mdi:bell"),
    ])

class PWSwitch(SwitchEntity):
    def __init__(self, base_url, password, host, name, mask, on_value, off_value, icon):
        self._base_url  = base_url
        self._password  = password
        self._mask      = mask
        self._on_value  = on_value
        self._off_value = off_value
        self._attr_name = f"UPS {name}"
        self._attr_icon = icon
        self._attr_unique_id = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(
            identifiers={("powerwalker_cgi", host)}, name="PowerWalker UPS"
        )
        self._attr_assumed_state = True
        self._is_on = True

    @property
    def is_on(self):
        return self._is_on

    def _sid(self):
        return str(random.random())

    async def _send_command(self, value):
        login_url = f"{self._base_url}/cgi-bin/rtControl.cgi?name=password&?params={self._password}&{self._sid()}"
        cmd_url   = f"{self._base_url}/cgi-bin/rtControl.cgi?name={self._mask}&?params={value}&{self._sid()}"
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(login_url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)):
                    pass
                await asyncio.sleep(0.3)
                async with session.get(cmd_url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    result = await resp.text()
                    _LOGGER.debug("Command %s=%s result: %s", self._mask, value, result)
                    return "(ACK" in result
        except Exception as e:
            _LOGGER.error("Switch command failed [%s]: %s", self._attr_name, e)
            return False

    async def async_turn_on(self, **kwargs):
        if await self._send_command(self._on_value):
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        if await self._send_command(self._off_value):
            self._is_on = False
            self.async_write_ha_state()