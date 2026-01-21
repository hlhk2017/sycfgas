"""Config flow for Sanya Changfeng Gas integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .api_client import SycfgasAPIClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("meter_uuid"): str,
        vol.Required("user_token"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api_client = SycfgasAPIClient(
        meter_uuid=data["meter_uuid"],
        user_token=data["user_token"],
    )

    try:
        # Test connection by querying account info
        account_info = await api_client.get_account_info()
        if not account_info or account_info.get("responseCode") != "100000":
            raise InvalidAuth

        result = account_info.get("result", {})
        meter_info = result.get("meterInfo", {})
        user_name = meter_info.get("custName", "未知用户")
        meter_no = meter_info.get("meterList", [{}])[0].get("meterNo", data["meter_uuid"][:12])

        return {
            "title": "三亚长丰燃气",
            "meter_uuid": data["meter_uuid"],
            "user_token": data["user_token"],
            "user_name": user_name,
            "meter_no": meter_no,
        }
    except Exception as err:
        _LOGGER.exception("Unexpected exception during validation")
        if isinstance(err, (InvalidAuth, CannotConnect)):
            raise
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sanya Changfeng Gas."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_SCHEMA
            )

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Use meter_uuid as unique_id
            await self.async_set_unique_id(user_input["meter_uuid"])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=info["title"],
                data={
                    "meter_uuid": user_input["meter_uuid"],
                    "user_token": user_input["user_token"],
                    "user_name": info.get("user_name"),
                    "meter_no": info.get("meter_no"),
                },
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
