"""Sensor platform for comma.ai."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CommaDataUpdateCoordinator, CommaDevice

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from . import CommaConfigEntry

_LOGGER = logging.getLogger(__name__)


class CommaSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """Description for comma.ai Sensor Entity."""

    value_fn: Callable[[CommaDevice], StateType]
    extra_values_fn: Callable[[CommaDevice], dict[str, Any]] | None = None


def get_last_ping_time(device: CommaDevice) -> StateType:
    """Get last ping time as datetime."""
    if device["last_athena_ping"] is None:
        return None
    return datetime.fromtimestamp(device["last_athena_ping"], tz=timezone.utc)


def get_last_location_time(device: CommaDevice) -> StateType:
    """Get last location time as datetime."""
    if device["location_time"] is None:
        return None
    # API returns milliseconds
    return datetime.fromtimestamp(device["location_time"] / 1000, tz=timezone.utc)


SENSOR_DESCRIPTIONS: tuple[CommaSensorEntityDescription, ...] = (
    CommaSensorEntityDescription(
        key="dongle_id",
        translation_key="dongle_id",
        icon="mdi:identifier",
        value_fn=lambda device: device["dongle_id"],
    ),
    CommaSensorEntityDescription(
        key="device_type",
        translation_key="device_type",
        icon="mdi:car-connected",
        value_fn=lambda device: device["device_type"],
    ),
    CommaSensorEntityDescription(
        key="is_owner",
        translation_key="is_owner",
        icon="mdi:account-check",
        value_fn=lambda device: "Yes" if device["is_owner"] else "No",
    ),
    CommaSensorEntityDescription(
        key="is_paired",
        translation_key="is_paired",
        icon="mdi:link-variant",
        value_fn=lambda device: "Yes" if device["is_paired"] else "No",
    ),
    CommaSensorEntityDescription(
        key="openpilot_version",
        translation_key="openpilot_version",
        icon="mdi:application-cog",
        value_fn=lambda device: device["openpilot_version"],
    ),
    CommaSensorEntityDescription(
        key="is_prime",
        translation_key="is_prime",
        icon="mdi:crown",
        value_fn=lambda device: "Yes" if device["prime"] else "No",
    ),
    CommaSensorEntityDescription(
        key="last_ping",
        translation_key="last_ping",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=get_last_ping_time,
    ),
    CommaSensorEntityDescription(
        key="last_location_time",
        translation_key="last_location_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=get_last_location_time,
    ),
    # All-time stats
    CommaSensorEntityDescription(
        key="total_distance",
        translation_key="total_distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_unit_of_measurement=UnitOfLength.MILES,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        icon="mdi:map-marker-distance",
        value_fn=lambda device: device["stats"]["all"]["distance"] if device["stats"] else None,
    ),
    CommaSensorEntityDescription(
        key="total_minutes",
        translation_key="total_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:clock-outline",
        value_fn=lambda device: device["stats"]["all"]["minutes"] if device["stats"] else None,
    ),
    CommaSensorEntityDescription(
        key="total_routes",
        translation_key="total_routes",
        icon="mdi:road-variant",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device["stats"]["all"]["routes"] if device["stats"] else None,
    ),
    # Week stats
    CommaSensorEntityDescription(
        key="week_distance",
        translation_key="week_distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_unit_of_measurement=UnitOfLength.MILES,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        icon="mdi:calendar-week",
        value_fn=lambda device: device["stats"]["week"]["distance"] if device["stats"] else None,
    ),
    CommaSensorEntityDescription(
        key="week_minutes",
        translation_key="week_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:calendar-week",
        value_fn=lambda device: device["stats"]["week"]["minutes"] if device["stats"] else None,
    ),
    CommaSensorEntityDescription(
        key="week_routes",
        translation_key="week_routes",
        icon="mdi:calendar-week",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda device: device["stats"]["week"]["routes"] if device["stats"] else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: CommaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up comma.ai sensor entities."""
    coordinator = config_entry.runtime_data.coordinator

    entities = []
    for dongle_id, device in coordinator.data["devices"].items():
        for description in SENSOR_DESCRIPTIONS:
            entities.append(CommaDeviceSensor(coordinator, dongle_id, description))

    async_add_entities(entities)


class CommaDeviceSensor(CoordinatorEntity[CommaDataUpdateCoordinator], SensorEntity):
    """Representation of a comma.ai device sensor."""

    entity_description: CommaSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CommaDataUpdateCoordinator,
        dongle_id: str,
        description: CommaSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.dongle_id = dongle_id
        self.entity_description = description
        
        device = coordinator.data["devices"][dongle_id]
        self._attr_unique_id = f"{dongle_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dongle_id)},
            name=device["alias"],
            manufacturer="comma.ai",
            model=device["device_type"],
            sw_version=device["openpilot_version"],
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        device = self.coordinator.data["devices"].get(self.dongle_id)
        if device is None:
            return None
        return self.entity_description.value_fn(device)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        device = self.coordinator.data["devices"].get(self.dongle_id)
        if device is None or self.entity_description.extra_values_fn is None:
            return None
        return self.entity_description.extra_values_fn(device)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.dongle_id in self.coordinator.data["devices"]
        )

