"""Tests the hikvision integration config flow."""

from unittest.mock import MagicMock

import pytest

from homeassistant.components.hikvision.const import (
    CONF_CUSTOMIZE,
    CONF_IGNORED,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.const import CONF_DELAY, CONF_NAME, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import homeassistant.helpers.issue_registry as ir

from .const import FAKE_CONFIG, LEGACY_PLATFORM_CONFIG


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
    camera.return_value.get_id = "1234"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == FAKE_CONFIG
    assert result["result"].unique_id == "1234"


async def test_duplicate_entry(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry is created when connection is successful."""
    camera.return_value.get_id = "1234"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == FAKE_CONFIG
    assert result["result"].unique_id == "1234"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_title_from_config(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry title from the config is used."""
    camera.return_value.get_id = "1234"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=FAKE_CONFIG
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "fake_name"


async def test_title_from_camera_name(hass: HomeAssistant, camera: MagicMock) -> None:
    """Test the entry title from the camera name is used."""
    config = FAKE_CONFIG.copy()
    del config[CONF_NAME]

    camera.return_value.get_id = "1234"
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

    camera.return_value.get_id = "1234"
    camera.return_value.get_name = None
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "fake_host"


@pytest.mark.parametrize(
    ("ssl", "url"), [(True, "https://fake_host"), (False, "http://fake_host")]
)
async def test_url(hass: HomeAssistant, camera: MagicMock, ssl: bool, url: str) -> None:
    """Test the URL used for SSL settings."""
    config = FAKE_CONFIG.copy()
    config[CONF_SSL] = ssl

    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )

    camera.assert_called_with(url, 1234, "fake_user", "fake_password")


async def test_yaml_import_with_delays(hass: HomeAssistant) -> None:
    """Check an issue is created if YAML delay settings are present."""
    yaml_config: dict = LEGACY_PLATFORM_CONFIG.copy()
    yaml_config.update({CONF_CUSTOMIZE: {"Some Sensor": {CONF_DELAY: 12}}})

    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=yaml_config
    )

    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, "customize_config_delay_present")
    assert issue


async def test_yaml_import_with_ignored(hass: HomeAssistant) -> None:
    """Check an issue is created if YAML ignored settings are present."""
    yaml_config: dict = LEGACY_PLATFORM_CONFIG.copy()
    yaml_config.update({CONF_CUSTOMIZE: {"Some Sensor": {CONF_IGNORED: True}}})

    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=yaml_config
    )

    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, "customize_config_ignored_present")
    assert issue
