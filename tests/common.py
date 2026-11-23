"""Test data and helpers for the comma.ai tests."""

from __future__ import annotations

from typing import Any

from custom_components.comma_ai.const import (
    CONF_IGNORE_NON_OWNED,
    CONF_JWT_TOKEN,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

API = "https://api.commadotai.com"
ATHENA = "https://athena.comma.ai"
DONGLE_ID = "abc123def4567890"
OTHER_DONGLE_ID = "0000000000000000"

PROFILE = {"id": "user-1", "username": "tester", "email": "tester@example.com"}

DEVICE = {
    "dongle_id": DONGLE_ID,
    "alias": "Test Device",
    "device_type": "three",
    "is_owner": True,
    "is_paired": True,
    "prime": False,
    "last_athena_ping": 1700000000,
    "openpilot_version": "0.9.8",
}

LOCATION = {"lat": 40.0, "lng": -86.0, "time": 1700000000000}

# comma's stats API reports distance in miles
STATS = {
    "all": {"distance": 100.0, "minutes": 73740, "routes": 50},
    "week": {"distance": 10.0, "minutes": 120, "routes": 5},
}

ROUTES = [
    {
        "create_time": 100,
        "git_branch": "old-branch",
        "git_commit": "ffffffffffffffffffffffffffffffffffffffff",
        "git_commit_date": "2020-01-01",
        "git_remote": "github.com/old/openpilot",
        "git_dirty": True,
        "platform": "OLD_CAR",
    },
    {
        "create_time": 200,
        "git_branch": "dev",
        "git_commit": "0123456789abcdef0123456789abcdef01234567",
        "git_commit_date": "2026-01-02",
        "git_remote": "github.com/commaai/openpilot",
        "git_dirty": False,
        "platform": "RIVIAN_R1",
    },
]

ATHENA_RESULT = {
    "result": {
        "deviceState": {"started": True},
        "pandaStates": [{"voltage": 13400}],
        "modelManagerSP": {
            "activeBundle": {
                "displayName": "The Cool People's Model (October 03, 2025)",
                "internalName": "TCPM",
            },
        },
    }
}


def register_api(
    aioclient_mock: Any,
    *,
    profile: Any = PROFILE,
    profile_status: int = 200,
    devices: Any = None,
    devices_status: int = 200,
    athena: Any = ATHENA_RESULT,
    athena_status: int = 200,
    stats_status: int = 200,
    routes_status: int = 200,
) -> None:
    """Register the comma.ai endpoints on the aiohttp mock."""
    aioclient_mock.get(f"{API}/v1/me/", json=profile, status=profile_status)
    aioclient_mock.get(
        f"{API}/v1/me/devices/",
        json=[DEVICE] if devices is None else devices,
        status=devices_status,
    )
    aioclient_mock.get(f"{API}/v1/devices/{DONGLE_ID}/location", json=LOCATION)
    aioclient_mock.get(
        f"{API}/v1.1/devices/{DONGLE_ID}/stats", json=STATS, status=stats_status
    )
    aioclient_mock.get(
        f"{API}/v1/devices/{DONGLE_ID}/routes", json=ROUTES, status=routes_status
    )
    aioclient_mock.post(f"{ATHENA}/{DONGLE_ID}", json=athena, status=athena_status)


def make_entry(**data: Any) -> MockConfigEntry:
    """Create a config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="tester",
        title="comma.ai (tester)",
        data={CONF_JWT_TOKEN: "token", CONF_IGNORE_NON_OWNED: False, **data},
    )
