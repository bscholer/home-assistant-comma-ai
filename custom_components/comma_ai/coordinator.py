"""Data update coordinator for comma.ai."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any, TypedDict

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CommaAPIError
from .const import CONF_IGNORE_NON_OWNED, DOMAIN, UPDATE_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import CommaConfigEntry
    from .api import CommaAPIClient

_LOGGER = logging.getLogger(__name__)


class CommaDevice(TypedDict):
    """Type for comma device data."""

    dongle_id: str
    alias: str
    device_type: str
    is_owner: bool
    is_paired: bool
    prime: bool
    location_lat: float | None
    location_lng: float | None
    location_time: int | None
    last_athena_ping: int | None
    openpilot_version: str | None
    git_branch: str | None
    git_commit: str | None
    git_commit_date: str | None
    git_remote: str | None
    git_dirty: bool | None
    platform: str | None
    stats: dict[str, Any] | None


class CommaCoordinatorData(TypedDict):
    """Type for coordinator data."""

    profile: dict[str, Any]
    devices: dict[str, CommaDevice]


class CommaDataUpdateCoordinator(DataUpdateCoordinator[CommaCoordinatorData]):
    """Class to manage fetching comma.ai data."""

    config_entry: CommaConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: CommaConfigEntry, api_client: CommaAPIClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api_client = api_client

    async def _async_update_data(self) -> CommaCoordinatorData:
        """Fetch data from API."""
        try:
            async with asyncio.TaskGroup() as tg:
                profile_task = tg.create_task(self.api_client.get_profile())
                devices_task = tg.create_task(self.api_client.get_devices())

            profile = profile_task.result()
            devices_list = devices_task.result()

            # Filter out non-owned devices if configured
            ignore_non_owned = self.config_entry.data.get(CONF_IGNORE_NON_OWNED, False)
            if ignore_non_owned:
                devices_list = [d for d in devices_list if d.get("is_owner", False)]

            # Convert devices list to dict keyed by dongle_id
            devices: dict[str, CommaDevice] = {}
            
            # Fetch stats, location and recent routes for each device
            stats_tasks = {}
            location_tasks = {}
            routes_tasks = {}
            async with asyncio.TaskGroup() as tg:
                for device in devices_list:
                    dongle_id = device["dongle_id"]
                    stats_tasks[dongle_id] = tg.create_task(
                        self._get_device_stats(dongle_id)
                    )
                    location_tasks[dongle_id] = tg.create_task(
                        self._get_device_location(dongle_id)
                    )
                    routes_tasks[dongle_id] = tg.create_task(
                        self._get_device_routes(dongle_id)
                    )
            
            for device in devices_list:
                dongle_id = device["dongle_id"]
                stats = stats_tasks[dongle_id].result()
                location = location_tasks[dongle_id].result()
                latest_route = self._latest_route(routes_tasks[dongle_id].result())
                
                devices[dongle_id] = CommaDevice(
                    dongle_id=dongle_id,
                    alias=device.get("alias", "Unknown"),
                    device_type=device.get("device_type", "unknown"),
                    is_owner=device.get("is_owner", False),
                    is_paired=device.get("is_paired", False),
                    prime=device.get("prime", False),
                    location_lat=location.get("lat") if location else None,
                    location_lng=location.get("lng") if location else None,
                    location_time=location.get("time") if location else None,
                    last_athena_ping=device.get("last_athena_ping"),
                    openpilot_version=device.get("openpilot_version"),
                    git_branch=latest_route.get("git_branch"),
                    git_commit=latest_route.get("git_commit"),
                    git_commit_date=latest_route.get("git_commit_date"),
                    git_remote=latest_route.get("git_remote"),
                    git_dirty=latest_route.get("git_dirty"),
                    platform=latest_route.get("platform"),
                    stats=stats,
                )

            return CommaCoordinatorData(
                profile=profile,
                devices=devices,
            )

        except CommaAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _get_device_stats(self, dongle_id: str) -> dict[str, Any] | None:
        """Get device stats, return None if not available."""
        try:
            return await self.api_client.get_device_stats(dongle_id)
        except CommaAPIError:
            _LOGGER.debug("Could not fetch stats for device %s", dongle_id)
            return None

    async def _get_device_location(self, dongle_id: str) -> dict[str, Any] | None:
        """Get device location, return None if not available."""
        try:
            return await self.api_client.get_device_location(dongle_id)
        except CommaAPIError:
            _LOGGER.debug("Could not fetch location for device %s", dongle_id)
            return None

    async def _get_device_routes(self, dongle_id: str) -> list[dict[str, Any]]:
        """Get recent device routes, return an empty list if not available."""
        try:
            return await self.api_client.get_device_routes(dongle_id)
        except CommaAPIError:
            _LOGGER.debug("Could not fetch routes for device %s", dongle_id)
            return []

    @staticmethod
    def _latest_route(routes: list[dict[str, Any]]) -> dict[str, Any]:
        """Return the most recent route, or an empty dict when there are none."""
        if not routes:
            return {}
        return max(routes, key=lambda route: route.get("create_time") or 0)


