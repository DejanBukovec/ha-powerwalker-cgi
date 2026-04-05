import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

DOMAIN = "powerwalker_cgi"

class PowerWalkerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PowerWalkerOptionsFlow()  # No need to pass config_entry here anymore

class PowerWalkerOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # This updates the entry data with new values from the settings button
            return self.async_create_entry(title="", data=user_input)

        # Access existing data via self.config_entry.data
        current_config = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("host", default=current_config.get("host")): str,
                vol.Optional("use_https", default=current_config.get("use_https", False)): bool,
                vol.Optional("port", default=current_config.get("port", 80)): int,
                vol.Optional("username", default=current_config.get("username", "admin")): str,
                vol.Optional("password", default=current_config.get("password", "")): str,
                vol.Optional("scan_interval", default=current_config.get("scan_interval", 30)): int,
            }),
        )