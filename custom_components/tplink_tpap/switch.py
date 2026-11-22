"""Account-level compatibility reconciliation switch.

On means reconcile Home Assistant compatibility: every poll POSTs ``on`` so a plug that firmware-flips
the account setting off is put back. Off means stop reconciling (so the setting is left alone) and POST
``off`` once, so turning the switch off actually sticks instead of being re-enabled on the next poll.
The entity's unique_id is kept as the original ``_ha_compatibility`` so existing installs are not orphaned.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ACCOUNT_NAME, CONF_AUTO_HEAL, DOMAIN, MANUFACTURER
from .coordinator import TplinkTpapCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TplinkTpapCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TplinkTpapSwitch(coordinator)])


class TplinkTpapSwitch(CoordinatorEntity[TplinkTpapCoordinator], SwitchEntity):
    """Enforcement toggle for account Home Assistant compatibility."""

    _attr_has_entity_name = True
    _attr_translation_key = "reconciliation"
    _attr_icon = "mdi:autorenew"

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
    def is_on(self) -> bool:
        # The switch reflects enforcement, not a (non-readable) live account value.
        return self.coordinator.auto_heal

    def _set_enforcement(self, on: bool) -> None:
        entry = self.coordinator.entry
        self.hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_AUTO_HEAL: on}
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Enabling enforcement: the options-update listener refreshes, which POSTs on.
        self._set_enforcement(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        # POST off once so it sticks, then stop enforcing so it is not re-enabled next poll.
        await self.coordinator.async_set_compatibility(False)
        self._set_enforcement(False)
