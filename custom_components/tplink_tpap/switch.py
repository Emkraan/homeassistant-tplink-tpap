"""Account-level switch: Home Assistant compatibility (on = HA-compatible, off = TPAP)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    async_add_entities([TplinkTpapSwitch(coordinator)])


class TplinkTpapSwitch(CoordinatorEntity[TplinkTpapCoordinator], SwitchEntity):
    """Account-level Home Assistant compatibility switch."""

    _attr_has_entity_name = True
    _attr_translation_key = "ha_compatibility"
    _attr_icon = "mdi:home-assistant"

    def __init__(self, coordinator: TplinkTpapCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ha_compatibility"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=ACCOUNT_NAME,
            manufacturer=MANUFACTURER,
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("compatible")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_account_compatibility(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_account_compatibility(False)
        await self.coordinator.async_request_refresh()
