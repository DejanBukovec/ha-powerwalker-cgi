import aiohttp
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    protocol = "https" if data.get("use_https") else "http"
    base_url = f"{protocol}://{data['host']}:{data['port']}"
    auth = (data.get("username"), data.get("password", ""))
    host = data['host']

    async_add_entities([
        PWButton(base_url, auth, host, "10-Second Test", "test", "1"),
        PWButton(base_url, auth, host, "Deep Discharge Test", "test", "3"),
        PWButton(base_url, auth, host, "Cancel Test", "test", "0")
    ])

class PWButton(ButtonEntity):
    def __init__(self, base_url, auth, host, name, cmd, param):
        self._base_url, self._auth, self._cmd, self._param = base_url, auth, cmd, param
        self._attr_name = f"UPS {name}"
        self._attr_unique_id = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(identifiers={("powerwalker_cgi", host)}, name="PowerWalker UPS")

    async def async_press(self):
        url = f"{self._base_url}/cgi-bin/rtControl.cgi?name={self._cmd}&?params={self._param}&"
        async with aiohttp.ClientSession() as session:
            await session.get(url, auth=aiohttp.BasicAuth(self._auth[0], self._auth[1]), ssl=False)