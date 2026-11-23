"""Tests for setup, the coordinator, and reauth handling."""

from __future__ import annotations

from unittest.mock import patch

from custom_components.comma_ai.const import DOMAIN
from custom_components.comma_ai.coordinator import (
    CommaDataUpdateCoordinator,
    _get_active_model_display_name,
)
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import (
    API,
    DEVICE,
    DONGLE_ID,
    OTHER_DONGLE_ID,
    make_entry,
    register_api,
)


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{DONGLE_ID}_{key}"
    )
    assert entity_id is not None, f"no {platform} entity for {key}"
    return entity_id


def test_latest_route_picks_newest() -> None:
    """The most recently created route wins, whatever the order."""
    routes = [{"create_time": 5, "n": "b"}, {"create_time": 9, "n": "a"}, {"n": "c"}]
    assert CommaDataUpdateCoordinator._latest_route(routes)["n"] == "a"


def test_latest_route_without_routes() -> None:
    """No routes gives an empty dict so the git sensors are unknown."""
    assert CommaDataUpdateCoordinator._latest_route([]) == {}


def test_get_active_model_display_name() -> None:
    """The model name comes from modelManagerSP's active bundle."""
    assert _get_active_model_display_name(None) is None
    assert _get_active_model_display_name({}) is None
    assert _get_active_model_display_name({"activeBundle": {}}) is None
    assert (
        _get_active_model_display_name({"activeBundle": {"displayName": "Foo"}})
        == "Foo"
    )


async def test_setup_loads_entry(hass: HomeAssistant, aioclient_mock) -> None:
    """A valid token loads the entry and creates entities."""
    register_api(aioclient_mock)
    entry = make_entry()
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(_entity_id(hass, "device_tracker", "tracker"))


async def test_setup_with_expired_token_starts_reauth(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A 401 on setup asks the user to re-authenticate."""
    register_api(aioclient_mock, profile_status=401)
    entry = make_entry()
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = list(entry.async_get_active_flows(hass, {SOURCE_REAUTH}))
    assert len(flows) == 1


async def test_refresh_with_expired_token_starts_reauth(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A 401 during a later refresh starts reauth.

    The coordinator fetches in a TaskGroup, which wraps the error in an
    ExceptionGroup, so this guards the unwrapping.
    """
    register_api(aioclient_mock)
    entry = make_entry()
    await _setup(hass, entry)
    coordinator = entry.runtime_data.coordinator

    aioclient_mock.clear_requests()
    register_api(aioclient_mock, devices_status=401)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert list(entry.async_get_active_flows(hass, {SOURCE_REAUTH}))


async def test_refresh_with_api_outage_is_not_reauth(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A server error fails the update without asking for a new token."""
    register_api(aioclient_mock)
    entry = make_entry()
    await _setup(hass, entry)
    coordinator = entry.runtime_data.coordinator

    aioclient_mock.clear_requests()
    register_api(aioclient_mock, devices_status=500)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert not list(entry.async_get_active_flows(hass, {SOURCE_REAUTH}))


async def test_ignore_non_owned_filters_devices(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Devices the user does not own are dropped when configured."""
    other = {**DEVICE, "dongle_id": OTHER_DONGLE_ID, "is_owner": False}
    register_api(aioclient_mock, devices=[DEVICE, other])
    aioclient_mock.get(f"{API}/v1/devices/{OTHER_DONGLE_ID}/location", json={})
    aioclient_mock.get(f"{API}/v1.1/devices/{OTHER_DONGLE_ID}/stats", json={})
    aioclient_mock.get(f"{API}/v1/devices/{OTHER_DONGLE_ID}/routes", json=[])
    entry = make_entry(ignore_non_owned=True)
    await _setup(hass, entry)

    assert set(entry.runtime_data.coordinator.data["devices"]) == {DONGLE_ID}


async def test_missing_device_data_degrades_to_unknown(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Failed per-device calls leave sensors unknown instead of failing setup."""
    register_api(aioclient_mock, routes_status=403, stats_status=404)
    entry = make_entry()
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    state = hass.states.get(_entity_id(hass, "sensor", "git_branch"))
    assert state.state == "unknown"
    state = hass.states.get(_entity_id(hass, "sensor", "total_minutes"))
    assert state.state == "unknown"


async def test_athena_fetched_right_after_boot(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """The first poll reads athena even when the host booted moments ago.

    time.monotonic() can be small on a freshly booted host, which used to
    make the 5 minute throttle skip the very first athena fetch.
    """
    register_api(aioclient_mock)
    with patch("custom_components.comma_ai.coordinator.time.monotonic", return_value=10.0):
        entry = make_entry()
        await _setup(hass, entry)

    assert entry.runtime_data.coordinator.data["devices"][DONGLE_ID]["car_running"] is True


async def test_athena_throttled_between_polls(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Athena is not called again within the athena interval."""
    register_api(aioclient_mock)
    entry = make_entry()
    await _setup(hass, entry)

    def athena_calls() -> int:
        return sum(1 for call in aioclient_mock.mock_calls if call[0] == "POST")

    first = athena_calls()
    assert first > 0
    await entry.runtime_data.coordinator.async_refresh()
    assert athena_calls() == first


async def test_athena_offline_device_does_not_fail_update(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """An unreachable device only matters for the athena entities."""
    register_api(aioclient_mock, athena_status=500)
    entry = make_entry()
    await _setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    device = entry.runtime_data.coordinator.data["devices"][DONGLE_ID]
    assert device["car_running"] is None
    assert device["car_battery_voltage"] is None
