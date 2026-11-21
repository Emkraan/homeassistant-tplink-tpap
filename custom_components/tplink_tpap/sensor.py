"""Diagnostic sensor per plug: current compatibility state."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
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
                new.append(TplinkTpapStateSensor(coordinator, plug["thingName"]))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class TplinkTpapStateSensor(CoordinatorEntity[TplinkTpapCoordinator], SensorEntity):
    """Reports compatible / tpap / unknown for one plug."""

    _attr_has_entity_name = True
    _attr_name = "Compatibility state"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options: ClassVar[list[str]] = ["compatible", "tpap", "unknown"]

    def __init__(self, coordinator: TplinkTpapCoordinator, thing_name: str) -> None:
        super().__init__(coordinator)
        self._thing = thing_name
        self._attr_unique_id = f"{thing_name}_compat_state"

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
    def native_value(self) -> str:
        plug = self._plug
        if not plug or plug.get("tpap_preferred") is None:
            return "unknown"
        return "tpap" if plug["tpap_preferred"] else "compatible"
