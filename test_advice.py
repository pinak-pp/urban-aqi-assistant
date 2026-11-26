"""Tests for the advice engine (advice.py)."""
import pytest

import advice
from aqi_data import Reading


def _reading(aqi):
    return Reading(city="Delhi", aqi=aqi, source="waqi", dominant="pm25")


@pytest.mark.parametrize("aqi,expected_tier", [
    (0, "ok"), (30, "ok"), (50, "ok"),
    (51, "usg"), (100, "usg"),
    (101, "bad"), (200, "bad"),
    (201, "vbad"), (428, "vbad"),
])
def test_tier_thresholds(aqi, expected_tier):
    g = advice.build_guidance(_reading(aqi), household=["kids"])
    assert g["tier"] == expected_tier


def test_tier_none_is_treated_as_worst():
    assert advice._tier(None) == "vbad"


def test_guidance_structure_complete():
    g = advice.build_guidance(_reading(160), household=["kids", "asthma"])
    for key in ("tier", "headline", "color", "health_note", "dominant",
                "masks", "ventilation", "outdoor", "routine",
                "indoor_hacks", "low_emission", "watch_for", "sensitive"):
        assert key in g, f"missing guidance key: {key}"
    assert len(g["routine"]) == 3          # morning / afternoon / evening
    assert g["sensitive"]  # household profile adds personalized addenda
    assert all(isinstance(s, str) and s for s in g["routine"]) or \
        all(isinstance(slot, tuple) for slot in g["routine"])


def test_guidance_escalates_with_aqi():
    low = advice.build_guidance(_reading(30), household=[])
    high = advice.build_guidance(_reading(280), household=[])
    # masks advice must get stronger as air gets worse
    assert "not needed" in low["masks"].lower()
    assert "n95" in high["masks"].lower()
    # clean air allows outdoor sport; severe days cancel it
    assert "outdoor sport" in low["outdoor"].lower()
    assert "cancel outdoor sport" in high["outdoor"].lower()
    # ventilation moves from open windows to sealed
    assert "open windows" in low["ventilation"].lower()
    assert "sealed" in high["ventilation"].lower()


def test_household_addenda_only_for_known_groups():
    g = advice.build_guidance(_reading(150), household=["kids", "unknown-group"])
    assert len(g["sensitive"]) == 1  # unknown group ignored safely


def test_watch_for_warning_signs_on_bad_days():
    ok = advice.build_guidance(_reading(30), household=[])
    bad = advice.build_guidance(_reading(190), household=[])
    assert ok["watch_for"] == []
    assert bad["watch_for"]  # escalation guidance present


def test_cpcb_note_mentions_scale():
    note = advice.cpcb_note(160)
    assert "CPCB" in note and "EPA" in note
    # 160 on the CPCB scale falls in 'Moderate' (101-200)
    assert "Moderate" in note


def test_dominant_label_translated():
    r = Reading(city="X", aqi=100, source="waqi", dominant="pm10")
    g = advice.build_guidance(r, household=[])
    assert g["dominant"] == "PM10"


def test_dominant_missing_falls_back_to_hint():
    r = Reading(city="X", aqi=100, source="waqi", dominant="")
    g = advice.build_guidance(r, household=[])
    assert "PM2.5" in g["dominant"]
