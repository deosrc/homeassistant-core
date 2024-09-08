"""The hikvision component."""

from pyhik.hikvision import HikCamera

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

PLATFORMS = [Platform.BINARY_SENSOR]


class HikvisionData:
    """Hikvision device event stream object."""

    def __init__(
        self,
        host: str,
        port: int,
        is_https: bool,
        name: str | None,
        username: str,
        password: str,
    ) -> None:
        """Initialize the data object."""
        self._host = host
        self._port = port
        self._is_https = is_https
        self._name = name
        self._username = username
        self._password = password

        # Establish camera
        url = f"{'https' if is_https else 'http'}://{host}"
        self.camdata = HikCamera(url, self._port, self._username, self._password)

        if self._name is None:
            self._name = self.camdata.get_name

    def stop_hik(self) -> None:
        """Shutdown Hikvision subscriptions and subscription thread on exit."""
        self.camdata.disconnect()

    def start_hik(self) -> None:
        """Start Hikvision event stream thread."""
        self.camdata.start_stream()

    @property
    def sensors(self):
        """Return list of available sensors and their states."""
        return self.camdata.current_event_states

    @property
    def cam_id(self):
        """Return device id."""
        return self.camdata.get_id

    @property
    def name(self):
        """Return device name."""
        return self._name

    @property
    def type(self):
        """Return device type."""
        return self.camdata.get_type

    def get_attributes(self, sensor, channel):
        """Return attribute list for sensor/channel."""
        return self.camdata.fetch_attributes(sensor, channel)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Connect component."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    is_https: bool = entry.data[CONF_SSL]
    name: str | None = entry.data.get(CONF_NAME)
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]

    def create_connection(
        host: str,
        port: int,
        is_https: bool,
        name: str | None,
        username: str,
        password: str,
    ):
        return HikvisionData(
            host,
            port,
            is_https,
            name,
            username,
            password,
        )

    connection = await hass.async_add_executor_job(
        create_connection,
        host,
        port,
        is_https,
        name,
        username,
        password,
    )
    if not connection.name:
        raise ConfigEntryNotReady

    entry.runtime_data = connection
    connection.start_hik()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    connection: HikvisionData = entry.runtime_data
    connection.stop_hik()
    entry.runtime_data = None
    return True
