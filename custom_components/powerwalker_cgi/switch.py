import aiohttp
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    protocol = "https" if data.get("use_https") else "http"
    base_url = f"{protocol}://{data['host']}:{data['port']}"
    auth = (data.get("username"), data.get("password", ""))
    host = data['host']

    async_add_entities([
        PWSwitch(base_url, auth, host, "Alarm Control", "alarmCtrl", "config.cgi"),
        PWSwitch(base_url, auth, host, "System Power", "ups", "rtControl.cgi")
    ], update_before_add=True)

class PWSwitch(SwitchEntity):
    def __init__(self, base_url, auth, host, name, mask, endpoint):
        self._base_url, self._auth, self._mask, self._endpoint = base_url, auth, mask, endpoint
        self._attr_name = f"UPS {name}"
        self._attr_unique_id = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(identifiers={("powerwalker_cgi", host)}, name="PowerWalker UPS")
        self._is_on = True

    @property
    def is_on(self): return self._is_on

    async def _send_cmd(self, param):
        url = f"{self._base_url}/cgi-bin/{self._endpoint}?name={self._mask}&?params={param}&"
        async with aiohttp.ClientSession() as session:
            await session.get(url, auth=aiohttp.BasicAuth(self._auth[0], self._auth[1]), ssl=False)

    async def async_turn_on(self, **kwargs):
        await self._send_cmd(1)
        self._is_on = True

    async def async_turn_off(self, **kwargs):
        await self._send_cmd(0)
        self._is_on = False