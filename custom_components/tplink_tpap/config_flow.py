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

from .api import TplinkTpapAuthError, TplinkTpapClient, TplinkTpapError
from .const import CONF_AUTO_HEAL, CONF_TERMINAL_UUID, DEFAULT_AUTO_HEAL, DOMAIN

KASA_ACCOUNT_URL = "https://www.tp-link.com/us/tplink-id/"


class TplinkTpapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["email"].lower())
            self._abort_if_unique_id_configured()
            terminal_uuid = uuid.uuid4().hex.upper()
            client = TplinkTpapClient(
                email=user_input["email"],
                password=user_input["password"],
                session=async_get_clientsession(self.hass),
                terminal_uuid=terminal_uuid,
            )
            try:
                await client.login()
            except TplinkTpapAuthError:
                errors["base"] = "invalid_auth"
            except TplinkTpapError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input["email"],
                    data={
                        "email": user_input["email"],
                        "password": user_input["password"],
                        CONF_TERMINAL_UUID: terminal_uuid,
                    },
                )

        schema = vol.Schema({vol.Required("email"): str, vol.Required("password"): str})
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"account_url": KASA_ACCOUNT_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return TplinkTpapOptionsFlow()


class TplinkTpapOptionsFlow(OptionsFlow):
    """Toggle auto-heal."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_AUTO_HEAL, DEFAULT_AUTO_HEAL)
        schema = vol.Schema({vol.Required(CONF_AUTO_HEAL, default=current): bool})
        return self.async_show_form(step_id="init", data_schema=schema)
