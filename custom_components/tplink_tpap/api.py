"""Async client for the TP-Link NBU IoT cloud, scoped to the Third-Party
Compatibility (TPAP) toggle.

The classic cloud login (V2, HMAC-SHA1) is reused from the vendored ``tplinkcloud``
signing module (piekstra/tplink-cloud-api, GPL-3.0). The NBU app-server calls were
reverse-engineered from the Kasa Android app: the app-server authenticates REST calls
with ``Authorization: ut|<classic token>`` plus an ``app-cid`` and a set of ``x-*``
headers, over plain TLS (no client certificate, no JWT for REST).
"""

from __future__ import annotations

import asyncio
import ssl
import uuid
from dataclasses import dataclass, field

import aiohttp

from .tplinkcloud.certs import get_ca_cert_path
from .tplinkcloud.signing import get_signing_headers

APP_TYPE = "Kasa_Android_Mix"
APP_VER = "3.4.703"
LOGIN_HOST = "https://n-wap.i.tplinkcloud.com"
LOGIN_PATH = "/api/v2/account/login"
USER_AGENT = "Dalvik/2.1.0 (Linux; U; Android 14; Pixel Build/UP1A)"


class TplinkTpapError(Exception):
    """Base error."""


class TplinkTpapAuthError(TplinkTpapError):
    """Login failed (bad credentials or account locked)."""


class TplinkTpapMfaRequired(TplinkTpapError):
    """Login needs a multi-factor code. A code has been sent to the account email."""

    def __init__(self, mfa_email: str | None, mfa_type: int) -> None:
        super().__init__("MFA required")
        self.mfa_email = mfa_email
        self.mfa_type = mfa_type


@dataclass
class TplinkTpapClient:
    """Minimal NBU client: log in, list plugs, read and set TPAP compatibility."""

    email: str
    password: str
    session: aiohttp.ClientSession
    terminal_uuid: str = field(default_factory=lambda: uuid.uuid4().hex.upper())
    _token: str | None = field(default=None, init=False)
    _region: str | None = field(default=None, init=False)
    _app_server: str | None = field(default=None, init=False)
    _ssl: ssl.SSLContext | None = field(default=None, init=False)
    _mfa_process_id: str | None = field(default=None, init=False)
    _mfa_type: int = field(default=1, init=False)

    def _build_ssl(self) -> ssl.SSLContext:
        # Trust the public CAs plus TP-Link's private CA chain (bundled).
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile=get_ca_cert_path())
        return ctx

    async def _ssl_ctx(self) -> ssl.SSLContext:
        # Build off the event loop: create_default_context / load_verify_locations
        # do blocking disk I/O, which Home Assistant forbids inside the loop.
        if self._ssl is None:
            loop = asyncio.get_running_loop()
            self._ssl = await loop.run_in_executor(None, self._build_ssl)
        return self._ssl

    @property
    def _query(self) -> dict[str, str]:
        return {
            "appName": APP_TYPE,
            "appVer": APP_VER,
            "netType": "wifi",
            "termID": self.terminal_uuid,
            "ospf": "Android 14",
            "brand": "TPLINK",
            "locale": "en_US",
            "model": "Pixel",
            "termName": "Pixel",
            "termMeta": "Pixel",
        }

    async def _post_v2(self, path: str, body: dict) -> dict:
        """Signed V2 POST to the login host. Returns the decoded JSON envelope."""
        import json

        body_json = json.dumps(body)
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json;charset=UTF-8",
            **get_signing_headers(body_json, path),
        }
        try:
            async with self.session.post(
                LOGIN_HOST + path,
                data=body_json,
                params=self._query,
                headers=headers,
                ssl=await self._ssl_ctx(),
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise TplinkTpapError(f"cloud request failed: {err}") from err

    def _apply_login_result(self, result: dict) -> None:
        self._token = result["token"]
        self._region = result.get("regionCode", "US")
        self._app_server = self._derive_app_server(result)
        self._mfa_process_id = None

    async def login(self) -> None:
        """Classic V2 login.

        Stores the token on success. If the account challenges with MFA, sends a
        code to the account email and raises TplinkTpapMfaRequired; the caller then
        collects the code and calls submit_mfa_code.
        """
        data = await self._post_v2(
            LOGIN_PATH,
            {
                "appType": APP_TYPE,
                "appVersion": APP_VER,
                "cloudPassword": self.password,
                "cloudUserName": self.email,
                "platform": "Android",
                "refreshTokenNeeded": True,
                "supportBindAccount": False,
                "terminalUUID": self.terminal_uuid,
                "terminalName": "Pixel",
                "terminalMeta": "Pixel",
            },
        )
        if data.get("error_code") != 0:
            raise TplinkTpapError(data.get("msg") or f"login failed ({data.get('error_code')})")
        result = data.get("result") or {}
        if result.get("token"):
            self._apply_login_result(result)
            return
        # MFA challenge: result carries errorCode -20677 plus MFAProcessId.
        if result.get("MFAProcessId") or str(result.get("errorCode")) == "-20677":
            self._mfa_process_id = result.get("MFAProcessId")
            types = result.get("supportedMFATypes") or [1]
            self._mfa_type = types[0] if types else 1
            await self._request_mfa_code()
            raise TplinkTpapMfaRequired(result.get("mfaEmail"), self._mfa_type)
        raise TplinkTpapAuthError(result.get("errorMsg") or "login failed")

    async def _request_mfa_code(self) -> None:
        """Ask the cloud to send the MFA verification code to the account email."""
        await self._post_v2(
            "/api/v2/account/getPushVC4TerminalMFA",
            {
                "appType": APP_TYPE,
                "cloudPassword": self.password,
                "cloudUserName": self.email,
                "locale": "en_US",
                "terminalUUID": self.terminal_uuid,
            },
        )

    async def submit_mfa_code(self, code: str) -> None:
        """Verify the MFA code and bind this terminal so future logins skip MFA."""
        data = await self._post_v2(
            "/api/v2/account/checkMFACodeAndLogin",
            {
                "appType": APP_TYPE,
                "cloudUserName": self.email,
                "code": code.strip(),
                "MFAProcessId": self._mfa_process_id,
                "MFAType": self._mfa_type,
                "supportBindAccount": False,
                "terminalBindEnabled": True,
            },
        )
        if data.get("error_code") != 0:
            raise TplinkTpapError(data.get("msg") or f"MFA failed ({data.get('error_code')})")
        result = data.get("result") or {}
        if not result.get("token"):
            raise TplinkTpapAuthError(result.get("errorMsg") or "invalid MFA code")
        self._apply_login_result(result)

    @staticmethod
    def _derive_app_server(result: dict) -> str:
        # appServerUrlV2 looks like https://n-use1-wap.i.tplinkcloud.com -> prefix use1.
        url = result.get("appServerUrlV2") or result.get("appServerUrl") or ""
        prefix = "use1"
        host = url.split("//", 1)[-1]
        part = host.split("-", 1)
        if len(part) == 2 and part[0] in ("n", "euw1", "use1", "ap1", "use1"):
            prefix = part[1].split("-", 1)[0]
        # fall back to parsing the middle token n-<prefix>-wap
        bits = host.split("-")
        if len(bits) >= 2 and bits[0] == "n":
            prefix = bits[1]
        return f"https://{prefix}-app-server.iot.i.tplinkcloud.com"

    @property
    def app_cid(self) -> str:
        return f"app:{APP_TYPE}:{self.terminal_uuid}"

    def _app_headers(self) -> dict[str, str]:
        if not self._token:
            raise TplinkTpapError("not logged in")
        return {
            "Authorization": f"ut|{self._token}",
            "app-cid": self.app_cid,
            "x-app-name": APP_TYPE,
            "x-app-version": APP_VER,
            "x-term-id": self.terminal_uuid,
            "x-ospf": "Android 14",
            "x-net-type": "wifi",
            "x-strict": "0",
            "x-kasa-canary-user": "true",
            "x-locale": "en_US",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=UTF-8",
        }

    async def _app_request(self, method: str, path: str, json_body=None, ok_404: bool = False):
        import json as _json

        assert self._app_server
        data = _json.dumps(json_body) if json_body is not None else None
        try:
            async with self.session.request(
                method,
                self._app_server + path,
                data=data,
                headers=self._app_headers(),
                ssl=await self._ssl_ctx(),
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise TplinkTpapAuthError("app-server rejected the token")
                if resp.status == 404 and ok_404:
                    return None
                if resp.status >= 400:
                    raise TplinkTpapError(f"{method} {path} -> {resp.status}: {text[:200]}")
                try:
                    return _json.loads(text) if text else {}
                except ValueError:
                    return {}
        except (aiohttp.ClientError, TimeoutError) as err:
            raise TplinkTpapError(f"{method} {path} failed: {err}") from err

    async def get_things(self) -> list[dict]:
        """Return the account's devices (plugs) from the app server."""
        data = await self._app_request("GET", "/v2/things")
        return data.get("data", []) if isinstance(data, dict) else []

    async def get_account_compatibility(self) -> bool | None:
        """Return True if Home Assistant compatibility is on at the account level.

        Read is confirmed by writing the same value back (the POST echoes state);
        a pure GET needs an undiscovered query parameter, so None means unknown.
        """
        return None

    async def set_account_compatibility(self, on: bool) -> bool:
        """Set account-level Home Assistant compatibility. Returns the new state."""
        body = {"homeAssistantCompatibility": "on" if on else "off"}
        data = await self._app_request("POST", "/v1/account/common-config", body)
        value = data.get("homeAssistantCompatibility") if isinstance(data, dict) else None
        return value == "on"

    async def get_device_tpap_preferred(self, thing_name: str) -> bool | None:
        """Read a device's TPAP preference. True = on TPAP (HA-incompatible).

        Returns None when the device has no thirdPartyCompatibility feature (404),
        so such devices are skipped rather than failing the whole setup.
        """
        data = await self._app_request(
            "GET",
            f"/v1/things/{thing_name}/features/thirdPartyCompatibility",
            ok_404=True,
        )
        if isinstance(data, dict) and "tpap_preferred" in data:
            return bool(data["tpap_preferred"])
        return None

    async def set_device_tpap_preferred(self, thing_name: str, preferred: bool) -> None:
        """Per-device preference. preferred=False means HA-compatible protocol is preferred."""
        await self._app_request(
            "PATCH",
            f"/v1/things/{thing_name}/features/thirdPartyCompatibility",
            {"tpap_preferred": preferred},
        )
