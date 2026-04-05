import aiohttp
import logging
import random
import asyncio
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    protocol = "https" if data.get("use_https") else "http"
    base_url = f"{protocol}://{data['host']}:{data['port']}"
    password = data.get("password", "")
    host = data['host']

    async_add_entities([
        PWSwitch(base_url, password, host, "System Power", "ups", "rtControl.cgi", "mdi:power"),
        PWSwitch(base_url, password, host, "Alarm Control", "alarmCtrl", "config.cgi", "mdi:bell")
    ])

class PWSwitch(SwitchEntity):
    def __init__(self, base_url, password, host, name, mask, endpoint, icon):
        self._base_url = base_url
        self._password = password
        self._mask = mask
        self._endpoint = endpoint
        self._attr_name = f"UPS {name}"
        self._attr_icon = icon
        self._attr_unique_id = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(identifiers={("powerwalker_cgi", host)}, name="PowerWalker UPS")
        self._attr_assumed_state = False
        self._is_on = True 

    def _generate_sid(self):
        """Generates a random SID similar to the browser."""
        return f"{random.random()}"

    async def _send_authenticated_command(self, param):
        """Sends login and command with fresh SIDs for each."""
        
        # 1. Password SID (Appended with &)
        pass_sid = self._generate_sid()
        login_url = f"{self._base_url}/cgi-bin/rtControl.cgi?name=password&?params={self._password}&{pass_sid}"
        
        # 2. Command SID (Appended with &?sid= to match your trace)
        cmd_sid = self._generate_sid()
        cmd_url = f"{self._base_url}/cgi-bin/{self._endpoint}?name={self._mask}&?params={param}&?sid={cmd_sid}"

        try:
            # Shared session to maintain the internal 'authenticated' state
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                # Step A: Authenticate
                async with session.get(login_url, ssl=False, timeout=5) as login_resp:
                    _LOGGER.debug("Login sent: %s", login_url)
                    await login_resp.text()
                
                # Tiny wait for the UPS to register the session
                await asyncio.sleep(0.3)

                # Step B: Command
                async with session.get(cmd_url, ssl=False, timeout=5) as resp:
                    result = await resp.text()
                    _LOGGER.debug("Command sent: %s | Result: %s", cmd_url, result)
                    return True
        except Exception as e:
            _LOGGER.error("Communication error: %s", e)
            return False

    async def async_turn_on(self, **kwargs):
        if await self._send_authenticated_command(1):
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        if await self._send_authenticated_command(0):
            self._is_on = False
            self.async_write_ha_state()