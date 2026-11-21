"""Diagnostic sensor: current account compatibility state."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ACCOUNT_NAME, DOMAIN, MANUFACTURER
from .coordinator import TplinkTpapCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TplinkTpapCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TplinkTpapStateSensor(coordinator)])


class TplinkTpapStateSensor(CoordinatorEntity[TplinkTpapCoordinator], SensorEntity):
    """Reports compatible / tpap / unknown for the account."""

    _attr_has_entity_name = True
    _attr_translation_key = "compatibility_state"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: ClassVar[list[str]] = ["compatible", "tpap", "unknown"]

    def __init__(self, coordinator: TplinkTpapCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_compat_state"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=ACCOUNT_NAME,
            manufacturer=MANUFACTURER,
        )

    @property
    def native_value(self) -> str:
        compatible = self.coordinator.data.get("compatible")
        if compatible is None:
            return "unknown"
        return "compatible" if compatible else "tpap"
