"""
Platform for Goldair WiFi-connected heaters, dehumidifiers and fans.

Based on sean6541/tuya-homeassistant for service call logic, and TarxBoy's
investigation into Goldair's tuyapi statuses
https://github.com/codetheweb/tuyapi/issues/31.
"""

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform

from .configuration import individual_config_schema
from .const import (
    CONF_CHILD_LOCK,
    CONF_CLIMATE,
    CONF_DEVICE_ID,
    CONF_DISPLAY_LIGHT,
    CONF_LOCAL_KEY,
    CONF_TYPE,
    CONF_TYPE_AUTO,
    CONF_TYPE_DEHUMIDIFIER,
    CONF_TYPE_FAN,
    CONF_TYPE_GPPH_HEATER,
    DOMAIN,
    SCAN_INTERVAL,
)
from .device import GoldairTuyaDevice

_LOGGER = logging.getLogger(__name__)

VERSION = "0.2.0"

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [vol.Schema(individual_config_schema())])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    for device_config in config.get(DOMAIN, []):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=device_config
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.debug(f"Setting up entry for device: {entry.data[CONF_DEVICE_ID]}")
    config = {**entry.data, **entry.options, "name": entry.title}
    setup_device(hass, config)

    platforms = []
    if config[CONF_CLIMATE] == True:
        platforms.append("climate")
    if config[CONF_DISPLAY_LIGHT] == True:
        platforms.append("light")
    if config[CONF_CHILD_LOCK] == True:
        platforms.append("lock")

    if platforms:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)

    entry.add_update_listener(async_update_entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.data.get(SOURCE_IMPORT):
        raise ValueError("Devices configured via yaml cannot be deleted from the UI.")

    _LOGGER.debug(f"Unloading entry for device: {entry.data[CONF_DEVICE_ID]}")
    config = entry.data
    data = hass.data[DOMAIN][config[CONF_DEVICE_ID]]

    platforms = []
    if CONF_CLIMATE in data:
        platforms.append("climate")
    if CONF_DISPLAY_LIGHT in data:
        platforms.append("light")
    if CONF_CHILD_LOCK in data:
        platforms.append("lock")

    if platforms:
        await hass.config_entries.async_unload_platforms(entry, platforms)

    delete_device(hass, config)
    del hass.data[DOMAIN][config[CONF_DEVICE_ID]]

    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.data.get(SOURCE_IMPORT):
        raise ValueError("Devices configured via yaml cannot be updated from the UI.")

    _LOGGER.debug(f"Updating entry for device: {entry.data[CONF_DEVICE_ID]}")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


def setup_device(hass: HomeAssistant, config: dict):
    _LOGGER.debug(f"Creating device: {config[CONF_DEVICE_ID]}")
    hass.data[DOMAIN] = hass.data.get(DOMAIN, {})
    device = GoldairTuyaDevice(
        config[CONF_NAME],
        config[CONF_DEVICE_ID],
        config[CONF_HOST],
        config[CONF_LOCAL_KEY],
        hass,
    )
    hass.data[DOMAIN][config[CONF_DEVICE_ID]] = {"device": device}

    return device


def delete_device(hass: HomeAssistant, config: dict):
    _LOGGER.debug(f"Deleting device: {config[CONF_DEVICE_ID]}")
    del hass.data[DOMAIN][config[CONF_DEVICE_ID]]["device"]
