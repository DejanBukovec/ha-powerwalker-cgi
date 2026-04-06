"""
PowerWalker CGI Integration — core module.

Architecture:
  - One DataUpdateCoordinator fetches BOTH realInfo.cgi (sensors) and
    getControl.cgi (switch states) on every poll interval.
  - sensor.py, switch.py and button.py all read from coordinator.data —
    zero additional HTTP requests on update.
  - Controls (switches/buttons) call _send_command() which does a fresh
    login + command over a single persistent TCP session.

coordinator.data structure:
  {
      "sensors":  list[str],   # newline-split tokens from realInfo.cgi
      "controls": list[str],   # newline-split tokens from getControl.cgi
  }

getControl.cgi raw response (newline-separated):
  Line 0: "1"  → (ignored / header)
  Line 1: "1"  → alarm state     (1 = ON,  other = OFF)
  Line 2: "1"  → UPS output ON   (1 = ON,  other = OFF)
  Line 3: "1"  → test running    (1 = test active)
  Line 4: "2"  → outlet control
  Line 5: "30" → outlet off delay
  Line 6: "30" → outlet on delay
  Line 7: "0"  → reboot off delay
  Line 8: "0"  → reboot on delay

Verified from two real device responses:
  UPS ON:  1 / 1 / 1 / 1 / 2 / 30 / 30 / 0 / 0
  UPS OFF: 1 / 1 / 0 / 0 / 2 / 30 / 30 / 0 / 0
"""

import asyncio
import logging
import random
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

DOMAIN = "powerwalker_cgi"
PLATFORMS = ["sensor", "switch", "button"]

_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}


def _sid() -> str:
    return str(random.random())


async def _fetch_coordinator_data(base_url: str) -> dict:
    """
    Fetch realInfo.cgi and getControl.cgi without authentication.
    Both endpoints are publicly readable — no login needed for GET.
    Both return newline-separated values.
    """
    sensor_url  = f"{base_url}/cgi-bin/realInfo.cgi?{_sid()}"
    control_url = f"{base_url}/cgi-bin/getControl.cgi?{_sid()}"

    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            async with session.get(
                sensor_url, ssl=False, timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                sensor_raw = await resp.text()

            async with session.get(
                control_url, ssl=False, timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                control_raw = await resp.text()

        # Both CGI responses are newline-separated, one value per line
        sensor_tokens  = [t.strip() for t in sensor_raw.strip().split("\n")  if t.strip()]
        control_tokens = [t.strip() for t in control_raw.strip().split("\n") if t.strip()]

        _LOGGER.debug("sensor  tokens (%d): %s", len(sensor_tokens),  sensor_tokens)
        _LOGGER.debug("control tokens (%d): %s", len(control_tokens), control_tokens)

        return {"sensors": sensor_tokens, "controls": control_tokens}

    except Exception as exc:
        raise UpdateFailed(f"Coordinator fetch failed: {exc}") from exc


async def _send_command(base_url: str, password: str, cgi_name: str, value: str) -> bool:
    """
    Authenticate then send a control command over a single persistent TCP session.
    The UPS card tracks auth state per TCP socket, so both requests must share
    the same aiohttp.TCPConnector instance.

    URL format from the UPS page JS:
      makeRequest("/cgi-bin/rtControl.cgi?name=" + mask + "&?params=" + value + "&", 1)
      → appends "?sid=" + Math.random()
      → final: rtControl.cgi?name=X&?params=Y&?sid=0.123
    """
    login_url = (
        f"{base_url}/cgi-bin/rtControl.cgi"
        f"?name=password&?params={password}&?sid={_sid()}"
    )
    cmd_url = (
        f"{base_url}/cgi-bin/rtControl.cgi"
        f"?name={cgi_name}&?params={value}&?sid={_sid()}"
    )

    connector = aiohttp.TCPConnector(ssl=False, force_close=False)
    try:
        async with aiohttp.ClientSession(connector=connector, headers=_HEADERS) as session:
            async with session.get(login_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                login_resp = await resp.text()
                _LOGGER.debug("Login response: %s", login_resp.strip())
                if "(ACK" not in login_resp:
                    _LOGGER.warning("Login may have failed: %s", login_resp.strip())

            await asyncio.sleep(0.4)

            async with session.get(cmd_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                result = await resp.text()
                _LOGGER.debug("Command %s=%s → %s", cgi_name, value, result.strip())
                if "(ACK" in result:
                    return True
                _LOGGER.error(
                    "Command %s=%s rejected. Response: %s", cgi_name, value, result.strip()
                )
                return False

    except Exception as exc:
        _LOGGER.error("Communication error [%s=%s]: %s", cgi_name, value, exc)
        return False
    finally:
        await connector.close()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    protocol = "https" if entry.data.get("use_https") else "http"
    base_url  = f"{protocol}://{entry.data['host']}:{entry.data['port']}"
    password  = entry.data.get("password", "")
    interval  = timedelta(seconds=entry.data.get("scan_interval", 30))

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"PowerWalker {entry.data['host']}",
        update_method=lambda: _fetch_coordinator_data(base_url),
        update_interval=interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "base_url":    base_url,
        "password":    password,
        "host":        entry.data["host"],
    }

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok