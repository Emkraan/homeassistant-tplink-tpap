"""Config and options flow for TP-Link Third-Party Compatibility."""

from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    TplinkTpapAuthError,
    TplinkTpapClient,
    TplinkTpapError,
    TplinkTpapMfaRequired,
)
from .const import CONF_AUTO_HEAL, CONF_TERMINAL_UUID, DEFAULT_AUTO_HEAL, DOMAIN

KASA_ACCOUNT_URL = "https://www.tp-link.com/us/tplink-id/"


class TplinkTpapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._client: TplinkTpapClient | None = None
        self._data: dict[str, Any] = {}

    def _entry_data(self) -> dict[str, Any]:
        return {
            "email": self._data["email"],
            "password": self._data["password"],
            CONF_TERMINAL_UUID: self._data[CONF_TERMINAL_UUID],
        }

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["email"].lower())
            self._abort_if_unique_id_configured()
            terminal_uuid = uuid.uuid4().hex.upper()
            self._data = {
                "email": user_input["email"],
                "password": user_input["password"],
                CONF_TERMINAL_UUID: terminal_uuid,
            }
            self._client = TplinkTpapClient(
                email=user_input["email"],
                password=user_input["password"],
                session=async_get_clientsession(self.hass),
                terminal_uuid=terminal_uuid,
            )
            try:
                await self._client.login()
            except TplinkTpapMfaRequired:
                return await self.async_step_mfa()
            except TplinkTpapAuthError:
                errors["base"] = "invalid_auth"
            except TplinkTpapError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=user_input["email"], data=self._entry_data())

        schema = vol.Schema({vol.Required("email"): str, vol.Required("password"): str})
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"account_url": KASA_ACCOUNT_URL},
        )

    async def async_step_mfa(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and self._client is not None:
            try:
                await self._client.submit_mfa_code(user_input["code"])
            except TplinkTpapAuthError:
                errors["base"] = "invalid_mfa"
            except TplinkTpapError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=self._data["email"], data=self._entry_data())

        return self.async_show_form(
            step_id="mfa",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return TplinkTpapOptionsFlow()


class TplinkTpapOptionsFlow(OptionsFlow):
    """Toggle auto-heal."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_AUTO_HEAL, DEFAULT_AUTO_HEAL)
        schema = vol.Schema({vol.Required(CONF_AUTO_HEAL, default=current): bool})
        return self.async_show_form(step_id="init", data_schema=schema)
