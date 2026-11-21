"""Data coordinator: read the account Home Assistant compatibility setting and self-heal."""

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
    """Polls the NBU cloud for the account Home Assistant compatibility setting.

    The setting is account level: ``GET /v1/account/common-config`` returns
    ``homeAssistantCompatibility: on|off``. It is the single switch that keeps the
    account's plugs reachable by the local ``tplink`` integration. There is no readable
    per-device endpoint (the per-device ``thirdPartyCompatibility`` is PATCH-only), so the
    integration models the account setting rather than one entity per plug.
    """

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
                compatible = await self.client.get_account_compatibility()
            except TplinkTpapAuthError:
                # token expired: re-login once and retry.
                self._logged_in = False
                await self._ensure_login()
                compatible = await self.client.get_account_compatibility()

            # Self-heal: the setting reading off means a plug flip turned it off; put it
            # back on so the local tplink integration keeps working.
            if self.auto_heal and compatible is False:
                _LOGGER.info(
                    "Account Home Assistant compatibility is off; re-enabling it",
                )
                compatible = await self.client.set_account_compatibility(True)

            return {"compatible": compatible}
        except TplinkTpapAuthError as err:
            raise UpdateFailed(f"authentication failed: {err}") from err
        except TplinkTpapError as err:
            raise UpdateFailed(str(err)) from err
