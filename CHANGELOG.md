# Changelog

## 2026.11.6

- The switch is now an enforcement toggle: on means re-apply Home Assistant compatibility every poll; off stops enforcing and turns it off once, so turning the switch off now sticks instead of being re-enabled on the next poll.
- Added a Refresh now button that runs a poll (and the enforce) on demand, for manual use or automations.
- Poll interval is now 15 minutes (was 5); the button covers "enforce right now", so the steady poll can be gentle on the cloud API.
- Added a Last check timestamp sensor so it is visible that the integration is alive and polling.
- Reworded the two-factor step: it no longer claims the code is emailed, since some accounts approve in the Kasa app instead.
- Note: a poll that found the setting off cannot be surfaced as a distinct event. The `POST` echoes only the new value, with no prior value or changed flag (verified live by an on/off/on cycle), and there is no readable `GET`, so "found off" is not detectable. Each enforce is logged at INFO instead.

## 2026.11.5

- Fix the entry getting stuck in setup: `GET /v1/account/common-config` is not readable. Verified live against the account, it returns `400 "missing request parameter"` for every known query shape (no params, `keys`, `configKeys`, `key`, `configKey`, `names`, and the standard app query), while `GET /v2/things` with the same auth returns 200.
- Read state by writing it instead: the `POST` to that path returns 200 and echoes the stored value (verified). With auto-heal on (the default), each poll POSTs `on`, which keeps the account's plugs reachable and reports the echoed state. With auto-heal off the state is reported as unknown, since there is no readable GET.

## 2026.11.4

- Redesign to the account-level Home Assistant compatibility setting. The previous per-device read hit `GET /v1/things/{name}/features/thirdPartyCompatibility`, which is not a real endpoint (the Kasa app only ever PATCHes it), so every device returned 404 and no entities were created.
- Read the real, account-level setting with `GET /v1/account/common-config` (`homeAssistantCompatibility` on/off), expose it as one switch and one compatibility-state sensor, and self-heal by turning it back on when it reads off.

## 2026.11.3

- Do not fail setup when a device has no thirdPartyCompatibility feature: devices that return 404 (for example the HS300 power strip) are skipped instead of erroring the whole entry.
- Treat a network error on an app-server call as a clean retry rather than an unexpected failure.

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
