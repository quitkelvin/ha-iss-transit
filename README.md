# ISS Transit for Home Assistant

Predicts when the **International Space Station passes in front of the Sun or the Moon** near you – and tells you
**exactly where to stand**. Other ISS integrations show visible passes; this one computes the transit *centre line* on the
ground and the nearest point to your location, so you can drive there with a camera.

![sensor attributes](https://img.shields.io/badge/no%20API%20key-required-brightgreen)

## What you get

| Entity | State | Attributes |
|---|---|---|
| `sensor.iss_transit_next_transit` | time of the next transit within your radius | `body` (sun/moon), `distance_km` to the centre line, `bearing_deg` (direction to drive), `latitude`/`longitude` of the best spot, `maps` (Google Maps link), `half_width_km` (visible up to this far from the centre line), `duration_s`, `body_altitude_deg`, `body_azimuth_deg`, `visible_from_home`, `transits` (full list) |
| `sensor.iss_transit_transits_within_radius` | number of transits in the look-ahead window | – |

A transit lasts only about one second and the visible strip is just a few kilometres wide – the coordinates matter.

## Setup

1. Install via HACS (custom repository `quitkelvin/ha-iss-transit`, category *Integration*) or copy `custom_components/iss_transit` into your config.
2. Restart Home Assistant, then **Settings → Devices & services → Add integration → ISS Transit**.
3. **Location:** open Google Maps, right-click (long-press on mobile) your spot and click the coordinates at the top – they are copied
   as `48.85837, 2.29448`. Paste them into the form.
4. **Radius:** how far you would travel (default 20 km). **Look-ahead:** 1–14 days (orbit predictions get less precise after a few days;
   the integration recalculates every 6 hours with fresh orbit data). **Minimum altitude:** ignore transits with the Sun/Moon lower than this.

Everything can be changed later under *Configure*. Several locations are possible (one entry each).

## How it works

* Orbit data (TLE) from [CelesTrak](https://celestrak.org), refreshed every 6 h; positions with [Skyfield](https://rhodesmill.org/skyfield/)
  and the JPL ephemeris DE421 (downloaded once, ~17 MB, stored in `.storage/iss_transit`).
* For every ISS pass the line from the Sun/Moon through the ISS is intersected with the WGS84 ellipsoid → transit centre line.
  The point of that line closest to you is reported with time, distance and direction.
* Accuracy: a few hundred metres and ~0.1 s with fresh orbit data. Check again on the day – ISS reboosts shift the track.

**Never look at the Sun without a certified solar filter.**

## Example card (Markdown)

```yaml
type: markdown
content: >
  {% set t = state_attr('sensor.iss_transit_next_transit', 'transits') or [] %}
  {% for x in t %}**{{ as_local(as_datetime(x.time)).strftime('%a %d.%m. %H:%M:%S') }}** ·
  ISS in front of the {{ x.body }} · {{ x.distance_km }} km {{ x.bearing_deg }}° ·
  [map]({{ x.maps }})
  {% else %}No transit within your radius.{% endfor %}
```

## License

MIT. Uses Skyfield (MIT) and CelesTrak orbit data.
