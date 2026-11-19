"""Tests for the comma.ai API client."""

from __future__ import annotations

import pytest
from custom_components.comma_ai.api import (
    CommaAPIClient,
    CommaAPIError,
    CommaAuthError,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .common import API, ATHENA, DONGLE_ID


@pytest.fixture
async def client(hass, aioclient_mock) -> CommaAPIClient:
    """Return an API client using Home Assistant's mocked session."""
    return CommaAPIClient("token", async_get_clientsession(hass))


async def test_request_sends_jwt_header(client, aioclient_mock) -> None:
    """Requests authenticate with the JWT header."""
    aioclient_mock.get(f"{API}/v1/me/", json={"id": "x"})

    assert await client.get_profile() == {"id": "x"}
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == "JWT token"


async def test_401_raises_auth_error(client, aioclient_mock) -> None:
    """A 401 is reported as an auth error so reauth can start."""
    aioclient_mock.get(f"{API}/v1/me/", status=401)

    with pytest.raises(CommaAuthError):
        await client.get_profile()


@pytest.mark.parametrize("status", [403, 404, 500])
async def test_other_errors_raise_api_error(client, aioclient_mock, status) -> None:
    """Other error statuses raise a plain API error, not an auth error."""
    aioclient_mock.get(f"{API}/v1/me/", status=status)

    with pytest.raises(CommaAPIError) as err:
        await client.get_profile()
    assert not isinstance(err.value, CommaAuthError)


async def test_auth_error_is_an_api_error() -> None:
    """Callers that catch API errors also see auth errors."""
    assert issubclass(CommaAuthError, CommaAPIError)


async def test_athena_returns_requested_service(client, aioclient_mock) -> None:
    """The athena result is looked up by service name."""
    aioclient_mock.post(
        f"{ATHENA}/{DONGLE_ID}",
        json={"result": {"deviceState": {"started": True}}},
    )

    assert await client.get_athena_message(DONGLE_ID, "deviceState") == {
        "started": True
    }
    assert await client.get_athena_message(DONGLE_ID, "pandaStates") is None


async def test_athena_unreachable_device_returns_none(client, aioclient_mock) -> None:
    """An offline device (error status or empty result) yields None."""
    aioclient_mock.post(f"{ATHENA}/{DONGLE_ID}", status=500)
    assert await client.get_athena_message(DONGLE_ID, "deviceState") is None

    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{ATHENA}/{DONGLE_ID}", json={"error": "timeout"})
    assert await client.get_athena_message(DONGLE_ID, "deviceState") is None


async def test_athena_401_raises_auth_error(client, aioclient_mock) -> None:
    """An expired token is not hidden by the offline-device handling."""
    aioclient_mock.post(f"{ATHENA}/{DONGLE_ID}", status=401)

    with pytest.raises(CommaAuthError):
        await client.get_athena_message(DONGLE_ID, "deviceState")
