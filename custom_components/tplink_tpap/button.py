"""Refresh now button: run a poll (and the enforce) on demand."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ACCOUNT_NAME, DOMAIN, MANUFACTURER
from .coordinator import TplinkTpapCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TplinkTpapCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TplinkTpapRefreshButton(coordinator)])


class TplinkTpapRefreshButton(CoordinatorEntity[TplinkTpapCoordinator], ButtonEntity):
    """Runs a poll immediately; with enforcement on this re-applies compatibility."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh_now"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: TplinkTpapCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_refresh_now"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=ACCOUNT_NAME,
            manufacturer=MANUFACTURER,
        )

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
