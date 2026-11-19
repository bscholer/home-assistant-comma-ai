"""Camera platform for comma.ai."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.camera import (
    Camera,
    CameraEntityDescription,
    async_get_still_stream,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CAMERA_DRIVER, CAMERA_ROAD, DOMAIN
from .coordinator import CommaDataUpdateCoordinator
from .livestream import CommaLiveStream

if TYPE_CHECKING:
    from aiohttp import web
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import CommaConfigEntry

_LOGGER = logging.getLogger(__name__)

# Starting a stream goes through comma's cloud and may wake the device's
# cameras, so a first snapshot can take a while
SNAPSHOT_TIMEOUT = 25
MJPEG_FRAME_TIMEOUT = 25


class CommaCameraEntityDescription(CameraEntityDescription, frozen_or_thawed=True):
    """Description for comma.ai Camera Entity."""

    camera: str


CAMERA_DESCRIPTIONS: tuple[CommaCameraEntityDescription, ...] = (
    CommaCameraEntityDescription(
        key="road_camera",
        translation_key="road_camera",
        camera=CAMERA_ROAD,
    ),
    CommaCameraEntityDescription(
        key="driver_camera",
        translation_key="driver_camera",
        camera=CAMERA_DRIVER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CommaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up comma.ai camera entities."""
    coordinator = config_entry.runtime_data.coordinator
    api_client = config_entry.runtime_data.api_client
    livestreams = config_entry.runtime_data.livestreams

    entities = []
    for dongle_id in coordinator.data["devices"]:
        livestream = livestreams.setdefault(
            dongle_id, CommaLiveStream(hass, api_client, dongle_id)
        )
        for description in CAMERA_DESCRIPTIONS:
            entities.append(
                CommaCamera(coordinator, dongle_id, livestream, description)
            )

    async_add_entities(entities)


class CommaCamera(CoordinatorEntity[CommaDataUpdateCoordinator], Camera):
    """Live view of one of a comma device's cameras."""

    _attr_has_entity_name = True
    # the stream is pushed as fast as frames arrive; see handle_async_mjpeg_stream
    _attr_frame_interval = 0.1

    entity_description: CommaCameraEntityDescription

    def __init__(
        self,
        coordinator: CommaDataUpdateCoordinator,
        dongle_id: str,
        livestream: CommaLiveStream,
        description: CommaCameraEntityDescription,
    ) -> None:
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        self.entity_description = description
        self.dongle_id = dongle_id
        self.livestream = livestream

        device = coordinator.data["devices"][dongle_id]
        self._attr_unique_id = f"{dongle_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dongle_id)},
            name=device["alias"],
            manufacturer="comma.ai",
            model=device["device_type"],
            sw_version=device["openpilot_version"],
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to live stream state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.livestream.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.dongle_id in self.coordinator.data["devices"]

    @property
    def is_streaming(self) -> bool:
        """Return True while the device is streaming this camera."""
        return (
            self.livestream.connected
            and self.livestream.active_camera == self.entity_description.camera
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return why the last stream attempt failed, if it did."""
        return {"last_error": self.livestream.last_error}

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image from the live stream."""
        return await self.livestream.async_get_image(
            self.entity_description.camera, SNAPSHOT_TIMEOUT
        )

    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse | None:
        """Serve the live stream as MJPEG, one image per received frame."""
        camera = self.entity_description.camera
        last_seq = 0
        last_image: bytes | None = None

        async def next_image() -> bytes | None:
            nonlocal last_seq, last_image
            result = await self.livestream.async_next_image(
                camera, last_seq, MJPEG_FRAME_TIMEOUT
            )
            if result is None:
                # no new frames: end the stream, unless we can keep showing
                # the last frame while the other camera has the video track
                return last_image if self.livestream.connected else None
            last_seq, last_image = result
            return last_image

        return await async_get_still_stream(
            request, next_image, self.content_type, self.frame_interval
        )
