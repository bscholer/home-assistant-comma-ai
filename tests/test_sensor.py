"""Tests for the sensor, binary sensor and device tracker entities."""

from __future__ import annotations

import pytest
from custom_components.comma_ai.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .common import DONGLE_ID, make_entry, register_api


async def _setup(hass: HomeAssistant, aioclient_mock, **api) -> None:
    register_api(aioclient_mock, **api)
    entry = make_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _state(hass: HomeAssistant, platform: str, key: str):
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{DONGLE_ID}_{key}"
    )
    assert entity_id is not None, f"no {platform} entity for {key}"
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def test_software_build_sensors(hass: HomeAssistant, aioclient_mock) -> None:
    """Build sensors come from the newest route."""
    await _setup(hass, aioclient_mock)

    assert _state(hass, "sensor", "git_branch").state == "dev"
    assert _state(hass, "sensor", "git_remote").state == "github.com/commaai/openpilot"
    assert _state(hass, "sensor", "platform").state == "RIVIAN_R1"

    commit = _state(hass, "sensor", "git_commit")
    assert commit.state == "0123456"
    assert commit.attributes["commit"] == "0123456789abcdef0123456789abcdef01234567"
    assert commit.attributes["commit_date"] == "2026-01-02"
    assert commit.attributes["dirty"] is False


async def test_distance_is_converted_from_miles(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """The API reports miles; Home Assistant converts to the unit system."""
    await _setup(hass, aioclient_mock)

    total = _state(hass, "sensor", "total_distance")
    assert total.attributes["unit_of_measurement"] == "km"
    assert float(total.state) == pytest.approx(160.934, rel=1e-3)

    week = _state(hass, "sensor", "week_distance")
    assert float(week.state) == pytest.approx(16.0934, rel=1e-3)


async def test_drive_time_default_units(hass: HomeAssistant, aioclient_mock) -> None:
    """Total drive time shows days and weekly drive time shows hours."""
    await _setup(hass, aioclient_mock)

    total = _state(hass, "sensor", "total_minutes")
    assert total.attributes["unit_of_measurement"] == "d"
    assert float(total.state) == pytest.approx(73740 / 1440)

    week = _state(hass, "sensor", "week_minutes")
    assert week.attributes["unit_of_measurement"] == "h"
    assert float(week.state) == pytest.approx(2.0)


async def test_car_battery_and_running(hass: HomeAssistant, aioclient_mock) -> None:
    """Athena data becomes the voltage sensor and the running binary sensor."""
    await _setup(hass, aioclient_mock)

    assert float(_state(hass, "sensor", "car_battery_voltage").state) == pytest.approx(13.4)
    assert _state(hass, "binary_sensor", "car_running").state == "on"


async def test_driving_model(hass: HomeAssistant, aioclient_mock) -> None:
    """The active driving model from modelManagerSP becomes a sensor."""
    await _setup(hass, aioclient_mock)

    assert (
        _state(hass, "sensor", "driving_model").state
        == "The Cool People's Model (October 03, 2025)"
    )


async def test_driving_model_unknown_without_model_manager(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """Stock openpilot does not publish modelManagerSP, so the sensor is unknown."""
    await _setup(
        hass,
        aioclient_mock,
        athena={"result": {"deviceState": {"started": False}, "pandaStates": []}},
    )

    assert _state(hass, "sensor", "driving_model").state == "unknown"


async def test_car_stopped(hass: HomeAssistant, aioclient_mock) -> None:
    """A device reporting started=false is off, not unknown."""
    await _setup(
        hass,
        aioclient_mock,
        athena={"result": {"deviceState": {"started": False}, "pandaStates": []}},
    )

    assert _state(hass, "binary_sensor", "car_running").state == "off"
    assert _state(hass, "sensor", "car_battery_voltage").state == "unknown"


async def test_unreachable_device_is_unknown_not_off(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """If athena cannot reach the device we do not claim the car is off."""
    await _setup(hass, aioclient_mock, athena_status=500)

    assert _state(hass, "binary_sensor", "car_running").state == "unknown"
    assert _state(hass, "sensor", "car_battery_voltage").state == "unknown"


async def test_device_tracker_location(hass: HomeAssistant, aioclient_mock) -> None:
    """The device tracker reports the GPS position."""
    await _setup(hass, aioclient_mock)

    tracker = _state(hass, "device_tracker", "tracker")
    assert tracker.attributes["latitude"] == 40.0
    assert tracker.attributes["longitude"] == -86.0
    assert "battery_level" not in tracker.attributes
