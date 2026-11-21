# TP-Link Third-Party Compatibility (TPAP) for Home Assistant

Keeps TP-Link / Kasa plugs on the **Home Assistant compatible** protocol so the
local `tplink` integration keeps working.

Some Kasa plugs firmware-flip the account setting **Me, Third-Party Compatibility**
off, which puts the plug on TPAP and breaks the local `tplink` integration with a
`403` at `handshake1`. The only documented fix is to toggle that setting back in the
Kasa app by hand. This integration does it for you: it exposes the setting as a
switch and, by default, automatically re-enables compatibility the moment a plug
flips to TPAP.

## What it does

- One **Home Assistant compatibility** switch per plug (on = HA-compatible, off = TPAP).
- A diagnostic **Compatibility state** sensor per plug (`compatible` / `tpap` / `unknown`).
- **Self-heal**: when a plug flips to TPAP, compatibility is re-enabled on the next poll
  (every few minutes). Turn this off in the integration's Options if you prefer manual control.

## How it works

It talks to the TP-Link NBU IoT cloud directly, the same calls the Kasa app makes:
a classic account login, then account-level and per-device compatibility settings on
the regional app server. It does not touch your plugs locally and does not need the
Kasa app running.

## Install (HACS)

1. HACS -> three dots -> **Custom repositories**.
2. Add `https://github.com/Emkraan/homeassistant-tplink-tpap` as an **Integration**.
3. Install **TP-Link Third-Party Compatibility**, then restart Home Assistant.
4. **Settings -> Devices & Services -> Add Integration -> TP-Link Third-Party Compatibility**,
   and sign in with your Kasa / TP-Link account.

Your email and password are stored in Home Assistant and used only for these calls.

## Credits and license

The classic cloud login signing is vendored from
[piekstra/tplink-cloud-api](https://github.com/piekstra/tplink-cloud-api) (GPL-3.0).
This project is therefore licensed **GPL-3.0**. Not affiliated with or endorsed by TP-Link.
