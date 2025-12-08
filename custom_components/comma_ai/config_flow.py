"""Config flow for comma.ai integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CommaAPIClient, CommaAPIError
from .const import CONF_IGNORE_NON_OWNED, CONF_JWT_TOKEN, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult

_LOGGER = logging.getLogger(__name__)

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_JWT_TOKEN): str,
        vol.Optional(CONF_IGNORE_NON_OWNED, default=False): bool,
    }
)


class CommaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for comma.ai."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self.errors = {}
        self.data = {}
        self.username = ""

    async def validate_config(self) -> None:
        """Validate the JWT token."""
        api_client = CommaAPIClient(
            jwt_token=self.data[CONF_JWT_TOKEN],
            session=async_get_clientsession(self.hass),
        )
        try:
            profile = await api_client.get_profile()
            self.username = profile.get("username", "Unknown")
            _LOGGER.debug("Successfully authenticated as: %s", self.username)
        except CommaAPIError as exc:
            _LOGGER.error("Authentication failed: %s", exc)
            self.errors = {"base": "invalid_auth"}
        except Exception as exc:
            _LOGGER.error("Unexpected error: %s", exc)
            self.errors = {"base": "cannot_connect"}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self.data[CONF_JWT_TOKEN] = user_input[CONF_JWT_TOKEN]
            self.data[CONF_IGNORE_NON_OWNED] = user_input.get(CONF_IGNORE_NON_OWNED, False)
            await self.validate_config()
            
            if not self.errors:
                # Check if already configured
                await self.async_set_unique_id(self.username)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"comma.ai ({self.username})",
                    data=self.data,
                )
        
        schema = self.add_suggested_values_to_schema(USER_DATA_SCHEMA, user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=self.errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration (e.g., expired JWT token)."""
        entry = self._get_reconfigure_entry()
        
        if user_input is not None:
            self.data[CONF_JWT_TOKEN] = user_input[CONF_JWT_TOKEN]
            self.data[CONF_IGNORE_NON_OWNED] = user_input.get(CONF_IGNORE_NON_OWNED, entry.data.get(CONF_IGNORE_NON_OWNED, False))
            await self.validate_config()
            
            if not self.errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data={
                        CONF_JWT_TOKEN: user_input[CONF_JWT_TOKEN],
                        CONF_IGNORE_NON_OWNED: self.data[CONF_IGNORE_NON_OWNED],
                    },
                )
        
        # Pre-fill with existing token (masked)
        existing_token = entry.data.get(CONF_JWT_TOKEN, "")
        suggested_values = {
            CONF_JWT_TOKEN: existing_token if len(existing_token) < 20 else "",
            CONF_IGNORE_NON_OWNED: entry.data.get(CONF_IGNORE_NON_OWNED, False),
        }
        
        schema = self.add_suggested_values_to_schema(USER_DATA_SCHEMA, suggested_values)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=self.errors,
            description_placeholders={
                "username": self.username or "your account"
            },
        )


