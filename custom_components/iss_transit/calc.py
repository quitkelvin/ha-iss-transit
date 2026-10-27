"""ISS transit finder: when does the ISS cross the Sun or the Moon, and where is the centre line?

Pure computation (no Home Assistant imports) so it can be tested on its own.

Method: for every ISS pass over the home location, the line from the Sun/Moon through the ISS is
intersected with the WGS84 ellipsoid. That intersection traces the transit centre line on the ground.
The point of that line closest to home gives distance, direction and exact coordinates to drive to.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np
from skyfield.api import EarthSatellite, Loader, wgs84
from skyfield.framelib import itrs

WGS84_A = 6378.137
WGS84_B = 6356.752314245
WGS84_E2 = 1 - (WGS84_B / WGS84_A) ** 2
SUN_RADIUS_KM = 696_000.0
MOON_RADIUS_KM = 1_737.4


@dataclass
class Transit:
    time: str              # UTC ISO time of the transit on the centre line (closest point to home)
    body: str              # "sun" or "moon"
    distance_km: float     # home → nearest point of the centre line
    bearing_deg: float     # direction from home to that point
    latitude: float        # nearest centre-line point
    longitude: float
    half_width_km: float   # the transit is visible up to this distance either side of the centre line
    duration_s: float      # time the ISS needs to cross the disc on the centre line
    body_altitude_deg: float
    body_azimuth_deg: float
    iss_range_km: float
    moon_illumination: float | None
    visible_from_home: bool

    def as_dict(self) -> dict:
        return asdict(self)


def parse_location(text: str) -> tuple[float, float]:
    """Accept the format Google Maps copies on right-click: '48.85837, 2.29448' (also with ';' or spaces)."""
    parts = [p for p in text.replace(";", ",").replace(" ", ",").split(",") if p.strip()]
    if len(parts) != 2:
        raise ValueError("expected 'latitude, longitude'")
    lat, lon = float(parts[0]), float(parts[1])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("coordinates out of range")
    return lat, lon


def _haversine(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _bearing(lat1, lon1, lat2, lon2):
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _ground_points(iss_xyz, body_xyz):
    """Intersect the line body → ISS (continued past the ISS) with the WGS84 ellipsoid. Arrays shape (3, n), km, ITRS."""
    d = iss_xyz - body_xyz
    d = d / np.linalg.norm(d, axis=0)
    s = np.array([1.0, 1.0, WGS84_A / WGS84_B])[:, None]           # scale z → sphere of radius a
    p, v = iss_xyz * s, d * s
    a = (v * v).sum(0)
    b = 2 * (p * v).sum(0)
    c = (p * p).sum(0) - WGS84_A ** 2
    disc = b * b - 4 * a * c
    ok = disc >= 0
    t = np.where(ok, (-b - np.sqrt(np.where(ok, disc, 0))) / (2 * a), np.nan)
    ok &= t > 0
    g = iss_xyz + d * t
    lat = np.degrees(np.arctan2(g[2], (1 - WGS84_E2) * np.hypot(g[0], g[1])))
    lon = np.degrees(np.arctan2(g[1], g[0]))
    return np.where(ok, lat, np.nan), np.where(ok, lon, np.nan)


def find_transits(lat: float, lon: float, elevation_m: float, tle: list[str], data_dir: str,
                  radius_km: float = 20.0, days: float = 10.0, min_altitude: float = 5.0, now=None) -> list[Transit]:
    load = Loader(data_dir, verbose=False)
    ts = load.timescale()
    eph = load("de421.bsp")
    earth, bodies = eph["earth"], {"sun": eph["sun"], "moon": eph["moon"]}
    iss = EarthSatellite(tle[-2].strip(), tle[-1].strip(), "ISS", ts)
    home = wgs84.latlon(lat, lon, elevation_m=elevation_m)
    t0 = ts.now() if now is None else ts.from_datetime(now)
    t1 = ts.tt_jd(t0.tt + days)

    # passes seen from home (the centre line within ~radius has practically the same pass)
    times, events = iss.find_events(home, t0, t1, altitude_degrees=0.0)
    passes, rise = [], None
    for t, e in zip(times, events):
        if e == 0:
            rise = t
        elif e == 2 and rise is not None:
            passes.append((rise, t))
            rise = None

    found: list[Transit] = []
    for rise, setting in passes:
        n = max(2, int((setting.tt - rise.tt) * 86400))            # 1 s steps
        tt = ts.tt_jd(np.linspace(rise.tt, setting.tt, n))
        iss_xyz = iss.at(tt).frame_xyz(itrs).km
        for name, body in bodies.items():
            body_xyz = (body - earth).at(tt).frame_xyz(itrs).km
            glat, glon = _ground_points(iss_xyz, body_xyz)
            dist = _haversine(lat, lon, glat, glon)
            if np.all(np.isnan(dist)) or np.nanmin(dist) > radius_km + 30:
                continue
            i = int(np.nanargmin(dist))
            # refine ±2 s in 0.02 s steps
            tf = ts.tt_jd(tt[i].tt + np.arange(-100, 101) * 0.02 / 86400)
            fl, fo = _ground_points(iss.at(tf).frame_xyz(itrs).km, (body - earth).at(tf).frame_xyz(itrs).km)
            fd = _haversine(lat, lon, fl, fo)
            if np.all(np.isnan(fd)):
                continue
            j = int(np.nanargmin(fd))
            if fd[j] > radius_km:
                continue
            tj, plat, plon = tf[j], float(fl[j]), float(fo[j])
            spot = wgs84.latlon(plat, plon)
            alt, az, _ = (earth + spot).at(tj).observe(body).apparent().altaz()
            if alt.degrees < min_altitude:
                continue
            topo = (iss - spot).at(tj)
            rng = topo.distance().km
            body_dist = (body - earth).at(tj).distance().km
            radius_deg = math.degrees(math.asin((SUN_RADIUS_KM if name == "sun" else MOON_RADIUS_KM) / body_dist))
            # angular speed of the ISS seen from the centre line → crossing time of the disc
            a1 = (iss - spot).at(ts.tt_jd(tj.tt - 0.5 / 86400))
            a2 = (iss - spot).at(ts.tt_jd(tj.tt + 0.5 / 86400))
            ang_speed = a1.separation_from(a2).degrees
            illum = None
            if name == "moon":
                from skyfield import almanac
                illum = round(float(almanac.fraction_illuminated(eph, "moon", tj)), 2)
            half_width = math.radians(radius_deg) * rng
            found.append(Transit(
                time=tj.utc_datetime().isoformat(timespec="milliseconds"), body=name,
                distance_km=round(float(fd[j]), 2), bearing_deg=round(_bearing(lat, lon, plat, plon)),
                latitude=round(plat, 5), longitude=round(plon, 5), half_width_km=round(half_width, 2),
                duration_s=round(2 * radius_deg / ang_speed, 2) if ang_speed > 0 else 0.0,
                body_altitude_deg=round(alt.degrees, 1), body_azimuth_deg=round(az.degrees), iss_range_km=round(rng),
                moon_illumination=illum, visible_from_home=bool(fd[j] <= half_width)))
    found.sort(key=lambda x: x.time)
    return found
