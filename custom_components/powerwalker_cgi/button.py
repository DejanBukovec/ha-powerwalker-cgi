"""
PowerWalker CGI — Button platform.

CGI names and values from the UPS HTML source:
  setControl('test10s','10')
  setControl('testDeep','deep')
  setControl('cancel','cn')
"""

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

from . import DOMAIN, _send_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    base_url   = entry_data["base_url"]
    password   = entry_data["password"]
    host       = entry_data["host"]

    async_add_entities([
        PWButton(base_url, password, host, "10-Second Test",      "test10s",  "10",   "mdi:timer-sand"),
        PWButton(base_url, password, host, "Deep Discharge Test", "testDeep", "deep", "mdi:battery-alert"),
        PWButton(base_url, password, host, "Cancel Test",         "cancel",   "cn",   "mdi:stop-circle"),
    ])


class PWButton(ButtonEntity):
    def __init__(self, base_url, password, host, name, cgi_name, param, icon):
        self._base_url = base_url
        self._password = password
        self._cgi_name = cgi_name
        self._param    = param

        self._attr_name        = f"UPS {name}"
        self._attr_icon        = icon
        self._attr_unique_id   = f"pw_{host}_{name.lower().replace(' ', '_')}"
        self._attr_device_info = DeviceInfo(
            identifiers={("powerwalker_cgi", host)},
            name="PowerWalker UPS",
            manufacturer="BlueWalker",
            model="VFI Series",
        )

    async def async_press(self):
        success = await _send_command(
            self._base_url, self._password, self._cgi_name, self._param
        )
        if not success:
            _LOGGER.error(
                "Button '%s': command %s=%s did not receive ACK",
                self._attr_name, self._cgi_name, self._param,
            )