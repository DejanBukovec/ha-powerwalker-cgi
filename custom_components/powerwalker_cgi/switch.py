"""
PowerWalker CGI — Switch platform.

Switch states are read from getControl.cgi via the coordinator — the same
poll that updates all sensors. No separate HTTP requests.

getControl.cgi raw response (space-separated, single line):
  1 1 1 0 2 30 30 0 0

The coordinator prepends a dummy token at index 0 so JS indices map directly:
  control_tokens[1] → alarm state    (1 = ON,  anything else = OFF)
  control_tokens[2] → UPS output     (1 = ON,  anything else = OFF)
  control_tokens[3] → test running   (1 = test active)

The "two bolt icons" bug was caused by _attr_assumed_state = True, which
renders a special "assumed state" card in HA with separate on/off buttons.
Removing that flag gives a standard clean toggle switch.
"""

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, _send_command

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    base_url    = entry_data["base_url"]
    password    = entry_data["password"]
    host        = entry_data["host"]

    async_add_entities([
        PWSwitch(
            coordinator, base_url, password, host,
            name           = "System Power",
            cgi_name       = "UPSOnOff",
            on_value       = "On",   # JS: setControl('UPSOnOff','On')
            off_value      = "Off",  # JS: setControl('UPSOnOff','Off')
            control_index  = 2,      # getControl.cgi token[2] = UPS output state
            icon           = "mdi:power",
        ),
        PWSwitch(
            coordinator, base_url, password, host,
            name           = "Alarm Control",
            cgi_name       = "AlarmOnOff",
            on_value       = "1",    # JS: setControl('AlarmOnOff','1')
            off_value      = "2",    # JS: setControl('AlarmOnOff','2') — NOT '0'!
            control_index  = 1,      # getControl.cgi token[1] = alarm state
            icon           = "mdi:bell",
        ),
    ])


class PWSwitch(CoordinatorEntity, SwitchEntity):
    """
    Switch backed by the shared coordinator for state reads.
    Write operations (turn_on / turn_off) go directly via _send_command()
    and then request a coordinator refresh so the UI updates promptly.
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
        # No _attr_assumed_state here — that was causing the double-bolt icon bug
        self._attr_device_info = DeviceInfo(
            identifiers={("powerwalker_cgi", host)},
            name="PowerWalker UPS",
            manufacturer="BlueWalker",
            model="VFI Series",
        )

    @property
    def is_on(self) -> bool | None:
        """Read real switch state from coordinator's getControl data."""
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
            # Request a fresh coordinator poll so state reflects the change immediately
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        if await _send_command(self._base_url, self._password, self._cgi_name, self._off_value):
            await self.coordinator.async_request_refresh()
