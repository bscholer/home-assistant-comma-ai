"""Binary sensor platform for comma.ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CommaDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import CommaConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CommaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up comma.ai binary sensor entities."""
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities(
        CommaCarRunningSensor(coordinator, dongle_id)
        for dongle_id in coordinator.data["devices"]
    )


class CommaCarRunningSensor(CoordinatorEntity[CommaDataUpdateCoordinator], BinarySensorEntity):
    """Whether the car the device is in is switched on."""

    _attr_has_entity_name = True
    _attr_translation_key = "car_running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: CommaDataUpdateCoordinator,
        dongle_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.dongle_id = dongle_id

        device = coordinator.data["devices"][dongle_id]
        self._attr_unique_id = f"{dongle_id}_car_running"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dongle_id)},
            name=device["alias"],
            manufacturer="comma.ai",
            model=device["device_type"],
            sw_version=device["openpilot_version"],
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the car is on."""
        device = self.coordinator.data["devices"].get(self.dongle_id)
        if device is None:
            return None
        # athena can't reach a sleeping device, which only happens with the car off
        return bool(device["car_running"])

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.dongle_id in self.coordinator.data["devices"]
