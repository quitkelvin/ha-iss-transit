"""ISS Transit: predicts ISS transits of the Sun and Moon near a location."""
from __future__ import annotations

import logging
import os
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .calc import find_transits, parse_location
from .const import (CONF_DAYS, CONF_LOCATION, CONF_MIN_ALTITUDE, CONF_RADIUS, DEFAULT_DAYS, DEFAULT_MIN_ALTITUDE,
                    DEFAULT_RADIUS, DOMAIN, TLE_URL, UPDATE_HOURS)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class IssTransitCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=UPDATE_HOURS))
        self.entry = entry
        self.data_dir = hass.config.path(".storage", DOMAIN)   # de421.bsp (~17 MB, downloaded once) + last TLE
        self._tle: list[str] | None = None

    @property
    def settings(self) -> dict:
        return {**self.entry.data, **self.entry.options}

    async def _fetch_tle(self) -> list[str]:
        try:
            async with async_get_clientsession(self.hass).get(TLE_URL, timeout=30) as r:
                text = await r.text()
            lines = [l for l in text.splitlines() if l.strip()]
            if len(lines) >= 2 and lines[-2].startswith("1 ") and lines[-1].startswith("2 "):
                self._tle = lines[-3:] if len(lines) >= 3 else lines
                await self.hass.async_add_executor_job(self._save_tle)
        except Exception as err:  # noqa: BLE001 – keep the last good TLE
            _LOGGER.warning("ISS TLE download failed: %s", err)
        if self._tle is None:
            self._tle = await self.hass.async_add_executor_job(self._load_tle)
        if not self._tle:
            raise UpdateFailed("no ISS orbit data (TLE) available")
        return self._tle

    def _save_tle(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        with open(os.path.join(self.data_dir, "iss.tle"), "w") as f:
            f.write("\n".join(self._tle))

    def _load_tle(self):
        try:
            with open(os.path.join(self.data_dir, "iss.tle")) as f:
                return f.read().splitlines()
        except OSError:
            return None

    async def _async_update_data(self):
        s = self.settings
        lat, lon = parse_location(s[CONF_LOCATION])
        tle = await self._fetch_tle()
        os.makedirs(self.data_dir, exist_ok=True)
        try:
            transits = await self.hass.async_add_executor_job(
                lambda: find_transits(lat, lon, self.hass.config.elevation or 0, tle, self.data_dir,
                                      float(s.get(CONF_RADIUS, DEFAULT_RADIUS)), float(s.get(CONF_DAYS, DEFAULT_DAYS)),
                                      float(s.get(CONF_MIN_ALTITUDE, DEFAULT_MIN_ALTITUDE))))
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"calculation failed: {err}") from err
        return {"transits": [t.as_dict() for t in transits], "tle_epoch": tle[-2][18:32].strip(), "home": (lat, lon)}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = IssTransitCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
