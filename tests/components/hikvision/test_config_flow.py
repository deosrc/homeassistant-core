"""Tests the hikvision integration config flow."""

from unittest.mock import MagicMock

from homeassistant.components.hikvision.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

FAKE_CONFIG = {
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
    camera.return_value.get_name = None
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "connection_failed"}


async def test_create_entry(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry is created when connection is successful."""
    camera.return_value.get_name = "Test"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == FAKE_CONFIG
