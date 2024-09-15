"""Fixtures for Hikvision tests."""

from unittest.mock import create_autospec, patch

from pyhik.hikvision import HikCamera
import pytest


@pytest.fixture(autouse=True)
def camera():
    """Mock a HikCamera client."""
    camera_mock = create_autospec(HikCamera, instance=True)

    with patch("homeassistant.components.hikvision.HikCamera") as class_mock:
        class_mock.return_value = camera_mock
        yield class_mock
