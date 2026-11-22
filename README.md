<div align="center">
  <img src="https://raw.githubusercontent.com/Emkraan/homeassistant-tplink-tpap/main/.github/homeassistant-tplink-tpap.png" alt="TP-Link Third-Party Compatibility" width="120" />
  <h1>TP-Link Third-Party Compatibility for Home Assistant</h1>
  <p>Keeps TP-Link / Kasa plugs on the Home Assistant compatible protocol, and auto-heals a plug that firmware-flips to TPAP.</p>

  [![HACS](https://img.shields.io/badge/HACS-Custom-orange?style=for-the-badge)](https://hacs.xyz)
  [![Release](https://img.shields.io/github/v/release/Emkraan/homeassistant-tplink-tpap?style=for-the-badge)](https://github.com/Emkraan/homeassistant-tplink-tpap/releases)
  [![HA Version](https://img.shields.io/badge/HA-2024.1.0%2B-blue?style=for-the-badge)](https://www.home-assistant.io)
  [![License](https://img.shields.io/github/license/Emkraan/homeassistant-tplink-tpap?style=for-the-badge)](LICENSE)
</div>

<div align="center">

⚠️ 🚨 **Unofficial integration. Not affiliated with or endorsed by TP-Link.** 🚨 ⚠️

</div>

---

## Table of Contents

- [Why](#why)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [How it works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Credits and license](#credits-and-license)

---

## Why

Some Kasa plugs firmware-flip the account setting **Me, Third-Party Compatibility** off. That puts the plug on TPAP and breaks the local `tplink` integration with a `403` at `handshake1`. The only documented fix is to toggle the setting back on in the Kasa app by hand, every time it happens. This integration does it for you.

- **Compatibility reconciliation switch**: on re-applies (reconciles) the account-level Home Assistant compatibility setting every poll, so a plug that firmware-flips it off is put back; off stops reconciling and turns it off once.
- **Refresh now button** to reconcile on demand, from the dashboard or an automation, without waiting for the next poll.
- **Last check** timestamp sensor so you can see the integration is alive and polling.
- **15-minute poll** by default: gentle on the cloud API, with the button covering "enforce right now".
- **Two-factor sign-in** supported: if TP-Link challenges with MFA (an emailed code, or an approval in the Kasa app), you complete it once and the device is trusted after that.
- **Cloud only**: it does not touch your plugs locally and does not need the Kasa app running.

## Requirements

| Requirement | Detail |
|---|---|
| Home Assistant | 2024.1.0 or newer |
| Account | A Kasa / TP-Link account that owns the plugs |
| Network | Outbound HTTPS to the TP-Link cloud |

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Emkraan&repository=homeassistant-tplink-tpap&category=integration)

1. Click the badge above, or in HACS open the three-dot menu, choose **Custom repositories**, and add `https://github.com/Emkraan/homeassistant-tplink-tpap` as an **Integration**.
2. Install **TP-Link Third-Party Compatibility**, then restart Home Assistant.
3. Go to **Settings -> Devices & Services -> Add Integration** and pick **TP-Link Third-Party Compatibility**.

## Configuration

Sign in with your Kasa / TP-Link email and password. If the account uses two-factor authentication, complete the challenge once (an emailed code, or an approval in the Kasa app); this device is then trusted so later sign-ins skip the step. Credentials are stored in Home Assistant and used only for the compatibility calls.

Options (gear icon on the integration) mirror the reconciliation switch: turning reconciliation off leaves the setting alone so you can manage it by hand.

## Entities

One device per account:

| Entity | Type | Purpose |
|---|---|---|
| Compatibility reconciliation | `switch` | On re-applies the setting every poll; off stops reconciling and turns it off once |
| Refresh now | `button` | Run a poll (and the reconcile) immediately, by hand or from an automation |
| Last check | `sensor` (diagnostic, timestamp) | When the integration last polled |

The default poll interval is **15 minutes**; press **Refresh now** (or call `button.press` on it) to enforce immediately.

## How it works

It talks to the TP-Link NBU IoT cloud, the same calls the Kasa app makes: a classic account login, then the account-level compatibility setting on the regional app server. The setting is written with a `POST` of `homeAssistantCompatibility`, which echoes the new value. There is no readable `GET` for it (the endpoint returns `400 "missing request parameter"`), so with enforcement on the integration simply re-applies `on` each poll rather than reading first.

## Troubleshooting

- **Setup says the code was wrong**: request a fresh code (re-run setup) and enter the newest one; codes expire quickly.
- **A plug is still unavailable in the `tplink` integration**: press **Refresh now** to enforce immediately, or wait for the next poll. The Kasa-app toggle is always a valid fallback.
- Turn on debug logging for `custom_components.tplink_tpap` to see the cloud calls.

## Credits and license

The classic cloud login signing is vendored from [piekstra/tplink-cloud-api](https://github.com/piekstra/tplink-cloud-api) (GPL-3.0). This project is therefore licensed **GPL-3.0**. Not affiliated with or endorsed by TP-Link.
