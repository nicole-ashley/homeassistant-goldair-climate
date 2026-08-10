"""
Platform to control the LED display light on Goldair WiFi-connected dehumidifiers.
"""

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import ATTR_HVAC_MODE
from homeassistant.components.light import ColorMode, LightEntity

from ..device import GoldairTuyaDevice
from .const import ATTR_DISPLAY_ON, HVAC_MODE_TO_DPS_MODE, PROPERTY_TO_DPS_ID


class GoldairDehumidifierLedDisplayLight(LightEntity):
    """Representation of a Goldair WiFi-connected dehumidifier LED display."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, device):
        """Initialize the light.
        Args:
            device (GoldairTuyaDevice): The device API instance."""
        self._device = device

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def name(self):
        """Return the name of the light."""
        return self._device.name

    @property
    def unique_id(self):
        """Return the unique id for this dehumidifier LED display."""
        return self._device.unique_id

    @property
    def device_info(self):
        """Return device information about this dehumidifier LED display."""
        return self._device.device_info

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        if self.is_on:
            return "mdi:led-on"
        else:
            return "mdi:led-off"

    @property
    def is_on(self):
        """Return the current state."""
        return self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_DISPLAY_ON])

    async def async_turn_on(self, **kwargs):
        await self._device.async_set_property(PROPERTY_TO_DPS_ID[ATTR_DISPLAY_ON], True)

    async def async_turn_off(self, **kwargs):
        await self._device.async_set_property(
            PROPERTY_TO_DPS_ID[ATTR_DISPLAY_ON], False
        )

    async def async_toggle(self, **kwargs):
        dps_hvac_mode = self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE])
        dps_display_on = self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_DISPLAY_ON])

        if dps_hvac_mode != HVAC_MODE_TO_DPS_MODE[HVACMode.OFF]:
            await (
                self.async_turn_on() if not dps_display_on else self.async_turn_off()
            )

    async def async_update(self):
        await self._device.async_refresh()
