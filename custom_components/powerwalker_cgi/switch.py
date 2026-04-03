from homeassistant.components.switch import SwitchEntity
import requests

async def async_setup_entry(hass, config_entry, async_add_entities):
    host = config_entry.data["host"]
    auth = (config_entry.data.get("username"), config_entry.data.get("password", ""))
    
    async_add_entities([
        PWConfigSwitch(host, auth, "Alarm Control", "alarmCtrl"),
        PWPowerSwitch(host, auth, "System Power", "ups")
    ])

class PWConfigSwitch(SwitchEntity):
    """For persistent settings like Alarms"""
    def __init__(self, host, auth, name, mask):
        self._host, self._auth, self._mask = host, auth, mask
        self._attr_name = f"UPS {name}"
        self._is_on = False

    def turn_on(self, **kwargs):
        requests.get(f"http://{self._host}/cgi-bin/config.cgi?name={self._mask}&?params=1&", auth=self._auth)
        self._is_on = True

    def turn_off(self, **kwargs):
        requests.get(f"http://{self._host}/cgi-bin/config.cgi?name={self._mask}&?params=0&", auth=self._auth)
        self._is_on = False

class PWPowerSwitch(SwitchEntity):
    """For Momentary Power Toggle"""
    def __init__(self, host, auth, name, mask):
        self._host, self._auth, self._mask = host, auth, mask
        self._attr_name = f"UPS {name}"

    @property
    def is_on(self):
        # We assume it's on if we can reach the API
        return True 

    def turn_on(self, **kwargs):
        requests.get(f"http://{self._host}/cgi-bin/rtControl.cgi?name={self._mask}&?params=1&", auth=self._auth)

    def turn_off(self, **kwargs):
        requests.get(f"http://{self._host}/cgi-bin/rtControl.cgi?name={self._mask}&?params=0&", auth=self._auth)