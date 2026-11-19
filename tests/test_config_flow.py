"""Tests for the comma.ai config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from custom_components.comma_ai.const import (
    CONF_IGNORE_NON_OWNED,
    CONF_JWT_TOKEN,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .common import API, make_entry, register_api


@pytest.fixture(autouse=True)
def no_setup():
    """Do not set the integration up when a flow creates an entry."""
    with patch("custom_components.comma_ai.async_setup_entry", return_value=True):
        yield


async def _start(hass: HomeAssistant, token: str = "new-token"):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_JWT_TOKEN: token}
    )


async def test_user_flow_creates_entry(hass: HomeAssistant, aioclient_mock) -> None:
    """A valid token creates an entry titled with the username."""
    aioclient_mock.get(f"{API}/v1/me/", json={"id": "1", "username": "tester"})
    result = await _start(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "comma.ai (tester)"
    assert result["data"][CONF_JWT_TOKEN] == "new-token"
    assert result["data"][CONF_IGNORE_NON_OWNED] is False


@pytest.mark.parametrize(
    ("profile", "title"),
    [
        ({"id": "1", "username": None, "email": "g@example.com"}, "comma.ai (g@example.com)"),
        ({"id": "user-42", "username": None}, "comma.ai (user-42)"),
    ],
)
async def test_account_without_username(
    hass: HomeAssistant, aioclient_mock, profile, title
) -> None:
    """Accounts without a username (e.g. Google sign-in) fall back to email, then id."""
    aioclient_mock.get(f"{API}/v1/me/", json=profile)
    result = await _start(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == title


async def test_invalid_token(hass: HomeAssistant, aioclient_mock) -> None:
    """A rejected token shows an auth error and stays on the form."""
    aioclient_mock.get(f"{API}/v1/me/", status=401)
    result = await _start(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_duplicate_account_aborts(hass: HomeAssistant, aioclient_mock) -> None:
    """The same account cannot be added twice."""
    make_entry().add_to_hass(hass)
    aioclient_mock.get(f"{API}/v1/me/", json={"id": "1", "username": "tester"})
    result = await _start(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_token(hass: HomeAssistant, aioclient_mock) -> None:
    """Reauth replaces the stored token and reloads the entry."""
    register_api(aioclient_mock)
    entry = make_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"]["jwt_url"] == "https://jwt.comma.ai"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_JWT_TOKEN: "fresh-token"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_JWT_TOKEN] == "fresh-token"


async def test_reauth_with_bad_token_stays_on_form(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A bad token during reauth shows an error instead of finishing."""
    register_api(aioclient_mock, profile_status=401)
    entry = make_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_JWT_TOKEN: "still-bad"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data[CONF_JWT_TOKEN] == "token"
