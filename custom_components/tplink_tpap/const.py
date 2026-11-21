"""Constants for the TP-Link Third-Party Compatibility integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "tplink_tpap"
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.BUTTON]

CONF_TERMINAL_UUID = "terminal_uuid"
CONF_AUTO_HEAL = "auto_heal"

DEFAULT_AUTO_HEAL = True
# Cloud polling; the plug flip is infrequent and the API is a shared cloud, so 15 minutes
# for steady state. The Refresh now button covers "enforce immediately" on demand.
DEFAULT_SCAN_INTERVAL = 900

MANUFACTURER = "TP-Link"
ACCOUNT_NAME = "TP-Link account"
