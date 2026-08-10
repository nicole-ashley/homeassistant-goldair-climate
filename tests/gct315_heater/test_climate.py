from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    SWING_HORIZONTAL,
    SWING_OFF,
)
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.goldair_climate.gct315_heater.climate import GoldairGCT315Heater
from custom_components.goldair_climate.gct315_heater.const import (
    ATTR_POWER_MODE,
    ATTR_POWER_MODE_AUTO,
    ATTR_POWER_MODE_USER,
    ATTR_TARGET_TEMPERATURE,
    ATTR_TIMER,
    PRESET_AUTO,
    PRESET_FAN,
    PRESET_HIGH,
    PRESET_LOW,
    PRESET_MODE_TO_DPS_LEVEL,
    PROPERTY_TO_DPS_ID,
)

from ..const import GCT315_HEATER_PAYLOAD
from ..helpers import assert_device_properties_set


class TestGoldairGCT315Heater(IsolatedAsyncioTestCase):
    def setUp(self):
        device_patcher = patch(
            "custom_components.goldair_climate.device.GoldairTuyaDevice"
        )
        self.addCleanup(device_patcher.stop)
        self.mock_device = device_patcher.start()

        self.subject = GoldairGCT315Heater(self.mock_device())

        self.dps = GCT315_HEATER_PAYLOAD.copy()
        self.subject._device.get_property.side_effect = lambda id: self.dps[id]

    def test_supported_features(self):
        self.assertEqual(
            self.subject.supported_features,
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.SWING_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF,
        )

    def test_should_poll(self):
        self.assertTrue(self.subject.should_poll)

    def test_name_returns_device_name(self):
        self.assertEqual(self.subject.name, self.subject._device.name)

    def test_unique_id_returns_device_unique_id(self):
        self.assertEqual(self.subject.unique_id, self.subject._device.unique_id)

    def test_device_info_returns_device_info_from_device(self):
        self.assertEqual(self.subject.device_info, self.subject._device.device_info)

    def test_icon(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = True
        self.dps[PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]] = ATTR_POWER_MODE_USER
        self.dps[PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]] = PRESET_MODE_TO_DPS_LEVEL[
            PRESET_HIGH
        ]
        self.assertEqual(self.subject.icon, "mdi:radiator")

        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = False
        self.assertEqual(self.subject.icon, "mdi:radiator-disabled")

    def test_icon_is_disabled_when_running_the_fan_without_heat(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = True
        self.dps[PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]] = ATTR_POWER_MODE_USER
        self.dps[PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]] = PRESET_MODE_TO_DPS_LEVEL[
            PRESET_FAN
        ]
        self.assertEqual(self.subject.icon, "mdi:radiator-disabled")

    def test_temperature_unit_returns_device_temperature_unit(self):
        self.assertEqual(
            self.subject.temperature_unit, self.subject._device.temperature_unit
        )

    def test_target_temperature(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_TARGET_TEMPERATURE]] = 25
        self.assertEqual(self.subject.target_temperature, 25)

    def test_target_temperature_step(self):
        self.assertEqual(self.subject.target_temperature_step, 1)

    def test_minimum_target_temperature(self):
        self.assertEqual(self.subject.min_temp, 15)

    def test_maximum_target_temperature(self):
        self.assertEqual(self.subject.max_temp, 45)

    async def test_legacy_set_temperature_with_temperature(self):
        async with assert_device_properties_set(
            self.subject._device, {PROPERTY_TO_DPS_ID[ATTR_TARGET_TEMPERATURE]: 25}
        ):
            await self.subject.async_set_temperature(temperature=25)

    async def test_legacy_set_temperature_with_preset_mode(self):
        async with assert_device_properties_set(
            self.subject._device,
            {
                PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]: ATTR_POWER_MODE_USER,
                PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]: PRESET_MODE_TO_DPS_LEVEL[
                    PRESET_LOW
                ],
            },
        ):
            await self.subject.async_set_temperature(preset_mode=PRESET_LOW)

    async def test_legacy_set_temperature_with_no_valid_properties(self):
        await self.subject.async_set_temperature(something="else")
        self.subject._device.async_set_property.assert_not_called

    async def test_set_target_temperature_succeeds_within_valid_range(self):
        async with assert_device_properties_set(
            self.subject._device, {PROPERTY_TO_DPS_ID[ATTR_TARGET_TEMPERATURE]: 40}
        ):
            await self.subject.async_set_target_temperature(40)

    async def test_set_target_temperature_rounds_value_to_closest_integer(self):
        async with assert_device_properties_set(
            self.subject._device,
            {PROPERTY_TO_DPS_ID[ATTR_TARGET_TEMPERATURE]: 25},
        ):
            await self.subject.async_set_target_temperature(24.6)

    async def test_set_target_temperature_fails_outside_valid_range(self):
        with self.assertRaisesRegex(
            ValueError, "Target temperature \\(14\\) must be between 15 and 45"
        ):
            await self.subject.async_set_target_temperature(14)

        with self.assertRaisesRegex(
            ValueError, "Target temperature \\(46\\) must be between 15 and 45"
        ):
            await self.subject.async_set_target_temperature(46)

    def test_current_temperature(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_TEMPERATURE]] = 19
        self.assertEqual(self.subject.current_temperature, 19)

    def test_hvac_mode(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = True
        self.assertEqual(self.subject.hvac_mode, HVACMode.HEAT)

        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = False
        self.assertEqual(self.subject.hvac_mode, HVACMode.OFF)

        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = None
        self.assertIs(self.subject.hvac_mode, None)

    def test_availability(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = False
        self.assertTrue(self.subject.available)

        self.dps[PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]] = None
        self.assertFalse(self.subject.available)

    def test_hvac_modes(self):
        self.assertEqual(self.subject.hvac_modes, [HVACMode.OFF, HVACMode.HEAT])

    async def test_turn_on(self):
        async with assert_device_properties_set(
            self.subject._device, {PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]: True}
        ):
            await self.subject.async_set_hvac_mode(HVACMode.HEAT)

    async def test_turn_off(self):
        async with assert_device_properties_set(
            self.subject._device, {PROPERTY_TO_DPS_ID[ATTR_HVAC_MODE]: False}
        ):
            await self.subject.async_set_hvac_mode(HVACMode.OFF)

    def test_preset_mode_reports_user_selected_level(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]] = ATTR_POWER_MODE_USER

        for preset, level in PRESET_MODE_TO_DPS_LEVEL.items():
            self.dps[PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]] = level
            self.assertEqual(self.subject.preset_mode, preset)

        self.dps[PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]] = None
        self.assertIs(self.subject.preset_mode, None)

    def test_preset_mode_reports_auto_regardless_of_the_level_chosen(self):
        # In Auto the appliance drives dps 5 itself, so its value is not a
        # user selection and must not be reported as one.
        self.dps[PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]] = ATTR_POWER_MODE_AUTO

        for level in PRESET_MODE_TO_DPS_LEVEL.values():
            self.dps[PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]] = level
            self.assertEqual(self.subject.preset_mode, PRESET_AUTO)

    def test_preset_modes(self):
        self.assertEqual(
            self.subject.preset_modes,
            [PRESET_AUTO, PRESET_FAN, PRESET_LOW, PRESET_HIGH],
        )

    async def test_set_preset_mode_to_auto_only_sets_the_power_mode(self):
        async with assert_device_properties_set(
            self.subject._device,
            {PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]: ATTR_POWER_MODE_AUTO},
        ):
            await self.subject.async_set_preset_mode(PRESET_AUTO)

    async def test_set_preset_mode_to_fan_also_hands_back_user_control(self):
        async with assert_device_properties_set(
            self.subject._device,
            {
                PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]: ATTR_POWER_MODE_USER,
                PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]: PRESET_MODE_TO_DPS_LEVEL[
                    PRESET_FAN
                ],
            },
        ):
            await self.subject.async_set_preset_mode(PRESET_FAN)

    async def test_set_preset_mode_to_low_also_hands_back_user_control(self):
        async with assert_device_properties_set(
            self.subject._device,
            {
                PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]: ATTR_POWER_MODE_USER,
                PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]: PRESET_MODE_TO_DPS_LEVEL[
                    PRESET_LOW
                ],
            },
        ):
            await self.subject.async_set_preset_mode(PRESET_LOW)

    async def test_set_preset_mode_to_high_also_hands_back_user_control(self):
        async with assert_device_properties_set(
            self.subject._device,
            {
                PROPERTY_TO_DPS_ID[ATTR_POWER_MODE]: ATTR_POWER_MODE_USER,
                PROPERTY_TO_DPS_ID[ATTR_PRESET_MODE]: PRESET_MODE_TO_DPS_LEVEL[
                    PRESET_HIGH
                ],
            },
        ):
            await self.subject.async_set_preset_mode(PRESET_HIGH)

    async def test_set_preset_mode_fails_for_an_unknown_preset(self):
        with self.assertRaisesRegex(ValueError, "Invalid preset mode: Eco"):
            await self.subject.async_set_preset_mode("Eco")

    def test_swing_mode(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_SWING_MODE]] = True
        self.assertEqual(self.subject.swing_mode, SWING_HORIZONTAL)

        self.dps[PROPERTY_TO_DPS_ID[ATTR_SWING_MODE]] = False
        self.assertEqual(self.subject.swing_mode, SWING_OFF)

        self.dps[PROPERTY_TO_DPS_ID[ATTR_SWING_MODE]] = None
        self.assertIs(self.subject.swing_mode, None)

    def test_swing_modes(self):
        self.assertEqual(self.subject.swing_modes, [SWING_OFF, SWING_HORIZONTAL])

    async def test_set_swing_mode_on(self):
        async with assert_device_properties_set(
            self.subject._device, {PROPERTY_TO_DPS_ID[ATTR_SWING_MODE]: True}
        ):
            await self.subject.async_set_swing_mode(SWING_HORIZONTAL)

    async def test_set_swing_mode_off(self):
        async with assert_device_properties_set(
            self.subject._device, {PROPERTY_TO_DPS_ID[ATTR_SWING_MODE]: False}
        ):
            await self.subject.async_set_swing_mode(SWING_OFF)

    def test_extra_state_attributes_reports_the_countdown(self):
        self.dps[PROPERTY_TO_DPS_ID[ATTR_TIMER]] = "3h"
        self.assertEqual(self.subject.extra_state_attributes, {ATTR_TIMER: "3h"})

        self.dps[PROPERTY_TO_DPS_ID[ATTR_TIMER]] = "cancel"
        self.assertEqual(self.subject.extra_state_attributes, {ATTR_TIMER: "cancel"})

    async def test_update(self):
        result = AsyncMock()
        self.subject._device.async_refresh.return_value = result()

        await self.subject.async_update()

        self.subject._device.async_refresh.assert_called_once()
        result.assert_awaited()
