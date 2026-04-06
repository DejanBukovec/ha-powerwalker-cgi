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
            return self.async_create_entry(
                title=f"UPS ({user_input['host']})", data=user_input
            )

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
        return PowerWalkerOptionsFlow()


class PowerWalkerOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("host",          default=current.get("host")): str,
                vol.Optional("use_https",     default=current.get("use_https", False)): bool,
                vol.Optional("port",          default=current.get("port", 80)): int,
                vol.Optional("username",      default=current.get("username", "admin")): str,
                vol.Optional("password",      default=current.get("password", "")): str,
                vol.Optional("scan_interval", default=current.get("scan_interval", 30)): int,
            }),
        )