import vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

DOMAIN = "powerwalker_cgi"

class PowerWalkerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Set default ports if blank
            if not user_input.get("port"):
                user_input["port"] = 443 if user_input.get("use_https") else 80
            return self.async_create_entry(title=f"UPS ({user_input['host']})", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Optional("use_https", default=False): bool,
                vol.Optional("port"): cv.port,
                vol.Optional("username", default="admin"): str,
                vol.Optional("password"): str,
                vol.Optional("scan_interval", default=30): int,
            }),
        )