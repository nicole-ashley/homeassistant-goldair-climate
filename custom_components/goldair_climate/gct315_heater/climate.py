"""
Goldair GCT315 WiFi ceramic tower heater device.
"""

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
)
from homeassistant.const import ATTR_TEMPERATURE

from ..device import GoldairTuyaDevice
from .const import (
    ATTR_POWER_MODE,
    ATTR_POWER_MODE_AUTO,
    ATTR_POWER_MODE_USER,
    ATTR_TARGET_TEMPERATURE,
    ATTR_TIMER,
    HVAC_MODE_TO_DPS_MODE,
    PRESET_AUTO,
    PRESET_FAN,
    PRESET_MODE_TO_DPS_LEVEL,
    PROPERTY_TO_DPS_ID,
    SWING_MODE_TO_DPS_MODE,
)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.SWING_MODE
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
)


class GoldairGCT315Heater(ClimateEntity):
    """Representation of a Goldair GCT315 WiFi ceramic tower heater."""

    def __init__(self, device):
        """Initialize the heater.
        Args:
            device (GoldairTuyaDevice): The device API instance."""
        self._device = device

        self._support_flags = SUPPORT_FLAGS

        self._TEMPERATURE_STEP = 1
        self._TEMPERATURE_LIMITS = {"min": 15, "max": 45}

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._device.name

    @property
    def unique_id(self):
        """Return the unique id for this heater."""
        return self._device.unique_id

    @property
    def device_info(self):
        """Return device information about this heater."""
        return self._device.device_info

    @property
    def icon(self):
        """Return the icon to use in the frontend for this device."""
        if self.hvac_mode == HVACMode.HEAT and self.preset_mode != PRESET_FAN:
            return "mdi:radiator"
        else:
            return "mdi:radiator-disabled"

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._device.temperature_unit

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_TARGET_TEMPERATURE])

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._TEMPERATURE_STEP

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._TEMPERATURE_LIMITS["min"]

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._TEMPERATURE_LIMITS["max"]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if kwargs.get(ATTR_PRESET_MODE) is not None:
            await self.async_set_preset_mode(kwargs.get(ATTR_PRESET_MODE))
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            await self.async_set_target_temperature(kwargs.get(ATTR_TEMPERATURE))

    async def async_set_target_temperature(self, target_temperature):
        target_temperature = int(round(target_temperature))

        limits = self._TEMPERATURE_LIMITS
        if not limits["min"] <= target_temperature <= limits["max"]:
            raise ValueError(
                f"Target temperature ({target_temperature}) must be between "
                f'{limits["min"]} and {limits["max"]}.'
            )

        await self._device.async_set_property(
            PROPERTY_TO_DPS_ID[ATTR_TARGET_TEMPERATURE], target_temperature
        )

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_TEMPERATURE])

    @property
    def available(self):
        """Return whether the device is currently reachable."""
        return self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]) is not None

    @property
    def hvac_mode(self):
        """Return current HVAC mode, ie Heat or Off."""
        dps_mode = self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE])

        if dps_mode is not None:
            return GoldairTuyaDevice.get_key_for_value(HVAC_MODE_TO_DPS_MODE, dps_mode)
        else:
            return None

    @property
    def hvac_modes(self):
        """Return the list of available HVAC modes."""
        return list(HVAC_MODE_TO_DPS_MODE.keys())

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new HVAC mode."""
        dps_mode = HVAC_MODE_TO_DPS_MODE[hvac_mode]
        await self._device.async_set_property(
            PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE], dps_mode
        )

    async def async_turn_on(self):
        """Turn the heater on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn the heater off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    @property
    def preset_mode(self):
        """Return current preset mode, ie Auto, Fan, Low or High.

        Auto lives on its own dps: when the appliance is picking the heat level
        itself, whatever dps 5 currently holds is its choice rather than the
        user's, so it must not be reported as a Fan/Low/High selection.
        """
        power_mode = self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_POWER_MODE])
        if power_mode == ATTR_POWER_MODE_AUTO:
            return PRESET_AUTO

        dps_level = self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE])
        if dps_level is not None:
            return GoldairTuyaDevice.get_key_for_value(
                PRESET_MODE_TO_DPS_LEVEL, dps_level
            )
        else:
            return None

    @property
    def preset_modes(self):
        """Return the list of available preset modes."""
        return [PRESET_AUTO, *PRESET_MODE_TO_DPS_LEVEL.keys()]

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        if preset_mode == PRESET_AUTO:
            # dps 4 only. Sending a level in the same write drops the appliance
            # straight back to "normal", so Auto would never take effect.
            await self._device.async_set_property(
                PROPERTY_TO_DPS_ID[ATTR_POWER_MODE], ATTR_POWER_MODE_AUTO
            )
            return

        if preset_mode not in PRESET_MODE_TO_DPS_LEVEL:
            raise ValueError(f"Invalid preset mode: {preset_mode}")

        # Writing a level makes the appliance hand control back on its own, but
        # set dps 4 explicitly so the intent is recorded rather than implied.
        await self._device.async_set_property(
            PROPERTY_TO_DPS_ID[ATTR_POWER_MODE], ATTR_POWER_MODE_USER
        )
        await self._device.async_set_property(
            PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE],
            PRESET_MODE_TO_DPS_LEVEL[preset_mode],
        )

    @property
    def swing_mode(self):
        """Return current swing mode: horizontal or off."""
        dps_mode = self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_SWING_MODE])
        if dps_mode is not None:
            return GoldairTuyaDevice.get_key_for_value(SWING_MODE_TO_DPS_MODE, dps_mode)
        else:
            return None

    @property
    def swing_modes(self):
        """Return the list of available swing modes."""
        return list(SWING_MODE_TO_DPS_MODE.keys())

    async def async_set_swing_mode(self, swing_mode):
        """Set new swing mode."""
        dps_mode = SWING_MODE_TO_DPS_MODE[swing_mode]
        await self._device.async_set_property(
            PROPERTY_TO_DPS_ID[ATTR_SWING_MODE], dps_mode
        )

    @property
    def extra_state_attributes(self):
        """Get additional attributes that HA doesn't naturally support.

        The appliance's auto-off countdown, as "cancel" or "1h" through "12h".
        """
        timer = self._device.get_property(PROPERTY_TO_DPS_ID[ATTR_TIMER])

        return {ATTR_TIMER: timer}

    async def async_update(self):
        await self._device.async_refresh()
