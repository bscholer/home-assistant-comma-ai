"""API client for comma.ai."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)


class CommaAPIError(Exception):
    """Raised when the API returns an error."""


class CommaAPIClient:
    """comma.ai API Client."""

    def __init__(self, jwt_token: str, session: ClientSession) -> None:
        """Initialize the API client."""
        self.jwt_token = jwt_token
        self.session = session
        self.base_url = "https://api.commadotai.com"

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict | list:
        """Make a request to the comma.ai API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"JWT {self.jwt_token}",
            "Content-Type": "application/json",
        }

        response = await self.session.request(method, url, headers=headers, **kwargs)
        
        if response.status == 401:
            raise CommaAPIError("Invalid JWT token")
        elif response.status == 403:
            raise CommaAPIError("Access forbidden")
        elif response.status == 404:
            raise CommaAPIError("Resource not found")
        elif response.status >= 400:
            raise CommaAPIError(f"API error: {response.status}")

        return await response.json()

    async def get_profile(self) -> dict[str, Any]:
        """Get user profile information."""
        return await self._request("GET", "/v1/me/")

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get list of devices owned or readable by authenticated user."""
        return await self._request("GET", "/v1/me/devices/")

    async def get_device_location(self, dongle_id: str) -> dict[str, Any]:
        """Get device location information."""
        return await self._request("GET", f"/v1/devices/{dongle_id}/location")

    async def get_device_stats(self, dongle_id: str) -> dict[str, Any]:
        """Get device driving statistics."""
        return await self._request("GET", f"/v1.1/devices/{dongle_id}/stats")


