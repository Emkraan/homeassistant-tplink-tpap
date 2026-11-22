"""Diagnostic sensor: the last check timestamp.

There is no readable GET for the account compatibility setting, so a
"compatibility state" sensor could only ever echo the value just written and
would carry no real information. The only honest, useful signal is when the
integration last ran, which this sensor reports.
"""

from __future__ import annotations

from datetime import datetime

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
    async_add_entities([TplinkTpapLastCheckSensor(coordinator)])


class TplinkTpapLastCheckSensor(CoordinatorEntity[TplinkTpapCoordinator], SensorEntity):
    """Timestamp of the last poll, so it is visible that the integration is alive."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_check"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: TplinkTpapCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_last_check"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=ACCOUNT_NAME,
            manufacturer=MANUFACTURER,
        )

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.get("last_check")
