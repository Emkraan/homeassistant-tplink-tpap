"""Data coordinator: enforce the account Home Assistant compatibility setting.

The setting is account level and there is no readable GET for it: ``GET /v1/account/common-config``
returns ``400 "missing request parameter"`` for every known query shape (verified live), while the
``POST`` to the same path returns 200 and echoes the stored value. So the integration learns the
state only by writing it. When auto-heal is on (the default and the point of the integration), each
poll POSTs ``on``, which is idempotent and keeps the account's plugs reachable by the local
``tplink`` integration; the POST echo is the state. With auto-heal off there is no way to read the
state, so it is reported as unknown until the switch is used.
"""

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

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.client.login()
            self._logged_in = True

    async def _enforce(self) -> bool:
        """POST the setting on; the echo is the state. Re-login once on token expiry."""
        try:
            return await self.client.set_account_compatibility(True)
        except TplinkTpapAuthError:
            self._logged_in = False
            await self._ensure_login()
            return await self.client.set_account_compatibility(True)

    async def async_set_compatibility(self, on: bool) -> None:
        """Write the setting (switch actions) and update coordinator state from the echo."""
        await self._ensure_login()
        try:
            compatible = await self.client.set_account_compatibility(on)
        except TplinkTpapAuthError:
            self._logged_in = False
            await self._ensure_login()
            compatible = await self.client.set_account_compatibility(on)
        self.async_set_updated_data({"compatible": compatible})

    async def _async_update_data(self) -> dict:
        try:
            await self._ensure_login()
            if self.auto_heal:
                # No readable GET exists; enforce by POSTing on (idempotent, echoes state).
                compatible = await self._enforce()
            else:
                # Cannot read the state without writing it, and auto-heal is off.
                compatible = None
            return {"compatible": compatible}
        except TplinkTpapAuthError as err:
            raise UpdateFailed(f"authentication failed: {err}") from err
        except TplinkTpapError as err:
            raise UpdateFailed(str(err)) from err
