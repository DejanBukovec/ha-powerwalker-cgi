import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# The domain must match your folder name
DOMAIN = "powerwalker_cgi"

# The platforms you have created files for
PLATFORMS = ["sensor", "switch", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PowerWalker CGI from a config entry."""
    
    # Store the entry data so other platforms can access it
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Registers a listener to update the integration when options are changed
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # This triggers the async_setup_entry in sensor.py, switch.py, etc.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # This forces the integration to reload if you change the IP/Password in the UI
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Properly shuts down the platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok