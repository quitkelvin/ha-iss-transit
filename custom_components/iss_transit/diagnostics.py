"""Diagnostics without the exact location.

The configured location is redacted; it and every centre-line point are only
given rounded to one decimal (about 10 km), so a shared diagnostics file does
not reveal where the user lives.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .calc import parse_location
from .const import CONF_LOCATION, DOMAIN

TO_REDACT = {CONF_LOCATION, "maps"}


def _round(value: Any) -> Any:
    return round(float(value), 1) if isinstance(value, (int, float)) else value


def _rough_location(text: Any) -> list[float] | str:
    try:
        lat, lon = parse_location(str(text))
    except (TypeError, ValueError):
        return "invalid"
    return [_round(lat), _round(lon)]


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return settings and the last calculation with coarse coordinates only."""
    settings = {**entry.data, **entry.options}
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    data = (coordinator.data if coordinator else None) or {}
    transits = [
        {**async_redact_data(t, TO_REDACT), "latitude": _round(t.get("latitude")), "longitude": _round(t.get("longitude"))}
        for t in data.get("transits", [])
    ]
    home = data.get("home")
    return {
        "settings": async_redact_data(settings, TO_REDACT),
        "location_rounded": _rough_location(settings.get(CONF_LOCATION)),
        "home_rounded": [_round(v) for v in home] if home else None,
        "tle_epoch": data.get("tle_epoch"),
        "transits": transits,
    }
