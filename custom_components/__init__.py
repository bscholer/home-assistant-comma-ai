"""The comma.ai integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo

from .api import CommaAPIClient
from .const import CONF_JWT_TOKEN, DOMAIN, PLATFORMS
from .coordinator import CommaDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class CommaData:
    """Dataclass for runtime data."""

    coordinator: CommaDataUpdateCoordinator
    api_client: CommaAPIClient


type CommaConfigEntry = ConfigEntry[CommaData]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CommaConfigEntry,
) -> bool:
    """Set up comma.ai integration using config entry."""
    _LOGGER.debug("Setting up comma.ai integration")
    
    api_client = CommaAPIClient(
        jwt_token=config_entry.data[CONF_JWT_TOKEN],
        session=async_get_clientsession(hass),
    )
    
    # Validate the token by fetching profile
    try:
        profile = await api_client.get_profile()
        _LOGGER.debug("Authenticated as user: %s", profile.get("username"))
    except Exception as err:
        _LOGGER.error("Failed to authenticate with comma.ai: %s", err)
        return False

    coordinator = CommaDataUpdateCoordinator(hass, config_entry, api_client)
    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = CommaData(
        coordinator=coordinator,
        api_client=api_client,
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CommaConfigEntry) -> bool:
    """Unload comma.ai config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        del entry.runtime_data
    return unload_ok


