import aiohttp
import logging
import random
import asyncio
from homeassistant.components.button import ButtonEntity
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
        PWButton(base_url, password, host, "10-Second Test",    "test10s",  "10",   "mdi:timer-sand"),
        PWButton(base_url, password, host, "Deep Discharge Test","testDeep","deep", "mdi:battery-alert"),
        PWButton(base_url, password, host, "Cancel Test",       "cancel",   "cn",   "mdi:stop-circle"),
    ])

class PWButton(ButtonEntity):
    def __init__(self, base_url, password, host, name, cmd, param, icon):
        self._base_url  = base_url
        self._password  = password
        self._cmd       = cmd
        self._param     = param
        self._attr_name = f"UPS {name}"
        self._attr_icon = icon
        self._attr_unique_id = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(
            identifiers={("powerwalker_cgi", host)}, name="PowerWalker UPS"
        )

    def _sid(self):
        return str(random.random())

    async def async_press(self):
        login_url = f"{self._base_url}/cgi-bin/rtControl.cgi?name=password&?params={self._password}&{self._sid()}"
        cmd_url   = f"{self._base_url}/cgi-bin/rtControl.cgi?name={self._cmd}&?params={self._param}&{self._sid()}"
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(login_url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)):
                    pass
                await asyncio.sleep(0.3)
                async with session.get(cmd_url, ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    result = await resp.text()
                    _LOGGER.debug("Button %s result: %s", self._cmd, result)
                    if "(ACK" not in result:
                        _LOGGER.warning("Unexpected response for %s: %s", self._cmd, result)
        except Exception as e:
            _LOGGER.error("Button command failed [%s]: %s", self._attr_name, e)