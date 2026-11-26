"""Custom Streamlit component: browser geolocation (GPS).

Renders a "Locate me (GPS)" button. When the user allows location access,
the component returns a dict {latitude, longitude, accuracy, ts} to Python.
No third-party pip package is needed - this talks the Streamlit component
protocol directly.

Notes:
  * Geolocation works on HTTPS sites (and on localhost). Streamlit Cloud
    serves over HTTPS, so the deployed app is fine.
  * Coordinates are only used inside this Streamlit session to find the
    nearest air-quality stations; they are not stored anywhere.
"""
import os

import streamlit.components.v1 as components

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "components", "geolocation")

_component = components.declare_component("geolocation", path=_PATH)


def get_location(key="geolocation"):
    """Return the user's location as a dict, or None until captured.

    The returned value persists across reruns (Streamlit keeps the last
    component value for the same key), so the caller can rely on it
    staying available after the button has been pressed once.
    """
    return _component(default=None, key=key)
