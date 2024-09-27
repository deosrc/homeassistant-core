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
        "Line Crossing": [
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
        sensor_entity_id = "binary_sensor.fake_name_line_crossing_1"
        sensor_name = "fake_name Line Crossing 1"
    else:
        sensor_entity_id = "binary_sensor.fake_name_line_crossing"
        sensor_name = "fake_name Line Crossing"

    entity_registry_entry = hass.data["entity_registry"].entities.data[sensor_entity_id]

    assert hass.states.get(sensor_entity_id) is not None
    assert entity_registry_entry.original_name == sensor_name
    assert entity_registry_entry.unique_id == "1234.Line Crossing.1"


async def test_callback_registered(
    hass: HomeAssistant, config_entry: MockConfigEntry, camera: MagicMock
) -> None:
    """Test callback is registered when sensor is created."""
    camera.return_value.get_id = 1234
    camera.return_value.get_type = "NVR"
    camera.return_value.current_event_states = {
        "Line Crossing": [
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

    sensor_entity_id = "binary_sensor.fake_name_line_crossing_1"
    entity_registry_entry = hass.data["entity_registry"].entities.data[sensor_entity_id]

    _, args, _ = camera.return_value.add_update_callback.mock_calls[0]
    assert args[1] == entity_registry_entry.unique_id


@pytest.mark.parametrize(
    ("raw_value", "expected_state"), [(True, "on"), (False, "off")]
)
async def test_sensor_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    camera: MagicMock,
    raw_value: bool,
    expected_state: str,
) -> None:
    """Test sensor value."""
    camera.return_value.get_id = 1234
    camera.return_value.get_type = "NVR"
    camera.return_value.fetch_attributes.return_value = [
        raw_value,  # Sensor State
        1,  # Channel Number (for NVRs)
        0,
        datetime(2024, 9, 15, 17, 28, 24, 938074),  # Last update time
    ]
    camera.return_value.current_event_states = {
        "Line Crossing": [camera.return_value.fetch_attributes.return_value]
    }

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.fake_name_line_crossing_1").state
    assert state == expected_state


async def test_sensor_delay(
    hass: HomeAssistant, config_entry_with_options: MockConfigEntry, camera: MagicMock
) -> None:
    """Test a sensor configured with a delay."""
    camera.return_value.get_id = 1234
    camera.return_value.get_type = "NVR"
    camera.return_value.fetch_attributes.return_value = [
        False,  # Sensor State
        1,  # Channel Number (for NVRs)
        0,
        datetime(2024, 9, 15, 17, 28, 24, 938074),  # Last update time
    ]
    camera.return_value.current_event_states = {
        "Line Crossing": [camera.return_value.fetch_attributes.return_value]
    }

    config_entry_with_options.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry_with_options.entry_id)
    await hass.async_block_till_done()

    # Check delay attribute
    sensor_state = hass.states.get("binary_sensor.fake_name_line_crossing_1")
    assert sensor_state.attributes.get("delay") == 12
