import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# The domain must match the folder name and manifest.json
DOMAIN = "powerwalker_cgi"

# List of platforms to support (the filenames sensor.py, switch.py, button.py)
PLATFORMS = ["sensor", "switch", "button"]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PowerWalker CGI from a config entry."""
    
    # Store the config data in hass.data so platforms can access it if needed
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # This tells Home Assistant to look at sensor.py, switch.py, and button.py
    # and run their 'async_setup_entry' functions.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This handles removing the integration without restarting HA
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok