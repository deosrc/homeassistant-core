"""Support for Hikvision event stream events represented as binary sensors."""

from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LAST_TRIP_TIME, CONF_DELAY
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import track_point_in_utc_time
from homeassistant.util.dt import utcnow

from . import HikvisionData

_LOGGER = logging.getLogger(__name__)

CONF_IGNORED = "ignored"

DEFAULT_IGNORED = False
DEFAULT_DELAY = 0

ATTR_DELAY = "delay"

DEVICE_CLASS_MAP = {
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

CUSTOMIZE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_IGNORED, default=DEFAULT_IGNORED): cv.boolean,
        vol.Optional(CONF_DELAY, default=DEFAULT_DELAY): cv.positive_int,
    }
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
        for channel in channel_list:
            # Build sensor name, then parse customize config.
            if data.type == "NVR":
                sensor_name = f"{sensor.replace(' ', '_')}_{channel[1]}"
            else:
                sensor_name = sensor.replace(" ", "_")

            # custom = customize.get(sensor_name.lower(), {})
            # ignore = custom.get(CONF_IGNORED)
            # delay = custom.get(CONF_DELAY)
            ignore = None
            delay = None

            _LOGGER.debug(
                "Entity: %s - %s, Options - Ignore: %s, Delay: %s",
                data.name,
                sensor_name,
                ignore,
                delay,
            )
            if not ignore:
                entities.append(
                    HikvisionBinarySensor(hass, sensor, channel[1], data, delay)
                )

    async_add_entities(entities)


class HikvisionBinarySensor(BinarySensorEntity):
    """Representation of a Hikvision binary sensor."""

    _attr_should_poll = False

    def __init__(self, hass, sensor, channel, cam, delay):
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
    def name(self):
        """Return the name of the Hikvision sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._id

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._sensor_state()

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        try:
            return DEVICE_CLASS_MAP[self._sensor]
        except KeyError:
            # Sensor must be unknown to us, add as generic
            return None

    @property
    def extra_state_attributes(self):
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
