"""
PowerWalker CGI — Switch platform.

Switch states are read from getControl.cgi via the coordinator.

getControl.cgi raw response (newline-separated, verified from device):
  UPS ON:  index[0]=1, index[1]=1, index[2]=1, index[3]=1, ...
  UPS OFF: index[0]=1, index[1]=1, index[2]=0, index[3]=0, ...

  index[1] → alarm state   (1 = alarm ON)
  index[2] → UPS output    (1 = output ON / inverter running)

Note: No dummy offset needed — response is already newline-split with
direct 0-based indices (unlike the old space-split approach).
"""

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, _send_command

_LOGGER = logging.getLogger(__name__)

# getControl.cgi token indices (0-based, newline-split)
_CTRL_ALARM_IDX  = 1   # 1 = alarm ON,   other = OFF
_CTRL_OUTPUT_IDX = 2   # 1 = output ON,  other = OFF


async def async_setup_entry(hass, config_entry, async_add_entities):
    entry_data  = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    base_url    = entry_data["base_url"]
    password    = entry_data["password"]
    host        = entry_data["host"]

    async_add_entities([
        PWSwitch(
            coordinator, base_url, password, host,
            name          = "System Power",
            cgi_name      = "UPSOnOff",
            on_value      = "On",        # JS: setControl('UPSOnOff','On')
            off_value     = "Off",       # JS: setControl('UPSOnOff','Off')
            control_index = _CTRL_OUTPUT_IDX,
            icon          = "mdi:power",
        ),
        PWSwitch(
            coordinator, base_url, password, host,
            name          = "Alarm Control",
            cgi_name      = "AlarmOnOff",
            on_value      = "1",         # JS: setControl('AlarmOnOff','1')
            off_value     = "2",         # JS: setControl('AlarmOnOff','2') — NOT '0'!
            control_index = _CTRL_ALARM_IDX,
            icon          = "mdi:bell",
        ),
    ])


class PWSwitch(CoordinatorEntity, SwitchEntity):
    """
    Switch backed by the coordinator for real state reads.
    Write operations go directly via _send_command() and then
    request a coordinator refresh so the UI updates promptly.
    """

    def __init__(
        self, coordinator, base_url, password, host,
        name, cgi_name, on_value, off_value, control_index, icon,
    ):
        super().__init__(coordinator)
        self._base_url      = base_url
        self._password      = password
        self._cgi_name      = cgi_name
        self._on_value      = on_value
        self._off_value     = off_value
        self._control_index = control_index

        self._attr_name        = f"UPS {name}"
        self._attr_icon        = icon
        self._attr_unique_id   = f"pw_{host}_{name.lower().replace(' ', '_')}"
        # No _attr_assumed_state — that was causing the double-bolt icon bug
        self._attr_device_info = DeviceInfo(
            identifiers={("powerwalker_cgi", host)},
            name="PowerWalker UPS",
            manufacturer="BlueWalker",
            model="VFI Series",
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        controls: list[str] = data.get("controls", [])
        if self._control_index >= len(controls):
            return None
        try:
            return int(controls[self._control_index]) == 1
        except (ValueError, IndexError):
            return None

    async def async_turn_on(self, **kwargs):
        if await _send_command(self._base_url, self._password, self._cgi_name, self._on_value):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        if await _send_command(self._base_url, self._password, self._cgi_name, self._off_value):
            await self.coordinator.async_request_refresh()