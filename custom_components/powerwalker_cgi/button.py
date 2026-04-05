import aiohttp
import logging
import random
import asyncio
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

_LOGGER = logging.getLogger(__name__)

# Essential headers to mimic the browser
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

    # Map the buttons to their internal CGI parameters
    # According to typical SNMP Web Pro v1.1: 1=10s Test, 3=Deep Test, 0=Cancel
    async_add_entities([
        PWButton(base_url, password, host, "10-Second Test", "test", "1", "mdi:timer-sand"),
        PWButton(base_url, password, host, "Deep Discharge Test", "test", "3", "mdi:battery-alert"),
        PWButton(base_url, password, host, "Cancel Test", "test", "0", "mdi:stop-circle")
    ])

class PWButton(ButtonEntity):
    def __init__(self, base_url, password, host, name, cmd, param, icon):
        self._base_url = base_url
        self._password = password
        self._cmd = cmd
        self._param = param
        self._attr_name = f"UPS {name}"
        self._attr_icon = icon
        self._attr_unique_id = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(
            identifiers={("powerwalker_cgi", host)},
            name="PowerWalker UPS",
        )

    def _generate_sid(self):
        """Generates a fresh random SID for every request."""
        return f"{random.random()}"

    async def async_press(self):
        """Handle the button press."""
        
        # Fresh SID for login
        pass_sid = self._generate_sid()
        login_url = f"{self._base_url}/cgi-bin/rtControl.cgi?name=password&?params={self._password}&{pass_sid}"
        
        # Fresh SID for the test command
        cmd_sid = self._generate_sid()
        # Using the &?sid= format found in your trace
        cmd_url = f"{self._base_url}/cgi-bin/rtControl.cgi?name={self._cmd}&?params={self._param}&?sid={cmd_sid}"

        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                # 1. Unlock session with password
                async with session.get(login_url, ssl=False, timeout=5) as login_resp:
                    _LOGGER.debug("Button Auth sent: %s", login_url)
                    await login_resp.text()
                
                # Tiny pause for the UPS card to process
                await asyncio.sleep(0.3)

                # 2. Execute the test
                async with session.get(cmd_url, ssl=False, timeout=5) as resp:
                    result = await resp.text()
                    _LOGGER.debug("Button Command sent: %s | Result: %s", cmd_url, result)
                    
        except Exception as e:
            _LOGGER.error("Failed to execute UPS button command: %s", e)