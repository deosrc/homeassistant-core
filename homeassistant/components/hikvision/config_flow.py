"""Config flow for hikvision integration."""

from typing import Any

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_DELAY,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue

from . import HikvisionData
from .const import CONF_CUSTOMIZE, CONF_IGNORED, DEFAULT_PORT, DOMAIN

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

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional("delay.motion"): cv.positive_int,
        vol.Optional("delay.line_crossing"): cv.positive_int,
        vol.Optional("delay.field_detection"): cv.positive_int,
        vol.Optional("delay.tamper_detection"): cv.positive_int,
        vol.Optional("delay.shelter_alarm"): cv.positive_int,
        vol.Optional("delay.disk_full"): cv.positive_int,
        vol.Optional("delay.disk_error"): cv.positive_int,
        vol.Optional("delay.net_interface_broken"): cv.positive_int,
        vol.Optional("delay.ip_conflict"): cv.positive_int,
        vol.Optional("delay.illegal_access"): cv.positive_int,
        vol.Optional("delay.video_mismatch"): cv.positive_int,
        vol.Optional("delay.bad_video"): cv.positive_int,
        vol.Optional("delay.pir_alarm"): cv.positive_int,
        vol.Optional("delay.face_detection"): cv.positive_int,
        vol.Optional("delay.scene_change_detection"): cv.positive_int,
        vol.Optional("delay.io"): cv.positive_int,
        vol.Optional("delay.unattended_baggage"): cv.positive_int,
        vol.Optional("delay.attended_baggage"): cv.positive_int,
        vol.Optional("delay.recording_failure"): cv.positive_int,
        vol.Optional("delay.exiting_region"): cv.positive_int,
        vol.Optional("delay.entering_region"): cv.positive_int,
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class HikvisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hikvision."""

    VERSION = 1

    async def async_step_import(
        self, legacy_config: dict
    ) -> config_entries.ConfigFlowResult:
        """Import the legacy yaml config."""
        if legacy_config.get(CONF_CUSTOMIZE):
            for sensor_config in legacy_config[CONF_CUSTOMIZE].values():
                if sensor_config.get(CONF_IGNORED):
                    async_create_issue(
                        self.hass,
                        DOMAIN,
                        "customize_config_ignored_present",
                        is_fixable=False,
                        is_persistent=False,
                        issue_domain=DOMAIN,
                        severity=IssueSeverity.WARNING,
                        translation_key="customize_config_ignored_present",
                        translation_placeholders={
                            "integration_title": "Hikvision",
                        },
                    )
                    break
            for sensor_config in legacy_config[CONF_CUSTOMIZE].values():
                if sensor_config.get(CONF_DELAY):
                    async_create_issue(
                        self.hass,
                        DOMAIN,
                        "customize_config_delay_present",
                        is_fixable=False,
                        is_persistent=False,
                        issue_domain=DOMAIN,
                        severity=IssueSeverity.WARNING,
                        translation_key="customize_config_delay_present",
                        translation_placeholders={
                            "integration_title": "Hikvision",
                        },
                    )
                    break

        del legacy_config[CONF_CUSTOMIZE]
        del legacy_config["platform"]

        try:
            conn = await self.hass.async_add_executor_job(
                self._create_connection, legacy_config
            )
            result = await self._async_create_entry(legacy_config, conn)
            self._create_deprecated_yaml_issue()
        except data_entry_flow.AbortFlow as err:
            if err.reason == "already_configured":
                self._create_deprecated_yaml_issue()
                return self.async_abort(reason="already_configured")
            raise
        except ConnectionError as err:
            async_create_issue(
                self.hass,
                DOMAIN,
                "deprecated_yaml_cannot_connect",
                is_fixable=False,
                is_persistent=False,
                issue_domain=DOMAIN,
                severity=IssueSeverity.WARNING,
                translation_key="deprecated_yaml_import_issue_cannot_connect",
                translation_placeholders={
                    "integration_title": "Hikvision",
                    "url": "https://www.home-assistant.io/integrations/hikvision/",
                },
            )
            raise data_entry_flow.AbortFlow("deprecated_yaml_import_failed") from err
        else:
            return result

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                conn = await self.hass.async_add_executor_job(
                    self._create_connection, user_input
                )
                return await self._async_create_entry(user_input, conn)
            except ConnectionError:
                errors["base"] = "connection_failed"

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    async def _async_create_entry(
        self, conf: dict, conn: HikvisionData
    ) -> config_entries.ConfigFlowResult:
        """Create the config entry."""
        await self.async_set_unique_id(str(conn.cam_id))
        self._abort_if_unique_id_configured()
        title = conf.get(CONF_NAME) or conn.name or conf[CONF_HOST]
        return self.async_create_entry(title=title, data=conf)

    def _create_deprecated_yaml_issue(self) -> None:
        """Create an issue for successful yaml import."""
        async_create_issue(
            self.hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            is_fixable=False,
            is_persistent=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "Hikvision",
            },
        )

    def _create_connection(self, inputs: dict) -> HikvisionData:
        """Create a connection to the Hikvision camera or NVR."""
        host = inputs[CONF_HOST]
        port = inputs.get(CONF_PORT)
        is_https = inputs.get(CONF_SSL, False)
        username = inputs[CONF_USERNAME]
        password = inputs[CONF_PASSWORD]

        conn = HikvisionData(host, port, is_https, None, username, password)
        if conn.cam_id:
            return conn

        raise ConnectionError

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return HikvisionOptionsFlowHandler(config_entry)


class HikvisionOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle options flow for the Hikvision integraton."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
