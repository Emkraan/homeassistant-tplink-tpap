"""Constants for the TP-Link Third-Party Compatibility integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "tplink_tpap"
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]

CONF_TERMINAL_UUID = "terminal_uuid"
CONF_AUTO_HEAL = "auto_heal"

DEFAULT_AUTO_HEAL = True
# Cloud polling; the plug flip is infrequent, so a few minutes is plenty.
DEFAULT_SCAN_INTERVAL = 300

MANUFACTURER = "TP-Link"
ACCOUNT_NAME = "TP-Link account"
