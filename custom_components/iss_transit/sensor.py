"""Sensors: next ISS transit (timestamp) and number of transits within the radius."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _maps(t: dict) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={t['latitude']},{t['longitude']}"


async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NextTransitSensor(c, entry), TransitCountSensor(c, entry)])


class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="ISS Transit",
                                            entry_type=DeviceEntryType.SERVICE, manufacturer="Celestrak TLE + Skyfield")

    @property
    def _transits(self) -> list[dict]:
        return (self.coordinator.data or {}).get("transits", [])


class NextTransitSensor(_Base):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:space-station"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "next_transit")

    @property
    def native_value(self):
        t = self._transits
        return datetime.fromisoformat(t[0]["time"]) if t else None

    @property
    def extra_state_attributes(self):
        t = self._transits
        attrs = {"transits": [{**x, "maps": _maps(x)} for x in t], "tle_epoch": (self.coordinator.data or {}).get("tle_epoch")}
        if t:
            attrs.update({k: t[0][k] for k in ("body", "distance_km", "bearing_deg", "latitude", "longitude", "half_width_km",
                                                "duration_s", "body_altitude_deg", "body_azimuth_deg", "visible_from_home")})
            attrs["maps"] = _maps(t[0])
        return attrs


class TransitCountSensor(_Base):
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "transit_count")

    @property
    def native_value(self):
        return len(self._transits)
