"""Fixtures for Hikvision tests."""

from unittest.mock import create_autospec, patch

from pyhik.hikvision import HikCamera
import pytest

from homeassistant.components.hikvision.const import DOMAIN

from .const import FAKE_CONFIG

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def camera():
    """Mock a HikCamera client."""
    camera_mock = create_autospec(HikCamera, instance=True)

    with patch("homeassistant.components.hikvision.HikCamera") as class_mock:
        class_mock.return_value = camera_mock
        yield class_mock


@pytest.fixture(autouse=True)
def config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(domain=DOMAIN, data=FAKE_CONFIG.copy())


@pytest.fixture(autouse=True)
def config_entry_with_options():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN, data=FAKE_CONFIG.copy(), options={"delay.line_crossing": 12}
    )
