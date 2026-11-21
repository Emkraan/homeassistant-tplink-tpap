# Changelog

## 2026.11.1

- Fix setup failing with "Unknown error": build the TLS context in an executor instead of the event loop.
- Move to the Emkraan org with the standard HA integration repo layout (validate CI, ruff, brand icon, renovate, security policy).

## 2026.11.0

- Initial release.
- Config flow for a Kasa / TP-Link account (email and password, stored locally).
- One switch per plug for Home Assistant (Third-Party) compatibility, and a diagnostic compatibility-state sensor.
- Automatic self-heal: when a plug firmware-flips to TPAP, re-enables Home Assistant compatibility on the next poll (toggle in Options).
