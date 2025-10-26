"""Device tracker platform for comma.ai."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CommaDataUpdateCoordinator, CommaDevice

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import CommaConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CommaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up comma.ai device tracker entities."""
    coordinator = config_entry.runtime_data.coordinator

    entities = []
    for dongle_id in coordinator.data["devices"]:
        entities.append(CommaDeviceTracker(coordinator, dongle_id))

    async_add_entities(entities)


class CommaDeviceTracker(CoordinatorEntity[CommaDataUpdateCoordinator], TrackerEntity):
    """Representation of a comma.ai device tracker."""

    _attr_has_entity_name = True
    _attr_translation_key = "location"

    def __init__(
        self,
        coordinator: CommaDataUpdateCoordinator,
        dongle_id: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self.dongle_id = dongle_id
        
        device = coordinator.data["devices"][dongle_id]
        self._attr_unique_id = f"{dongle_id}_tracker"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dongle_id)},
            name=device["alias"],
            manufacturer="comma.ai",
            model=device["device_type"],
            sw_version=device["openpilot_version"],
        )

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        device = self.coordinator.data["devices"].get(self.dongle_id)
        if device is None:
            return None
        return device["location_lat"]

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        device = self.coordinator.data["devices"].get(self.dongle_id)
        if device is None:
            return None
        return device["location_lng"]

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        # Location accuracy is not provided by the comma.ai location API
        return 0

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        # Battery level is not provided by the comma.ai API
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        device = self.coordinator.data["devices"].get(self.dongle_id)
        return (
            super().available
            and device is not None
            and device["location_lat"] is not None
            and device["location_lng"] is not None
        )


