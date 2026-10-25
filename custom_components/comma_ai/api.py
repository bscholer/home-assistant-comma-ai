"""API client for comma.ai."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientTimeout

from .const import ATHENA_BASE_URL

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

    @property
    def _headers(self) -> dict[str, str]:
        """Return the headers used to authenticate requests."""
        return {
            "Authorization": f"JWT {self.jwt_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict | list:
        """Make a request to the comma.ai API."""
        url = f"{self.base_url}{endpoint}"
        response = await self.session.request(
            method, url, headers=self._headers, **kwargs
        )
        
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

    async def get_turn_credentials(self) -> dict[str, Any]:
        """Get TURN/STUN servers for WebRTC live streaming."""
        return await self._request("GET", "/v1/me/turn")

    async def athena_rpc(
        self,
        dongle_id: str,
        method: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30,
    ) -> dict[str, Any]:
        """Call a JSON-RPC method on the device through comma's athena relay.

        Returns the raw JSON-RPC response, which holds either "result" or "error".
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": method,
            "params": params or {},
        }
        response = await self.session.post(
            f"{ATHENA_BASE_URL}/{dongle_id}",
            json=payload,
            headers=self._headers,
            timeout=ClientTimeout(total=timeout),
        )

        if response.status == 401:
            raise CommaAPIError("Invalid JWT token")
        if response.status >= 400:
            # athena answers 404 "Device not registered" when the device is offline
            body = (await response.text())[:200]
            raise CommaAPIError(f"Athena error {response.status}: {body}")

        return await response.json(content_type=None)
