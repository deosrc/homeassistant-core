"""Test the binary sensor platform of the Hikvision integration."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.mark.parametrize(("cam_type"), [("NVR"), ("")])
async def test_sensor_setup(
    hass: HomeAssistant, config_entry: MockConfigEntry, camera: MagicMock, cam_type: str
) -> None:
    """Test sensor naming for different device types."""
    camera.return_value.get_id = 1234
    camera.return_value.get_type = cam_type
    camera.return_value.current_event_states = {
        "test sensor": [
            [
                False,  # Sensor State
                1,  # Channel Number (for NVRs)
                0,
                datetime(2024, 9, 15, 17, 28, 24, 938074),  # Last update time
            ]
        ]
    }

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    if cam_type == "NVR":
        sensor_entity_id = "binary_sensor.fake_name_test_sensor_1"
        sensor_name = "fake_name test sensor 1"
    else:
        sensor_entity_id = "binary_sensor.fake_name_test_sensor"
        sensor_name = "fake_name test sensor"

    entity_registry_entry = hass.data["entity_registry"].entities.data[sensor_entity_id]

    assert hass.states.get(sensor_entity_id) is not None
    assert entity_registry_entry.original_name == sensor_name
    assert entity_registry_entry.unique_id == "1234.test sensor.1"


async def test_callback_registered(
    hass: HomeAssistant, config_entry: MockConfigEntry, camera: MagicMock
) -> None:
    """Test callback is registered when sensor is created."""
    camera.return_value.get_id = 1234
    camera.return_value.get_type = "NVR"
    camera.return_value.current_event_states = {
        "test sensor": [
            [
                False,  # Sensor State
                1,  # Channel Number (for NVRs)
                0,
                datetime(2024, 9, 15, 17, 28, 24, 938074),  # Last update time
            ]
        ]
    }

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    sensor_entity_id = "binary_sensor.fake_name_test_sensor_1"
    entity_registry_entry = hass.data["entity_registry"].entities.data[sensor_entity_id]

    _, args, _ = camera.return_value.add_update_callback.mock_calls[0]
    assert args[1] == entity_registry_entry.unique_id
