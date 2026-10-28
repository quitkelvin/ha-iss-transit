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

A transit lasts only about one second and the visible strip is just a few kilometres wide – the coordinates matter,
but they are predictions (see *Accuracy* below).

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
* **Accuracy – all times and positions are estimates.** They have not been validated against measured transits.
  The result can only be as good as the orbit data: TLE/SGP4 predictions drift by kilometres within a few days, and an ISS reboost or
  avoidance manoeuvre can move the centre line by much more than its width. The geometric calculation ignores
  atmospheric refraction, which matters at low Sun/Moon altitudes. Coordinates and times are shown with metre /
  millisecond resolution – that is **not** their precision. Re-check on the day (fresh TLE) and, if possible, compare with a second
  prediction service before you travel.

**Never look at the Sun – with the eye, a camera viewfinder, binoculars or a telescope – without a certified solar filter
in front of the optics.** This integration gives no safety warnings of its own.

## Data sources and their terms

* **CelesTrak** (celestrak.org, operated by Dr. T.S. Kelso) – ISS orbit data (TLE). Free to download; CelesTrak asks
  users to follow its usage policy and updates GP data only every 2 hours, repeated downloads may be blocked (HTTP 403).
  This integration downloads once every 6 hours per configured location and keeps the last good data set if a download
  fails. The orbit data are not part of this repository and are not covered by its MIT licence.
* **NASA/JPL ephemeris DE421** – downloaded once by Skyfield from JPL. Not part of this repository and not covered by its
  MIT licence; JPL's own terms apply.
* **Skyfield** (MIT licence, Brandon Rhodes) – installed by Home Assistant as a Python requirement, not bundled here.

## Disclaimer

Independent hobby project, not affiliated with or endorsed by CelesTrak, NASA/JPL or any space agency. Provided free of
charge "as is", without any warranty (see [LICENSE](LICENSE)); liability is excluded as far as the law permits.
Mandatory statutory liability (e.g. for intent or gross negligence, or for injury to life, body or health) is not
affected. You are responsible for your own safety, for eye protection and for where you travel and stand (traffic,
private land).

**Kurzfassung (DE):** Unabhängiges Hobbyprojekt. Zeiten und Orte sind **Schätzungen** ohne Validierung gegen echte
Transits; Bahndaten (TLE) und ISS-Manöver können die Mittellinie um Kilometer verschieben – am Tag selbst neu prüfen.
**Nie ohne zertifizierten Sonnenfilter vor der Optik in die Sonne schauen.** Bahndaten von CelesTrak (deren
Nutzungsregeln gelten, Abruf hier alle 6 h), Ephemeride DE421 von NASA/JPL – beide nicht Teil dieses Repos und nicht
von der MIT-Lizenz erfasst. Unentgeltlich, ohne Gewährleistung, Haftung ausgeschlossen, soweit gesetzlich zulässig;
zwingende Haftung (Vorsatz, grobe Fahrlässigkeit, Leben/Körper/Gesundheit) bleibt unberührt.

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

MIT for the code in this repository. External data (CelesTrak TLE, JPL DE421) and Skyfield keep their own
terms – see *Data sources and their terms*.
