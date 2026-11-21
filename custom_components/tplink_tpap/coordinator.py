"""Data coordinator: list plugs, read TPAP state, and self-heal flipped plugs."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TplinkTpapAuthError, TplinkTpapClient, TplinkTpapError
from .const import (
    CONF_AUTO_HEAL,
    CONF_TERMINAL_UUID,
    DEFAULT_AUTO_HEAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class TplinkTpapCoordinator(DataUpdateCoordinator[dict]):
    """Polls the NBU cloud for plugs and their TPAP compatibility state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self.client = TplinkTpapClient(
            email=entry.data["email"],
            password=entry.data["password"],
            session=async_get_clientsession(hass),
            terminal_uuid=entry.data[CONF_TERMINAL_UUID],
        )
        self._logged_in = False

    @property
    def auto_heal(self) -> bool:
        return self.entry.options.get(CONF_AUTO_HEAL, DEFAULT_AUTO_HEAL)

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.client.login()
            self._logged_in = True

    async def _async_update_data(self) -> dict:
        try:
            await self._ensure_login()
            try:
                things = await self.client.get_things()
            except TplinkTpapAuthError:
                # token expired: re-login once and retry.
                self._logged_in = False
                await self._ensure_login()
                things = await self.client.get_things()

            plugs: list[dict] = []
            for thing in things:
                if thing.get("category") != "plug" and not str(
                    thing.get("thingModelId", "")
                ).startswith("kasa:plug"):
                    continue
                name = thing.get("thingName")
                preferred = await self.client.get_device_tpap_preferred(name)
                plug = {
                    "thingName": name,
                    "alias": thing.get("deviceAlias") or thing.get("alias") or name,
                    "model": thing.get("model", ""),
                    "tpap_preferred": preferred,
                }
                plugs.append(plug)

                # Self-heal: a plug sitting on TPAP (preferred True) is HA-incompatible.
                if self.auto_heal and preferred is True:
                    _LOGGER.info(
                        "Plug %s flipped to TPAP; re-enabling Home Assistant compatibility",
                        plug["alias"],
                    )
                    await self.client.set_account_compatibility(True)
                    await self.client.set_device_tpap_preferred(name, False)
                    plug["tpap_preferred"] = False

            return {"plugs": plugs}
        except TplinkTpapAuthError as err:
            raise UpdateFailed(f"authentication failed: {err}") from err
        except TplinkTpapError as err:
            raise UpdateFailed(str(err)) from err
