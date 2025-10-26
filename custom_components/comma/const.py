"""Constants for the comma.ai integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "comma"
PLATFORMS = [Platform.SENSOR, Platform.DEVICE_TRACKER]

CONF_JWT_TOKEN: Final = "jwt_token"

API_BASE_URL: Final = "https://api.commadotai.com"

# Update interval in seconds
UPDATE_INTERVAL: Final = 60


