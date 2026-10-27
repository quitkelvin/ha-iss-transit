"""Config flow for ISS Transit: paste coordinates from Google Maps, choose a radius."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .calc import parse_location
from .const import (CONF_DAYS, CONF_LOCATION, CONF_MIN_ALTITUDE, CONF_RADIUS, DEFAULT_DAYS, DEFAULT_MIN_ALTITUDE,
                    DEFAULT_RADIUS, DOMAIN)


def _schema(d: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_LOCATION, default=d.get(CONF_LOCATION, "")): str,
        vol.Required(CONF_RADIUS, default=d.get(CONF_RADIUS, DEFAULT_RADIUS)): vol.All(vol.Coerce(float), vol.Range(min=1, max=200)),
        vol.Required(CONF_DAYS, default=d.get(CONF_DAYS, DEFAULT_DAYS)): vol.All(vol.Coerce(float), vol.Range(min=1, max=14)),
        vol.Required(CONF_MIN_ALTITUDE, default=d.get(CONF_MIN_ALTITUDE, DEFAULT_MIN_ALTITUDE)): vol.All(vol.Coerce(float), vol.Range(min=0, max=60)),
    })


def _check(user_input: dict) -> dict:
    errors = {}
    try:
        parse_location(user_input[CONF_LOCATION])
    except ValueError:
        errors[CONF_LOCATION] = "invalid_location"
    return errors


class IssTransitConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = _check(user_input)
            if not errors:
                lat, lon = parse_location(user_input[CONF_LOCATION])
                await self.async_set_unique_id(f"{lat:.4f},{lon:.4f}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"ISS Transit ({user_input[CONF_RADIUS]:g} km)", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return IssTransitOptionsFlow()


class IssTransitOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = _check(user_input)
            if not errors:
                return self.async_create_entry(data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(user_input or current), errors=errors)
