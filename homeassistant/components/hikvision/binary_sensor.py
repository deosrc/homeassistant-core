"""Support for Hikvision event stream events represented as binary sensors."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LAST_TRIP_TIME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import track_point_in_utc_time
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util.dt import utcnow

from . import HikvisionData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_DELAY = "delay"

DEVICE_CLASS_MAP: Mapping[str, BinarySensorDeviceClass | None] = {
    "Motion": BinarySensorDeviceClass.MOTION,
    "Line Crossing": BinarySensorDeviceClass.MOTION,
    "Field Detection": BinarySensorDeviceClass.MOTION,
    "Tamper Detection": BinarySensorDeviceClass.MOTION,
    "Shelter Alarm": None,
    "Disk Full": None,
    "Disk Error": None,
    "Net Interface Broken": BinarySensorDeviceClass.CONNECTIVITY,
    "IP Conflict": BinarySensorDeviceClass.CONNECTIVITY,
    "Illegal Access": None,
    "Video Mismatch": None,
    "Bad Video": None,
    "PIR Alarm": BinarySensorDeviceClass.MOTION,
    "Face Detection": BinarySensorDeviceClass.MOTION,
    "Scene Change Detection": BinarySensorDeviceClass.MOTION,
    "I/O": None,
    "Unattended Baggage": BinarySensorDeviceClass.MOTION,
    "Attended Baggage": BinarySensorDeviceClass.MOTION,
    "Recording Failure": None,
    "Exiting Region": BinarySensorDeviceClass.MOTION,
    "Entering Region": BinarySensorDeviceClass.MOTION,
}

PYHIKVISION_HA_SENSOR_TYPE_MAP: Mapping[str, str] = {
    "Motion": "motion",
    "Line Crossing": "line_crossing",
    "Field Detection": "field_detection",
    "Tamper Detection": "tamper_detection",
    "Shelter Alarm": "shelter_alarm",
    "Disk Full": "disk_full",
    "Disk Error": "disk_error",
    "Net Interface Broken": "net_interface_broken",
    "IP Conflict": "ip_conflict",
    "Illegal Access": "illegal_access",
    "Video Mismatch": "video_mismatch",
    "Bad Video": "bad_video",
    "PIR Alarm": "pir_alarm",
    "Face Detection": "face_detection",
    "Scene Change Detection": "scene_change_detection",
    "I/O": "io",
    "Unattended Baggage": "unattended_baggage",
    "Attended Baggage": "attended_baggage",
    "Recording Failure": "recording_failure",
    "Exiting Region": "exiting_region",
    "Entering Region": "entering_region",
}


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import legacy yaml config."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=config,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hikvision binary sensor devices."""
    data: HikvisionData = config_entry.runtime_data
    if data.sensors is None:
        _LOGGER.error("Hikvision event stream has no data, unable to set up")
        return

    entities = []

    for sensor, channel_list in data.sensors.items():
        # Determine delay
        sensor_type = PYHIKVISION_HA_SENSOR_TYPE_MAP.get(sensor, sensor)
        delay_options_key = f"delay.{sensor_type}"
        delay = config_entry.options.get(delay_options_key, 0)

        for channel in channel_list:
            # Build sensor name, then parse customize config.
            if data.type == "NVR":
                sensor_name = f"{sensor.replace(' ', '_')}_{channel[1]}"
            else:
                sensor_name = sensor.replace(" ", "_")

            _LOGGER.debug(
                "Entity: %s - %s, Options - Delay: %s",
                data.name,
                sensor_name,
                delay,
            )
            entities.append(
                HikvisionBinarySensor(hass, sensor, channel[1], data, delay)
            )

    async_add_entities(entities)


class HikvisionBinarySensor(BinarySensorEntity):
    """Representation of a Hikvision binary sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        sensor: str,
        channel: int,
        cam: HikvisionData,
        delay: int | None,
    ) -> None:
        """Initialize the binary_sensor."""
        self._hass = hass
        self._cam = cam
        self._sensor = sensor
        self._channel = channel

        if self._cam.type == "NVR":
            self._name = f"{self._cam.name} {sensor} {channel}"
        else:
            self._name = f"{self._cam.name} {sensor}"

        self._id = f"{self._cam.cam_id}.{sensor}.{channel}"

        if delay is None:
            self._delay = 0
        else:
            self._delay = delay

        self._timer = None

        # Register callback function with pyHik
        self._cam.camdata.add_update_callback(self._update_callback, self._id)

    def _sensor_state(self):
        """Extract sensor state."""
        return self._cam.get_attributes(self._sensor, self._channel)[0]

    def _sensor_last_update(self):
        """Extract sensor last update time."""
        return self._cam.get_attributes(self._sensor, self._channel)[3]

    @property
    def name(self) -> str:
        """Return the name of the Hikvision sensor."""
        return self._name

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._id

    @property
    def is_on(self) -> bool:
        """Return true if sensor is on."""
        return self._sensor_state()

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of this sensor, from DEVICE_CLASSES."""
        try:
            return DEVICE_CLASS_MAP[self._sensor]
        except KeyError:
            # Sensor must be unknown to us, add as generic
            return None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes."""
        attr = {ATTR_LAST_TRIP_TIME: self._sensor_last_update()}

        if self._delay != 0:
            attr[ATTR_DELAY] = self._delay

        return attr

    def _update_callback(self, msg):
        """Update the sensor's state, if needed."""
        _LOGGER.debug("Callback signal from: %s", msg)

        if self._delay > 0 and not self.is_on:
            # Set timer to wait until updating the state
            def _delay_update(now):
                """Timer callback for sensor update."""
                _LOGGER.debug(
                    "%s Called delayed (%ssec) update", self._name, self._delay
                )
                self.schedule_update_ha_state()
                self._timer = None

            if self._timer is not None:
                self._timer()
                self._timer = None

            self._timer = track_point_in_utc_time(
                self._hass, _delay_update, utcnow() + timedelta(seconds=self._delay)
            )

        elif self._delay > 0 and self.is_on:
            # For delayed sensors kill any callbacks on true events and update
            if self._timer is not None:
                self._timer()
                self._timer = None

            self.schedule_update_ha_state()

        else:
            self.schedule_update_ha_state()
