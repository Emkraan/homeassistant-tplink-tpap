"""Switch per plug: Home Assistant compatibility (on = HA-compatible, off = TPAP)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import TplinkTpapCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TplinkTpapCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = []
        for plug in coordinator.data.get("plugs", []):
            if plug["thingName"] not in known:
                known.add(plug["thingName"])
                new.append(TplinkTpapSwitch(coordinator, plug["thingName"]))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class TplinkTpapSwitch(CoordinatorEntity[TplinkTpapCoordinator], SwitchEntity):
    """Home Assistant compatibility switch for one plug."""

    _attr_has_entity_name = True
    _attr_name = "Home Assistant compatibility"
    _attr_icon = "mdi:home-assistant"

    def __init__(self, coordinator: TplinkTpapCoordinator, thing_name: str) -> None:
        super().__init__(coordinator)
        self._thing = thing_name
        self._attr_unique_id = f"{thing_name}_ha_compat"

    @property
    def _plug(self) -> dict | None:
        for plug in self.coordinator.data.get("plugs", []):
            if plug["thingName"] == self._thing:
                return plug
        return None

    @property
    def available(self) -> bool:
        return super().available and self._plug is not None

    @property
    def device_info(self) -> DeviceInfo:
        plug = self._plug or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._thing)},
            name=plug.get("alias") or self._thing,
            manufacturer=MANUFACTURER,
            model=plug.get("model") or None,
        )

    @property
    def is_on(self) -> bool | None:
        plug = self._plug
        if not plug or plug.get("tpap_preferred") is None:
            return None
        # tpap_preferred True means the plug is on TPAP = HA-incompatible.
        return not plug["tpap_preferred"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_account_compatibility(True)
        await self.coordinator.client.set_device_tpap_preferred(self._thing, False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_device_tpap_preferred(self._thing, True)
        await self.coordinator.async_request_refresh()
