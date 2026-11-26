"""Tests for the data layer (aqi_data.py)."""
import pytest

import aqi_data
from aqi_data import (
    Reading, band_for, _conc_to_aqi, fetch_waqi, fetch_reading,
    fetch_aqicn, reverse_geocode, load_demo,
)
from conftest import FakeResponse, waqi_payload


# ---------------------------------------------------------------- bands
@pytest.mark.parametrize("aqi,expected_label", [
    (0, "Good"), (25, "Good"), (50, "Good"),
    (51, "Moderate"), (100, "Moderate"),
    (101, "Unhealthy for Sensitive Groups"), (150, "Unhealthy for Sensitive Groups"),
    (151, "Unhealthy"), (200, "Unhealthy"),
    (201, "Very Unhealthy"), (300, "Very Unhealthy"),
    (301, "Hazardous"), (428, "Hazardous"), (500, "Hazardous"),
])
def test_band_boundaries(aqi, expected_label):
    assert band_for(aqi)["label"] == expected_label


def test_band_none_returns_none():
    assert band_for(None) is None


def test_bands_have_colors_and_ranges():
    for band in (band_for(10), band_for(160), band_for(400)):
        assert band["color"].startswith("#") and len(band["color"]) == 7
        assert band["lo"] <= band["hi"]


# ------------------------------------------- concentration -> AQI (EPA)
@pytest.mark.parametrize("param,conc,expected", [
    ("pm25", 0.0, 0),
    ("pm25", 12.0, 50),
    ("pm25", 35.0, 99),
    ("pm25", 55.4, 150),
    ("pm25", 150.4, 200),
    ("pm25", 250.4, 300),
    ("pm25", 350.0, 380),      # inside hazardous segment
    ("pm25", 900.0, 500),      # above the table -> capped at 500
    ("pm10", 54, 50),
    ("pm10", 154, 100),
    ("pm10", 254, 150),
    ("pm10", 354, 200),
    ("pm10", 424, 300),
    ("pm10", 700, 500),
    ("pm10", None, None),
    ("no2", 40, None),         # no breakpoints for gases -> None
])
def test_conc_to_aqi(param, conc, expected):
    assert _conc_to_aqi(param, conc) == expected


# ------------------------------------------------------------------ WAQI
def test_fetch_waqi_parses_payload(waqi_ok):
    r = fetch_waqi("Delhi", "tok", coords=(28.61, 77.21))
    assert isinstance(r, Reading)
    assert r.source == "waqi"
    assert r.aqi == 150
    assert r.station == "Test Station"
    assert set(r.pollutants) == {"pm25", "pm10", "no2"}
    assert r.dominant == "pm25"
    assert not r.is_demo
    # sub-indices flow through to bands (22.1 is Good on the EPA scale)
    assert r.pollutants["pm25"].band["label"] == "Good"


def test_fetch_waqi_geo_fallback_after_unknown_station(waqi_unknown_station):
    """Cities like Ranchi have no name feed; the geo feed must be tried next."""
    r = fetch_waqi("Ranchi", "tok", coords=(23.34, 85.31))
    assert r.aqi == 150
    assert r.station == "Nearest Station"
    assert waqi_unknown_station["n"] == 2  # name feed + geo feed


def test_fetch_waqi_geo_only_when_no_coords(monkeypatch):
    calls = []

    def fake_get(url, *a, **k):
        calls.append(url)
        return FakeResponse(json_data={"status": "error", "data": "Unknown station"})

    monkeypatch.setattr(aqi_data.requests, "get", fake_get)
    with pytest.raises(ValueError):
        fetch_waqi("Nowhere", "tok", coords=None)
    assert len(calls) == 1  # no geo feed possible without coords


def test_fetch_waqi_rejects_missing_aqi(monkeypatch):
    payload = waqi_payload(aqi=None)
    monkeypatch.setattr(
        aqi_data.requests, "get",
        lambda *a, **k: FakeResponse(json_data=payload))
    with pytest.raises(ValueError):
        fetch_waqi("Somewhere", "tok")


# ----------------------------------------------------------------- aqicn
def _aqicn_html(aqi="172", updated="2026-11-26 14:00 pm", temp="21"):
    return (
        "<div id='aqiwgtvalue' title=\"Unhealthy\" background='#ff0000'>"
        f"{aqi}</div>"
        "<script>function checkWidgetUpdateTime(123,'"
        f"on 26th Nov 2026, {updated}'</script>"
        f"<span temp='{temp}'></span>"
    )


def test_fetch_aqicn_parses_live_page(monkeypatch):
    monkeypatch.setattr(aqi_data.requests, "get",
                        lambda *a, **k: FakeResponse(text=_aqicn_html()))
    r = fetch_aqicn({"name": "Delhi", "slug": "delhi"})
    assert r.source == "aqicn" and r.aqi == 172
    assert r.temperature == "21C"
    # '26th' -> '26', trailing 'pm' removed
    assert "26th" not in r.updated
    assert not r.updated.lower().endswith("pm")


def test_fetch_aqicn_needs_slug():
    with pytest.raises(ValueError):
        fetch_aqicn({"name": "Ranchi", "slug": None})


def test_fetch_aqicn_rejects_no_data(monkeypatch):
    monkeypatch.setattr(
        aqi_data.requests, "get",
        lambda *a, **k: FakeResponse(text=_aqicn_html(aqi="n/a")))
    with pytest.raises(ValueError):
        fetch_aqicn({"name": "Delhi", "slug": "delhi"})


# ------------------------------------------------------------ orchestrator
def test_fetch_reading_prefers_waqi_then_openaq(monkeypatch):
    calls = []

    def fake_get(url, *a, **k):
        calls.append(url)
        if "api.waqi.info" in url:
            return FakeResponse(json_data=waqi_payload(aqi=95))
        raise AssertionError("OpenAQ should not be called when WAQI succeeded")

    monkeypatch.setattr(aqi_data.requests, "get", fake_get)
    meta = {"name": "Delhi", "slug": "delhi", "coords": (28.61, 77.21)}
    r, log = fetch_reading("Delhi", meta, waqi_token="t", openaq_key="k")
    assert r.source == "waqi" and r.aqi == 95
    assert log[-1] == ("waqi", "ok")


def test_fetch_reading_falls_back_to_demo(monkeypatch):
    def boom(*a, **k):
        raise aqi_data.requests.ConnectionError("network down")

    monkeypatch.setattr(aqi_data.requests, "get", boom)
    meta = {"name": "Ranchi", "slug": None, "coords": (23.34, 85.31)}
    r, log = fetch_reading("Ranchi", meta, waqi_token="t", openaq_key="k")
    assert r.source == "demo" and r.is_demo
    assert [src for src, _ in log] == ["waqi", "openaq", "aqicn", "demo"]
    # failures are logged with a reason, never crash the app
    assert all("network down" in msg for _, msg in log[:2])
    assert "needs a token" in log[2][1]  # Ranchi has no keyless page


def test_fetch_reading_demo_mode_skips_network(monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("demo mode must not touch the network")

    monkeypatch.setattr(aqi_data.requests, "get", no_network)
    meta = {"name": "X", "slug": "x", "coords": (1, 1)}
    r, log = fetch_reading("X", meta, mode="demo")
    assert r.source == "demo" and log == [("demo", "fallback after live sources failed or unavailable")]


# ----------------------------------------------------------- reverse geocode
def test_reverse_geocode_label(monkeypatch):
    monkeypatch.setattr(aqi_data.requests, "get", lambda *a, **k: FakeResponse(
        json_data={"address": {"city": "Ranchi", "state": "Jharkhand"}}))
    assert reverse_geocode(23.344, 85.309) == "Ranchi, Jharkhand"


def test_reverse_geocode_network_failure_returns_none(monkeypatch):
    def boom(*a, **k):
        raise aqi_data.requests.ConnectionError("no net")

    monkeypatch.setattr(aqi_data.requests, "get", boom)
    assert reverse_geocode(10.0, 20.0) is None


# ---------------------------------------------------------------- demo data
def test_load_demo_shape():
    r = load_demo("Anywhere")
    assert r.aqi == 428 and r.source == "demo" and r.is_demo
    assert r.pollutants  # pollutant panel is populated
    assert r.band["label"] == "Hazardous"
