# Changelog

## 2026.11.2

- Support two-factor authentication: when TP-Link challenges with MFA, a code is emailed and the config flow prompts for it, then binds this device so future sign-ins skip MFA.
- Never crash the config flow on an unexpected login response (the "Unknown error" case); surface a clear message instead.

## 2026.11.1

- Fix setup failing with "Unknown error": build the TLS context in an executor instead of the event loop.
- Move to the Emkraan org with the standard HA integration repo layout (validate CI, ruff, brand icon, renovate, security policy).

## 2026.11.0

- Initial release.
- Config flow for a Kasa / TP-Link account (email and password, stored locally).
- One switch per plug for Home Assistant (Third-Party) compatibility, and a diagnostic compatibility-state sensor.
- Automatic self-heal: when a plug firmware-flips to TPAP, re-enables Home Assistant compatibility on the next poll (toggle in Options).
