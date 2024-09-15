"""Config flow for hikvision integration."""

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
import homeassistant.helpers.config_validation as cv

from . import HikvisionData
from .const import DEFAULT_PORT, DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SSL, default=False): cv.boolean,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class HikvisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hikvision."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            result = await self.hass.async_add_executor_job(
                self.create_connection,
                host,
                port,
                user_input[CONF_SSL],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )

            if result.cam_id:
                await self.async_set_unique_id(str(result.cam_id))
                title = user_input.get(CONF_NAME) or result.name or host
                return self.async_create_entry(title=title, data=user_input)

            errors["base"] = "connection_failed"

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    def create_connection(
        self, host: str, port: int, is_https: bool, username: str, password: str
    ) -> HikvisionData:
        """Check the connection to a Hikvision camera or NVR.

        Returns the name of the Camera/NVR, or None if a connection could not be established.
        """
        return HikvisionData(host, port, is_https, None, username, password)
