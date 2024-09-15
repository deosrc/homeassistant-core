"""Tests the hikvision integration config flow."""

from unittest.mock import MagicMock

from homeassistant.components.hikvision.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

FAKE_CONFIG = {
    CONF_NAME: "fake_name",
    CONF_HOST: "fake_host",
    CONF_PORT: 1234,
    CONF_SSL: False,
    CONF_USERNAME: "fake_user",
    CONF_PASSWORD: "fake_password",
}


async def test_show_config_form(hass: HomeAssistant) -> None:
    """Test that the config form is shown."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_connection_failed(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the error when connection fails."""
    camera.return_value.get_id = 0
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "connection_failed"}


async def test_create_entry(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry is created when connection is successful."""
    camera.return_value.get_id = 1234
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == FAKE_CONFIG


async def test_title_from_config(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry title from the config is used."""
    camera.return_value.get_id = 1234
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "fake_name"


async def test_title_from_camera_name(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry title from the camera name is used."""
    config = FAKE_CONFIG.copy()
    del config[CONF_NAME]

    camera.return_value.get_id = 1234
    camera.return_value.get_name = "fake_camera"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "fake_camera"


async def test_title_from_hostname(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry title from the hostname is used."""
    config = FAKE_CONFIG.copy()
    del config[CONF_NAME]

    camera.return_value.get_id = 1234
    camera.return_value.get_name = None
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "fake_host"
