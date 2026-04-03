from homeassistant.components.button import ButtonEntity
import requests

async def async_setup_entry(hass, config_entry, async_add_entities):
    host = config_entry.data["host"]
    auth = (config_entry.data.get("username"), config_entry.data.get("password", ""))
    
    async_add_entities([
        PWButton(host, auth, "10-Second Self Test", "test", "1"),
        PWButton(host, auth, "Deep Discharge Test", "test", "3"),
        PWButton(host, auth, "Cancel Test", "test", "0")
    ])

class PWButton(ButtonEntity):
    def __init__(self, host, auth, name, cmd, param):
        self._host, self._auth = host, auth
        self._attr_name = f"UPS {name}"
        self._cmd, self._param = cmd, param

    def press(self):
        requests.get(f"http://{self._host}/cgi-bin/rtControl.cgi?name={self._cmd}&?params={self._param}&", auth=self._auth)