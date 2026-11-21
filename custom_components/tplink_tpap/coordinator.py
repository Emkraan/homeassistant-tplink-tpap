"""Data coordinator: enforce the account Home Assistant compatibility setting.

The setting is account level and there is no readable GET for it: ``GET /v1/account/common-config``
returns ``400 "missing request parameter"`` for every known query shape (verified live), while the
``POST`` to the same path returns 200 and echoes the stored value. The POST echoes only the new value,
with no "changed" flag, prior value, or timestamp (verified live by an on/off/on cycle), so whether a
poll actually found the setting off cannot be detected. The integration therefore enforces: when
enforcement is on (the ``auto_heal`` option, the default), each poll POSTs ``on``, which is idempotent
and keeps the account's plugs reachable by the local ``tplink`` integration. With enforcement off there
is no readable state, so the last known value is kept.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
    """Enforces the account Home Assistant compatibility setting (no readable GET)."""

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

    @property
    def _last_compatible(self) -> bool | None:
        return (self.data or {}).get("compatible")

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.client.login()
            self._logged_in = True

    async def _post(self, on: bool) -> bool:
        """POST the setting; the echo is the state. Re-login once on token expiry."""
        try:
            return await self.client.set_account_compatibility(on)
        except TplinkTpapAuthError:
            self._logged_in = False
            await self._ensure_login()
            return await self.client.set_account_compatibility(on)

    async def async_set_compatibility(self, on: bool) -> None:
        """Write the setting (switch actions) and publish state from the POST echo."""
        await self._ensure_login()
        compatible = await self._post(on)
        self.async_set_updated_data({"compatible": compatible, "last_check": dt_util.utcnow()})

    async def _async_update_data(self) -> dict:
        now: datetime = dt_util.utcnow()
        try:
            await self._ensure_login()
            if self.auto_heal:
                # No readable GET exists; enforce by POSTing on (idempotent, echoes state).
                # The echo carries no prior value, so a poll that actually found it off is
                # indistinguishable from steady state and cannot be surfaced as an event.
                compatible = await self._post(True)
                _LOGGER.info("Enforced Home Assistant compatibility (posted on)")
            else:
                # Enforcement off: cannot read state, keep the last known value.
                compatible = self._last_compatible
            return {"compatible": compatible, "last_check": now}
        except TplinkTpapAuthError as err:
            raise UpdateFailed(f"authentication failed: {err}") from err
        except TplinkTpapError as err:
            raise UpdateFailed(str(err)) from err
