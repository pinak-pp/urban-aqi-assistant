"""Data layer for the Urban AQI Assistant.

Fetch order (first success wins, every step logged):
  1. WAQI JSON API   -- needs a free token from https://aqicn.org/api/
                        (full pollutant breakdown for ANY city)
  2. OpenAQ v3 API   -- needs a free key from https://explore.openaq.org/
                        (official CPCB station concentrations, converted to AQI)
  3. aqicn.org page  -- keyless live scraping of the city page
                        (overall AQI + category + temperature; no pollutant detail)
  4. Bundled demo    -- realistic severe-winter sample data, clearly labeled

All indices follow the US EPA AQI scale (0-500), which is what WAQI/aqicn
report. India's official CPCB NAQI uses different breakpoints; see the note
in the app UI.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Urban-AQI-Assistant)"}
IST = timezone(__import__("datetime").timedelta(seconds=5 * 3600 + 1800))

# US EPA AQI bands: (low_aqi, high_aqi, label, hex_color)
EPA_BANDS = [
    (0, 50, "Good", "#00E400"),
    (51, 100, "Moderate", "#FFFF00"),
    (101, 150, "Unhealthy for Sensitive Groups", "#FF7E00"),
    (151, 200, "Unhealthy", "#FF0000"),
    (201, 300, "Very Unhealthy", "#8F3F97"),
    (301, 500, "Hazardous", "#7E0023"),
]

# India's official CPCB National AQI bands (displayed for comparison only)
CPCB_BANDS = [
    (0, 50, "Good", "#009966"),
    (51, 100, "Satisfactory", "#FFDE33"),
    (101, 200, "Moderate", "#FF9933"),
    (201, 300, "Poor", "#FF0066"),
    (301, 400, "Very Poor", "#990099"),
    (401, 500, "Severe", "#7E0023"),
]

POLLUTANT_META = {
    "pm25": {"label": "PM2.5", "desc": "Fine particles (winter smog driver)", "unit": "ug/m3 (AQI sub-index)"},
    "pm10": {"label": "PM10", "desc": "Coarse dust particles", "unit": "ug/m3 (AQI sub-index)"},
    "no2": {"label": "NO2", "desc": "Nitrogen dioxide (traffic)", "unit": "AQI sub-index"},
    "so2": {"label": "SO2", "desc": "Sulphur dioxide (industry)", "unit": "AQI sub-index"},
    "co": {"label": "CO", "desc": "Carbon monoxide", "unit": "AQI sub-index"},
    "o3": {"label": "O3", "desc": "Ground-level ozone", "unit": "AQI sub-index"},
}
POLLUTANT_ORDER = ["pm25", "pm10", "no2", "so2", "co", "o3"]


@dataclass
class Pollutant:
    key: str
    sub_index: float          # AQI sub-index (EPA scale)
    concentration: float = None  # raw value from the source, if known
    unit: str = ""

    @property
    def band(self):
        return band_for(self.sub_index)


@dataclass
class Reading:
    city: str
    aqi: int
    source: str                     # 'waqi' | 'openaq' | 'aqicn' | 'demo'
    source_detail: str = ""
    updated: str = ""
    pollutants: dict = field(default_factory=dict)  # key -> Pollutant
    temperature: str = ""
    dominant: str = ""
    station: str = ""
    notes: list = field(default_factory=list)

    @property
    def band(self):
        return band_for(self.aqi)

    @property
    def is_demo(self):
        return self.source == "demo"


def band_for(aqi):
    if aqi is None:
        return None
    for lo, hi, label, color in EPA_BANDS:
        if lo <= aqi <= hi:
            return {"label": label, "color": color, "lo": lo, "hi": hi}
    return {"label": "Hazardous", "color": "#7E0023", "lo": 301, "hi": 500}


# --------------------------------------------------------------------------
# 0. Reverse geocoding for GPS mode (free OpenStreetMap Nominatim, no key)
# --------------------------------------------------------------------------
from functools import lru_cache


@lru_cache(maxsize=256)
def _reverse_geocode_cached(lat3, lon3):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "json", "lat": lat3, "lon": lon3, "zoom": 10},
            headers={"User-Agent": "Urban-AQI-Assistant/1.0 (educational demo)"},
            timeout=15,
        )
        r.raise_for_status()
        addr = r.json().get("address", {})
    except Exception:
        return None
    place = (addr.get("city") or addr.get("town") or addr.get("village")
             or addr.get("hamlet") or addr.get("county") or "").strip()
    state = (addr.get("state") or "").strip()
    if place and state:
        return f"{place}, {state}"
    return place or state or None


def reverse_geocode(lat, lon):
    """Human-readable label for GPS coordinates (cached, 3-decimal grid)."""
    return _reverse_geocode_cached(round(lat, 3), round(lon, 3))


# --------------------------------------------------------------------------
# 1. WAQI official JSON API (token)
# --------------------------------------------------------------------------
def fetch_waqi(city_name, token, coords=None, session=None):
    """WAQI feed: try the city-name feed first, then the nearest-station
    geo feed (fixes cities like Ranchi that have no feed under their own
    name but do have monitoring stations nearby)."""
    slug = str(city_name).lower().replace(" ", "-")
    urls = [(f"https://api.waqi.info/feed/{slug}/", False)]
    if coords:
        lat, lon = coords
        urls.append((f"https://api.waqi.info/feed/geo:{lat:.4f};{lon:.4f}/", True))
    last_err = None
    for url, is_geo in urls:
        try:
            return _parse_waqi(city_name, url, token, is_geo, session)
        except Exception as e:
            last_err = e
    raise last_err


def _parse_waqi(city_name, url, token, is_geo=False, session=None):
    r = (session or requests).get(url, params={"token": token}, headers=UA, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "ok":
        raise ValueError(f"WAQI: {data.get('data')}")
    d = data["data"]
    if not str(d.get("aqi", "")).isdigit():
        raise ValueError(f"WAQI: station '{d.get('city', {}).get('name', '?')}' "
                         "reports no AQI right now")
    pollutants = {}
    iaqi = d.get("iaqi") or {}
    for key, val in iaqi.items():
        if key in POLLUTANT_META:
            v = val.get("v") if isinstance(val, dict) else val
            if v is not None:
                pollutants[key] = Pollutant(key, float(v))
    dom = d.get("dominantpol") or ("pm25" if "pm25" in pollutants else "")
    t = ""
    try:
        tt = d.get("time", {}).get("s")
        if tt:
            t = datetime.strptime(tt, "%Y-%m-%d %H:%M:%S").astimezone(IST).strftime("%d %b %Y, %H:%M IST")
    except Exception:
        pass
    attrib = ""
    try:
        attrib = d.get("attributions", [{}])[0].get("name", "")
    except Exception:
        pass
    station = d.get("city", {}).get("name", city_name)
    geo_note = f"nearest station to {city_name}: {station}" if is_geo else station
    return Reading(
        city=city_name,
        aqi=int(d.get("aqi")),
        source="waqi",
        source_detail=f"WAQI real-time feed - {geo_note}"
                     f"{(' - ' + attrib) if attrib else ''}",
        updated=t,
        pollutants=pollutants,
        dominant=dom,
        station=station,
        notes=["Full pollutant sub-indices from the official WAQI data feed."
               + (" Station is the closest monitor to the selected city."
                  if is_geo else "")],
    )


# --------------------------------------------------------------------------
# 2. OpenAQ v3 (key) -- CPCB station concentrations converted to EPA AQI
# --------------------------------------------------------------------------
# EPA breakpoints for concentration -> AQI sub-index
EPA_BREAKPOINTS = {
    "pm25": [(0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
             (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 500.4, 301, 500)],
    "pm10": [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150),
             (255, 354, 151, 200), (355, 424, 201, 300), (425, 604, 301, 500)],
}


def _conc_to_aqi(param, conc):
    if param not in EPA_BREAKPOINTS or conc is None:
        return None
    for clow, chigh, ilow, ihigh in EPA_BREAKPOINTS[param]:
        if clow <= conc <= chigh:
            return round((ihigh - ilow) / (chigh - clow) * (conc - clow) + ilow)
    return 500 if conc > EPA_BREAKPOINTS[param][-1][1] else None


def fetch_openaq(city, api_key, session=None):
    s = session or requests
    lat, lon = city["coords"]
    heads = dict(UA, **{"x-api-key": api_key})
    r = s.get("https://api.openaq.org/v3/locations",
              params={"coordinates": f"{lat},{lon}", "radius": 50000, "limit": 5},
              headers=heads, timeout=20)
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise ValueError("OpenAQ: no monitoring stations within 50 km of this city")
    errors = []
    for loc in results[:5]:
        try:
            reading = _openaq_location_reading(loc, city["name"], heads, s)
            if reading:
                return reading
        except Exception as e:
            errors.append(str(e)[:80])
    raise ValueError("OpenAQ: no usable PM readings near this city "
                     f"({'; '.join(errors)})" if errors else
                     "OpenAQ: stations near this city report no PM readings right now")


def _openaq_location_reading(loc, city_name, heads, s):
    sensors = {}
    for sensor in loc.get("sensors", []):
        param = (sensor.get("parameter") or {}).get("name") or sensor.get("parameterId")
        if param:
            sensors[sensor["id"]] = str(param).lower()
    r2 = s.get(f"https://api.openaq.org/v3/locations/{loc['id']}/latest",
               headers=heads, timeout=20)
    r2.raise_for_status()
    pollutants, values = {}, {}
    for row in r2.json().get("results", []):
        param = sensors.get(row.get("sensorsId"))
        if param in ("pm25", "pm1", "pm10"):
            param = "pm25" if param == "pm1" else param
            if param in values:
                continue
            conc = row.get("value")
            values[param] = conc
            aqi_sub = _conc_to_aqi(param, conc)
            if aqi_sub is not None:
                pollutants[param] = Pollutant(param, float(aqi_sub), concentration=conc, unit="ug/m3")
    if not pollutants:
        return None
    overall = max(int(p.sub_index) for p in pollutants.values())
    updated = ""
    try:
        utc = r2.json()["results"][0]["datetime"]["utc"]
        updated = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(IST).strftime("%d %b %Y, %H:%M IST")
    except Exception:
        pass
    return Reading(
        city=city_name,
        aqi=overall,
        source="openaq",
        source_detail=f"OpenAQ - official station: {loc.get('name', 'unnamed')}",
        updated=updated,
        pollutants=pollutants,
        dominant=max(pollutants, key=lambda k: pollutants[k].sub_index),
        station=loc.get("name", ""),
        notes=["PM2.5/PM10 concentrations from official monitoring stations, converted to the US EPA AQI scale."],
    )


# --------------------------------------------------------------------------
# 3. Keyless live scrape of aqicn.org city page
# --------------------------------------------------------------------------
def fetch_aqicn(city, session=None):
    if not city.get("slug"):
        raise ValueError("No keyless aqicn.org page for this city - needs a token")
    url = f"https://aqicn.org/city/{city['slug']}/"
    r = (session or requests).get(url, headers=UA, timeout=20)
    r.raise_for_status()
    body = r.text
    m = re.search(r"id='aqiwgtvalue'[^>]*title=\"([^\"]*)\"[^>]*>([^<]*)<", body)
    if not m:
        raise ValueError("aqicn.org page did not render a live value for this city")
    category, raw = m.group(1).strip(), m.group(2).strip()
    if not raw.isdigit():
        raise ValueError(f"aqicn.org reports 'no data' for this city right now ({raw})")
    aqi = int(raw)
    # the page renders its own human-readable update string; prefer it
    updated = ""
    um = re.search(r"checkWidgetUpdateTime\(\d+,'([^']+)'", body)
    if um:
        updated = " ".join(um.group(1).split()).lstrip("on ").strip()
        # the source mixes 24h time with a stray 'am/pm' suffix - clean it
        updated = re.sub(r"\s+[ap]m\s*$", "", updated, flags=re.I)
        # '25th 2026' -> '25 Nov 2026' (drop English day-ordinal suffixes safely)
        updated = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", updated)
    if not updated:
        epoch = re.search(r"id='aqiwgtutime'[^>]*val='(\d+)'", body)
        if epoch:
            try:
                updated = datetime.fromtimestamp(int(epoch.group(1)), tz=IST).strftime("%d %b %Y, %H:%M IST")
            except Exception:
                pass
    temp = ""
    tm = re.search(r"temp='(\d+)'", body)
    if tm:
        temp = f"{tm.group(1)}C"
    return Reading(
        city=city["name"],
        aqi=aqi,
        source="aqicn",
        source_detail=f"aqicn.org live city page (category: {category})",
        updated=updated,
        pollutants={},
        temperature=temp,
        notes=["Overall city AQI scraped live from aqicn.org. Pollutant detail needs a free WAQI token."],
    )


# --------------------------------------------------------------------------
# 4. Bundled demo data (severe winter smog day, Delhi-like)
# --------------------------------------------------------------------------
def load_demo(city_name):
    with open(os.path.join(HERE, "sample_data.json"), encoding="utf-8") as f:
        d = json.load(f)
    pollutants = {k: Pollutant(k, v["sub_index"], concentration=v.get("concentration"))
                  for k, v in d["pollutants"].items()}
    return Reading(
        city=city_name,
        aqi=d["aqi"],
        source="demo",
        source_detail="DEMO sample data (typical severe winter smog day)",
        updated=d["updated"],
        pollutants=pollutants,
        dominant=d.get("dominant", "pm25"),
        temperature=d.get("temperature", ""),
        notes=["These are sample values for illustration - not live measurements."],
    )


# --------------------------------------------------------------------------
# Orchestrator with graceful fallback
# --------------------------------------------------------------------------
def fetch_reading(city_name, city_meta, waqi_token=None, openaq_key=None, mode="auto"):
    """Try sources in order; returns (Reading, attempts log)."""
    attempts = []
    order = []
    if mode in ("auto", "waqi") and waqi_token:
        order.append("waqi")
    if mode in ("auto", "openaq") and openaq_key:
        order.append("openaq")
    if mode in ("auto", "live"):
        order.append("aqicn")
    if mode == "demo":
        order = []

    for src in order:
        try:
            if src == "waqi":
                return fetch_waqi(city_name, waqi_token,
                                  coords=city_meta.get("coords")), attempts + [("waqi", "ok")]
            if src == "openaq":
                return fetch_openaq(city_meta, openaq_key), attempts + [("openaq", "ok")]
            if src == "aqicn":
                return fetch_aqicn(city_meta), attempts + [("aqicn", "ok")]
        except Exception as e:
            attempts.append((src, str(e)[:120]))

    return load_demo(city_name), attempts + [("demo", "fallback after live sources failed or unavailable")]


if __name__ == "__main__":
    # quick self-test
    import cities as cc
    for name in ["Delhi", "Mumbai", "Pune"]:
        meta = cc.get_city(name)
        try:
            reading, log = fetch_reading(name, meta, mode="live")
            print(name, "->", reading.source, reading.aqi, reading.band["label"], reading.updated, reading.temperature)
        except Exception as e:
            print(name, "ERR", e)
