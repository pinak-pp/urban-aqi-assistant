"""Shared pytest fixtures: fake HTTP responses so no test touches the network."""
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# make sure the test run never picks up a real .env with live keys
os.environ.pop("WAQI_TOKEN", None)
os.environ.pop("OPENAQ_API_KEY", None)

import aqi_data  # noqa: E402


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, json_data=None, text="", status_code=200):
        self._json = json_data
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise aqi_data.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def waqi_payload(aqi=150, iaqi=None, station="Test Station"):
    """Build a realistic WAQI API JSON payload."""
    return {
        "status": "ok",
        "data": {
            "aqi": aqi,
            "idx": 12345,
            "city": {"name": station},
            "dominantpol": "pm25",
            "time": {"s": "2026-11-26 08:00:00"},
            "iaqi": iaqi if iaqi is not None else {
                "pm25": {"v": 22.1}, "pm10": {"v": 60}, "no2": {"v": 18},
            },
            "attributions": [{"name": "Test EPA"}],
        },
    }


@pytest.fixture
def waqi_ok(monkeypatch):
    monkeypatch.setattr(
        aqi_data.requests, "get",
        lambda *a, **k: FakeResponse(json_data=waqi_payload()))


@pytest.fixture
def waqi_unknown_station(monkeypatch):
    """First call (city-name feed) fails, like Ranchi; geo feed is tried next."""
    calls = {"n": 0}

    def fake_get(url, *a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(json_data={"status": "error",
                                           "data": "Unknown station"})
        return FakeResponse(json_data=waqi_payload(station="Nearest Station"))

    monkeypatch.setattr(aqi_data.requests, "get", fake_get)
    return calls
