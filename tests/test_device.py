import threading
from datetime import datetime, timedelta
from time import sleep, time
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call, patch

from homeassistant.const import UnitOfTemperature

from custom_components.goldair_climate.const import (
    API_PROTOCOL_VERSIONS,
    CONF_TYPE_DEHUMIDIFIER,
    CONF_TYPE_FAN,
    CONF_TYPE_GECO_HEATER,
    CONF_TYPE_GPCV_HEATER,
    CONF_TYPE_GPPH_HEATER,
)
from custom_components.goldair_climate.device import GoldairTuyaDevice

from .const import (
    DEHUMIDIFIER_PAYLOAD,
    FAN_PAYLOAD,
    GECO_HEATER_PAYLOAD,
    GPCV_HEATER_PAYLOAD,
    GPPH_HEATER_PAYLOAD,
)


class TestDevice(IsolatedAsyncioTestCase):
    def setUp(self):
        device_patcher = patch("tinytuya.Device")
        self.addCleanup(device_patcher.stop)
        self.mock_api = device_patcher.start()

        hass_patcher = patch("homeassistant.core.HomeAssistant")
        self.addCleanup(hass_patcher.stop)
        self.hass = hass_patcher.start()

        self.subject = GoldairTuyaDevice(
            "Some name", "some_dev_id", "some.ip.address", "some_local_key", self.hass()
        )

    def test_configures_tinytuya_correctly(self):
        self.mock_api.assert_called_once_with(
            "some_dev_id", "some.ip.address", "some_local_key"
        )
        self.assertIs(self.subject._api, self.mock_api())

    def test_name(self):
        """Returns the name given at instantiation."""
        self.assertEqual(self.subject.name, "Some name")

    def test_unique_id(self):
        """Returns the unique ID presented by the API class."""
        self.assertIs(self.subject.unique_id, self.mock_api().id)

    def test_device_info(self):
        """Returns generic info plus the unique ID for categorisation."""
        self.assertEqual(
            self.subject.device_info,
            {
                "identifiers": {("goldair_climate", self.mock_api().id)},
                "name": "Some name",
                "manufacturer": "Goldair",
            },
        )

    def test_temperature_unit(self):
        self.assertEqual(self.subject.temperature_unit, UnitOfTemperature.CELSIUS)

    async def test_refreshes_state_if_no_cached_state_exists(self):
        self.subject._cached_state = {}
        self.subject.async_refresh = AsyncMock()

        await self.subject.async_inferred_type()

        self.subject.async_refresh.assert_awaited()

    async def test_detects_geco_heater_payload(self):
        self.subject._cached_state = GECO_HEATER_PAYLOAD
        self.assertEqual(
            await self.subject.async_inferred_type(), CONF_TYPE_GECO_HEATER
        )

    async def test_detects_gpcv_heater_payload(self):
        self.subject._cached_state = GPCV_HEATER_PAYLOAD
        self.assertEqual(
            await self.subject.async_inferred_type(), CONF_TYPE_GPCV_HEATER
        )

    async def test_detects_gpph_heater_payload(self):
        self.subject._cached_state = GPPH_HEATER_PAYLOAD
        self.assertEqual(
            await self.subject.async_inferred_type(), CONF_TYPE_GPPH_HEATER
        )

    async def test_detects_dehumidifier_payload(self):
        self.subject._cached_state = DEHUMIDIFIER_PAYLOAD
        self.assertEqual(
            await self.subject.async_inferred_type(), CONF_TYPE_DEHUMIDIFIER
        )

    async def test_detects_fan_payload(self):
        self.subject._cached_state = FAN_PAYLOAD
        self.assertEqual(await self.subject.async_inferred_type(), CONF_TYPE_FAN)

    async def test_detection_returns_none_when_device_type_could_not_be_detected(self):
        self.subject._cached_state = {"1": False}
        self.assertEqual(await self.subject.async_inferred_type(), None)

    async def test_does_not_refresh_more_often_than_cache_timeout(self):
        refresh_task = AsyncMock()
        self.subject._cached_state = {"updated_at": time() - 19}
        self.subject._refresh_task = awaitable = refresh_task()

        await self.subject.async_refresh()

        refresh_task.assert_awaited()
        self.assertIs(self.subject._refresh_task, awaitable)

    async def test_refreshes_when_there_is_no_pending_reset(self):
        async_job = AsyncMock()
        self.subject._cached_state = {"updated_at": time() - 19}
        self.subject._hass.async_add_executor_job.return_value = awaitable = async_job()

        await self.subject.async_refresh()

        self.subject._hass.async_add_executor_job.assert_called_once_with(
            self.subject.refresh
        )
        self.assertIs(self.subject._refresh_task, awaitable)
        async_job.assert_awaited()

    async def test_refreshes_when_there_is_expired_pending_reset(self):
        async_job = AsyncMock()
        self.subject._cached_state = {"updated_at": time() - 20}
        self.subject._hass.async_add_executor_job.return_value = awaitable = async_job()
        self.subject._refresh_task = {}

        await self.subject.async_refresh()

        self.subject._hass.async_add_executor_job.assert_called_once_with(
            self.subject.refresh
        )
        self.assertIs(self.subject._refresh_task, awaitable)
        async_job.assert_awaited()

    def test_refresh_reloads_status_from_device(self):
        self.subject._api.status.return_value = {"dps": {"1": False}}
        self.subject._cached_state = {"1": True}

        self.subject.refresh()

        self.subject._api.status.assert_called_once()
        self.assertEqual(self.subject._cached_state["1"], False)
        self.assertTrue(
            time() - 1 <= self.subject._cached_state["updated_at"] <= time()
        )

    def test_refresh_retries_up_to_four_times(self):
        self.subject._api.status.side_effect = [
            Exception("Error"),
            Exception("Error"),
            Exception("Error"),
            {"dps": {"1": False}},
        ]

        self.subject.refresh()

        self.assertEqual(self.subject._api.status.call_count, 4)
        self.assertEqual(self.subject._cached_state["1"], False)

    def test_refresh_retries_when_device_reports_an_error(self):
        """tinytuya returns an "Err" payload rather than raising, so the device layer
        has to turn that into a failure itself or the retry never fires."""
        self.subject._api.status.side_effect = [
            {"Err": "905", "Error": "Network Error: Device Unreachable"},
            {"dps": {"1": False}},
        ]

        self.subject.refresh()

        self.assertEqual(self.subject._api.status.call_count, 2)
        self.assertEqual(self.subject._cached_state["1"], False)

    def test_refresh_retries_when_device_returns_an_empty_response(self):
        self.subject._api.status.side_effect = [None, {"dps": {"1": False}}]

        self.subject.refresh()

        self.assertEqual(self.subject._api.status.call_count, 2)
        self.assertEqual(self.subject._cached_state["1"], False)

    def test_refresh_retries_when_response_contains_no_state(self):
        self.subject._api.status.side_effect = [
            {"not_dps": True},
            {"dps": {"1": False}},
        ]

        self.subject.refresh()

        self.assertEqual(self.subject._api.status.call_count, 2)
        self.assertEqual(self.subject._cached_state["1"], False)

    def test_send_raises_when_device_reports_an_error(self):
        self.subject._api.set_multiple_values.return_value = {
            "Err": "914",
            "Error": "Invalid JSON Response from Device",
        }

        with self.assertRaises(ConnectionError):
            self.subject._send_properties({"1": True})

    def test_refresh_clears_cached_state_and_pending_updates_after_failing_four_times(
        self,
    ):
        self.subject._cached_state = {"1": True}
        self.subject._pending_updates = {"1": False}
        self.subject._api.status.side_effect = [
            Exception("Error"),
            Exception("Error"),
            Exception("Error"),
            Exception("Error"),
        ]

        self.subject.refresh()

        self.assertEqual(self.subject._api.status.call_count, 4)
        self.assertEqual(self.subject._cached_state, {"updated_at": 0})
        self.assertEqual(self.subject._pending_updates, {})

    def test_api_protocol_version_is_rotated_with_each_failure(self):
        self.subject._api.set_version.assert_called_once_with(API_PROTOCOL_VERSIONS[0])
        self.subject._api.set_version.reset_mock()

        self.subject._api.status.side_effect = [Exception("Error")] * 4
        self.subject.refresh()

        # Every failed attempt but the last rotates onto the next version, wrapping
        # around the end of the list.
        self.subject._api.set_version.assert_has_calls(
            [
                call(API_PROTOCOL_VERSIONS[(i + 1) % len(API_PROTOCOL_VERSIONS)])
                for i in range(3)
            ]
        )

    def test_api_protocol_version_is_stable_once_successful(self):
        self.subject._api.set_version.assert_called_once_with(API_PROTOCOL_VERSIONS[0])
        self.subject._api.set_version.reset_mock()

        self.subject._api.status.side_effect = [{"dps": {"1": False}}] + [
            Exception("Error")
        ] * 4

        self.subject.refresh()  # succeeds, pinning the working protocol version
        self.subject.refresh()  # fails four times, but must not rotate away from it

        self.subject._api.set_version.assert_not_called()

    def test_reset_cached_state_clears_cached_state_and_pending_updates(self):
        self.subject._cached_state = {"1": True, "updated_at": time()}
        self.subject._pending_updates = {"1": False}

        self.subject._reset_cached_state()

        self.assertEqual(self.subject._cached_state, {"updated_at": 0})
        self.assertEqual(self.subject._pending_updates, {})

    def test_get_property_returns_value_from_cached_state(self):
        self.subject._cached_state = {"1": True}
        self.assertEqual(self.subject.get_property("1"), True)

    def test_get_property_returns_pending_update_value(self):
        self.subject._pending_updates = {
            "1": {"value": False, "updated_at": time() - 9}
        }
        self.assertEqual(self.subject.get_property("1"), False)

    def test_pending_update_value_overrides_cached_value(self):
        self.subject._cached_state = {"1": True}
        self.subject._pending_updates = {
            "1": {"value": False, "updated_at": time() - 9}
        }

        self.assertEqual(self.subject.get_property("1"), False)

    def test_expired_pending_update_value_does_not_override_cached_value(self):
        self.subject._cached_state = {"1": True}
        self.subject._pending_updates = {
            "1": {"value": False, "updated_at": time() - 10}
        }

        self.assertEqual(self.subject.get_property("1"), True)

    def test_get_property_returns_none_when_value_does_not_exist(self):
        self.subject._cached_state = {"1": True}
        self.assertIs(self.subject.get_property("2"), None)

    async def test_async_set_property_schedules_job(self):
        async_job = AsyncMock()
        self.subject._hass.async_add_executor_job.return_value = awaitable = async_job()

        await self.subject.async_set_property("1", False)

        self.subject._hass.async_add_executor_job.assert_called_once_with(
            self.subject.set_property, "1", False
        )
        async_job.assert_awaited()

    def test_set_property_immediately_stores_new_value_to_pending_updates(self):
        self.subject.set_property("1", False)
        self.subject._cached_state = {"1": True}
        self.assertEqual(self.subject.get_property("1"), False)

    def test_debounces_multiple_set_calls_into_one_api_call(self):
        with patch("custom_components.goldair_climate.device.Timer") as mock:
            self.subject.set_property("1", True)
            mock.assert_called_once_with(1, self.subject._send_pending_updates)

            debounce = self.subject._debounce
            mock.reset_mock()

            self.subject.set_property("2", False)
            debounce.cancel.assert_called_once()
            mock.assert_called_once_with(1, self.subject._send_pending_updates)

            self.subject._send_pending_updates()
            self.subject._api.set_multiple_values.assert_called_once_with(
                {"1": True, "2": False}
            )

    def test_set_properties_takes_no_action_when_no_properties_are_provided(self):
        with patch("custom_components.goldair_climate.device.Timer") as mock:
            self.subject._set_properties({})
            mock.assert_not_called()

    def test_anticipate_property_value_updates_cached_state(self):
        self.subject._cached_state = {"1": True}
        self.subject.anticipate_property_value("1", False)
        self.assertEqual(self.subject._cached_state["1"], False)

    def test_get_key_for_value_returns_key_from_object_matching_value(self):
        obj = {"key1": "value1", "key2": "value2"}

        self.assertEqual(GoldairTuyaDevice.get_key_for_value(obj, "value1"), "key1")
        self.assertEqual(GoldairTuyaDevice.get_key_for_value(obj, "value2"), "key2")

    def test_get_key_for_value_returns_fallback_when_value_not_found(self):
        obj = {"key1": "value1", "key2": "value2"}
        self.assertEqual(
            GoldairTuyaDevice.get_key_for_value(obj, "value3", fallback="fb"), "fb"
        )
