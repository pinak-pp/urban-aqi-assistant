"""Tests for the city catalog (cities.py)."""
import cities


def test_catalog_has_40_plus_cities():
    assert len(cities.CITIES) >= 40


def test_city_names_unique():
    names = [c["name"] for c in cities.CITIES]
    assert len(names) == len(set(names)), "duplicate city names in catalog"


def test_every_city_has_required_fields():
    for c in cities.CITIES:
        assert c["name"] and c["state"], c
        lat, lon = c["coords"]
        # inside India's bounding box
        assert 6.0 <= lat <= 36.5, f"{c['name']} latitude out of India: {lat}"
        assert 68.0 <= lon <= 97.5, f"{c['name']} longitude out of India: {lon}"
        # slug is None (token city) or a clean lowercase slug
        slug = c["slug"]
        assert slug is None or (slug == slug.lower() and " " not in slug), c


def test_get_city_roundtrip():
    for c in cities.CITIES[:8]:
        got = cities.get_city(c["name"])
        assert got is not None and got["name"] == c["name"]


def test_get_city_unknown_returns_none():
    assert cities.get_city("Atlantis") is None


def test_city_names_matches_catalog():
    assert sorted(cities.CITY_NAMES) == sorted(c["name"] for c in cities.CITIES)


def test_major_cities_present():
    for must in ("Delhi", "Mumbai", "Kolkata", "Chennai"):
        assert cities.get_city(must), f"{must} missing from catalog"
