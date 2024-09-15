"""Constants for Hikvision tests."""

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)

FAKE_CONFIG = {
    CONF_NAME: "fake_name",
    CONF_HOST: "fake_host",
    CONF_PORT: 1234,
    CONF_SSL: False,
    CONF_USERNAME: "fake_user",
    CONF_PASSWORD: "fake_password",
}
