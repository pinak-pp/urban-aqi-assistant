"""Urban Air Quality Assistant - India.

A family-focused winter-smog dashboard for Indian cities:
live AQI, pollutant breakdown, personalised routines and indoor air hacks.

Run:  streamlit run app.py
"""
import os
import datetime as dt

import streamlit as st

import aqi_data
import advice
import cities as cc
import geolocation  # custom "Locate me (GPS)" component

st.set_page_config(
    page_title="Urban AQI Assistant - India",
    page_icon="~",
    layout="wide",
)

# --- theme detection (light / dark) ----------------------------------------
def _is_dark_theme():
    try:
        base = (st.context.theme or {}).get("base")
        if base:
            return base == "dark"
    except Exception:
        pass
    try:
        return st.get_option("theme.base") == "dark"
    except Exception:
        return False


IS_DARK = _is_dark_theme()

# palette that adapts to the active Streamlit theme
C = (
    dict(tilebg="#232734", tileborder="#3a3f52", tiletext="#e8eaf0",
         tileh="#f2f4f8", sub="#c3c9d6", legend="#f2f4f8", small="#c3c9d6",
         advicebg="#232734", advicetext="#e8eaf0", na="#8b93a7")
    if IS_DARK else
    dict(tilebg="#f7f8fa", tileborder="#e6e8ec", tiletext="#222222",
         tileh="#111111", sub="#444444", legend="#333333", small="#444444",
         advicebg="#fafafa", advicetext="#222222", na="#666666")
)

# --- minimal styling -----------------------------------------------------
st.markdown(f"""
<style>
    .big-aqi {{ font-size: 76px; font-weight: 800; line-height: 1; }}
    .band-chip {{ display: inline-block; padding: 4px 14px; border-radius: 18px;
                 font-weight: 700; color: #111; }}
    .tile {{ border-radius: 10px; padding: 12px 14px; background: {C['tilebg']};
            border: 1px solid {C['tileborder']}; color: {C['tiletext']}; }}
    .tile h4 {{ margin: 0 0 2px 0; font-size: 15px; color: {C['tileh']}; }}
    .tile p {{ color: {C['tiletext']}; }}
    .tile .val {{ font-size: 26px; font-weight: 800; }}
    .tile .sub {{ font-size: 12px; color: {C['sub']}; font-weight: 600; }}
    .advicebox {{ border-left: 4px solid #888; padding: 8px 14px; margin: 6px 0;
                 background: {C['advicebg']}; border-radius: 0 8px 8px 0; color: {C['advicetext']}; }}
    .demo-warn {{ background: #fff3cd; border: 1px solid #e0c96b; padding: 8px 12px;
                 border-radius: 8px; color: #222; }}
    .legend-num {{ color: {C['legend']}; font-size: 12px; font-weight: 600; }}
    .tile:focus-within {{ outline: 2px solid {C['na']}; }}
    a {{ text-underline-offset: 2px; }}
    :focus-visible {{ outline-offset: 2px; }}
</style>
""", unsafe_allow_html=True)


def readable_on(hex_color):
    """Return dark or white text depending on the background luminance."""
    h = hex_color.lstrip("#")
    r, g_, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    lum = 0.299 * r + 0.587 * g_ + 0.114 * b
    return "#111111" if lum > 140 else "#FFFFFF"


# band-color text variants per theme (lo, hi, light-theme, dark-theme)
BAND_TEXT = [
    (0, 50, "#0B7A3E", "#2BD46A"),      # green
    (51, 100, "#8A6D00", "#FFE45C"),    # amber
    (101, 150, "#C05A00", "#FFA24D"),   # orange
    (151, 200, "#C00000", "#FF7B7B"),   # red
    (201, 300, "#6B2A78", "#CFA0F0"),   # purple
    (301, 500, "#7E0023", "#F08CA6"),   # maroon
]


def band_text_color(aqi):
    for lo, hi, light, dark in BAND_TEXT:
        if aqi is not None and lo <= aqi <= hi:
            return dark if IS_DARK else light
    return "#7E0023"


# --- permanent key loading (.env file / environment / Streamlit secrets) ----
def _load_dotenv():
    """Minimal .env loader (KEY=VALUE lines) - keeps requirements at 2 packages."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(),
                                           val.strip().strip('"').strip("'"))
    except Exception:
        pass


def _get_key(name):
    """Key priority: real environment variable > .env file > Streamlit secrets."""
    val = os.environ.get(name, "")
    if not val:
        try:
            val = str(st.secrets.get(name, ""))
        except Exception:
            val = ""
    return val or ""


_load_dotenv()
env_waqi = _get_key("WAQI_TOKEN")
env_openaq = _get_key("OPENAQ_API_KEY")


@st.cache_data(ttl=600, show_spinner=False)
def get_reading(city_name, slug, coords, waqi_token, openaq_key, mode):
    meta = {"name": city_name, "slug": slug, "coords": coords}
    return aqi_data.fetch_reading(city_name, meta, waqi_token or None,
                                   openaq_key or None, mode)


# --- sidebar --------------------------------------------------------------
st.sidebar.title("Urban AQI Assistant")

st.sidebar.subheader("Location")
loc_mode = st.sidebar.radio(
    "Find my air quality by",
    ["City", "GPS (my location)"],
    index=0,
    help="GPS asks the browser for your coordinates; they are used only in "
         "this session to find the nearest monitoring stations.",
)

gps = None
if loc_mode == "GPS (my location)":
    geolocation.get_location(key="gps")
    gps = st.session_state.get("gps")
else:
    st.session_state.pop("gps", None)

city_label, city = None, None
if loc_mode == "City" or gps is None:
    if loc_mode == "GPS (my location)":
        st.sidebar.info(
            "Tap **Locate me (GPS)** and allow location access. "
            "Your browser may ask for permission.")
    city_label = st.sidebar.selectbox(
        "City",
        cc.CITY_NAMES,
        index=0,
        help="Keyless live data covers major cities; others use the "
             "configured server-side API keys.",
    )
    city = cc.get_city(city_label)

st.sidebar.subheader("Data source")
mode = st.sidebar.radio(
    "Mode",
    ["auto", "live", "waqi", "openaq", "demo"],
    format_func=lambda m: {
        "auto": "Auto (best available)",
        "live": "Live keyless (aqicn.org)",
        "waqi": "WAQI API",
        "openaq": "OpenAQ v3",
        "demo": "Demo data",
    }[m],
    index=0,
)

# Keys are loaded SERVER-SIDE ONLY (environment variables, .env file or
# Streamlit secrets). They are never shown, echoed or editable in the UI.
waqi_token, openaq_key = env_waqi, env_openaq
if env_waqi or env_openaq:
    active = [n for n, v in (("WAQI", env_waqi), ("OpenAQ", env_openaq)) if v]
    st.sidebar.success(f"API keys active (server-side): {', '.join(active)}")
else:
    st.sidebar.caption(
        "No keys configured. Set WAQI_TOKEN / OPENAQ_API_KEY in a local .env "
        "file (see .env.example) or in Streamlit Cloud secrets. "
        "Keys are never displayed in the app.")

st.sidebar.subheader("Your household")
household = st.sidebar.multiselect(
    "Who lives at home?",
    list(advice.HOUSEHOLD_LABELS.keys()),
    format_func=advice.HOUSEHOLD_LABELS.get,
    default=["kids"],
    help="Personalises the health advice.",
)

st.sidebar.caption(
    "Data: WAQI/aqicn.org, OpenAQ (official CPCB monitors). "
    "Informational only - not medical advice."
)

# --- fetch ----------------------------------------------------------------
if gps is not None:
    # GPS mode: reverse-geocode for a friendly label, then query by
    # coordinates (WAQI nearest-station geo feed / OpenAQ station search).
    place = aqi_data.reverse_geocode(gps["latitude"], gps["longitude"]) or "My location"
    st.sidebar.success(
        f"Located: {place}\n\n"
        f"({gps['latitude']:.3f}, {gps['longitude']:.3f} "
        f"± {round(gps.get('accuracy', 0))} m)")
    if not (env_waqi or env_openaq):
        st.sidebar.caption(
            "GPS mode needs at least one server-side key "
            "(WAQI or OpenAQ) for live nearest-station data.")
    fetch_name, fetch_slug, fetch_coords = place, None, (
        round(gps["latitude"], 4), round(gps["longitude"], 4))
else:
    fetch_name, fetch_slug, fetch_coords = (
        city_label, city["slug"], tuple(city["coords"]))

with st.spinner("Fetching live air quality..."):
    reading, attempts = get_reading(fetch_name, fetch_slug, fetch_coords,
                                    waqi_token, openaq_key, mode)

band = reading.band
g = advice.build_guidance(reading, household)

# --- header ----------------------------------------------------------------
st.title("Urban Air Quality Assistant")
st.caption(
    "Beating winter smog, one routine at a time - live AQI, pollutant breakdown, "
    "family-safe schedules and indoor air hacks for Indian cities."
)

# --- source status ----------------------------------------------------------
src_badge = {
    "waqi": ("LIVE - WAQI feed", "#d4edda"),
    "openaq": ("LIVE - OpenAQ station", "#d4edda"),
    "aqicn": ("LIVE - aqicn.org", "#d4edda"),
    "demo": ("DEMO DATA - not live", "#fff3cd"),
}[reading.source]
st.markdown(
    f"<span class='band-chip' style='background:{src_badge[1]}'>{src_badge[0]}</span> "
    f"<small style='color:{C['small']};font-size:13px'>{reading.source_detail} | "
    f"updated {reading.updated or 'n/a'}</small>",
    unsafe_allow_html=True,
)

# --- AQI hero ---------------------------------------------------------------
c1, c2, c3 = st.columns([2, 3, 3])
with c1:
    st.markdown(
        f"<div class='tile' role='group' aria-label='Current air quality for {reading.city}' "
        f"style='border-top:6px solid {band['color']}'>"
        f"<h4>AQI - {reading.city}</h4>"
        f"<div class='big-aqi' role='img' "
        f"aria-label='Air quality index {reading.aqi} of 500, {band['label']}' "
        f"style='color:{band_text_color(reading.aqi)}'>{reading.aqi}</div>"
        f"<span class='band-chip' style='background:{band['color']};"
        f"color:{readable_on(band['color'])}'>{band['label']}</span></div>",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"<div class='tile' role='group' aria-label='Health impact summary'>"
        f"<h4>Health impact</h4>"
        f"<p style='margin:4px 0'>{g['health_note']}</p>"
        f"<p style='margin:4px 0;font-size:12.5px;color:{C['sub']}'>"
        f"Main pollutant today: <b>{g['dominant']}</b></p></div>",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"<div class='tile' role='group' aria-label='Masks and ventilation summary'>"
        f"<h4>At a glance</h4>"
        f"<p style='margin:4px 0'><b>Masks:</b> {g['masks']}</p>"
        f"<p style='margin:4px 0'><b>Ventilation:</b> "
        f"{g['ventilation'].split('.')[0]}.</p></div>",
        unsafe_allow_html=True,
    )

# --- pollutant panel ----------------------------------------------------------
if reading.pollutants:
    if reading.is_demo:
        st.markdown(
            "<div class='demo-warn'><b>Sample pollutant levels shown below (DEMO).</b> "
            "Live pollutant detail needs a server-side WAQI token (set it in .env "
            "or Streamlit secrets - see README), or pick a keyless-live city like "
            "Delhi or Mumbai for the overall AQI.</div>",
            unsafe_allow_html=True,
        )
    st.subheader("Pollutant breakdown (EPA AQI sub-indices)")
    cols = st.columns(3)
    for i, key in enumerate(aqi_data.POLLUTANT_ORDER):
        p = reading.pollutants.get(key)
        meta = aqi_data.POLLUTANT_META[key]
        with cols[i % 3]:
            if p:
                pb = p.band
                pct = min(100, int(100 * p.sub_index / 500))
                conc = (f" | {p.concentration:.0f} ug/m3"
                        if p.concentration else "")
                st.markdown(
                    f"<div class='tile' role='group' aria-label='{meta['label']} level'>"
                    f"<h4>{meta['label']} "
                    f"<small>{meta['desc']}</small></h4>"
                    f"<div class='val' style='color:{band_text_color(p.sub_index)}'>{int(p.sub_index)}</div>"
                    f"<div class='sub'>{pb['label']}{conc}</div>"
                    f"<div style='background:#e8e8e8;border-radius:6px;height:8px;"
                    f"margin-top:6px'><div style='width:{pct}%;height:8px;"
                    f"border-radius:6px;background:{pb['color']}'></div></div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='tile' role='group' aria-label='{meta['label']} not reported'>"
                    f"<h4>{meta['label']}</h4>"
                    f"<div class='val' style='color:{C['na']}'>-</div>"
                    f"<div class='sub'>not reported by this source</div></div>",
                    unsafe_allow_html=True,
                )
else:
    st.info(
        "This source reports the overall AQI only. A server-side WAQI token "
        "(aqicn.org/data-platform/token, set in .env or Streamlit secrets) or an "
        "OpenAQ key unlocks per-pollutant levels; or switch Data source to Demo "
        "to preview the pollutant panel."
    )

# --- AQI scale legend ----------------------------------------------------------
st.markdown("##### Where today sits on the AQI scale (US EPA, 0-500)")
scale = ("<div style='display:flex;border-radius:8px;overflow:hidden;height:26px' "
         f"role='img' aria-label='AQI scale bar from 0 to 500. "
         f"Current reading: {reading.aqi}, {band['label']}.'>")
for lo, hi, label, color in aqi_data.EPA_BANDS:
    w = (hi - lo) / 500 * 100
    scale += f"<div style='width:{w}%;background:{color}'></div>"
scale += "</div><div style='display:flex;margin-top:3px'>"
for lo, hi, label, color in aqi_data.EPA_BANDS:
    scale += f"<div class='legend-num' style='width:{(hi - lo) / 500 * 100:.0f}%'>{lo}-{hi} {label}</div>"
scale += "</div>"
st.markdown(scale, unsafe_allow_html=True)
with st.expander("How this compares with India's official CPCB NAQI scale"):
    st.caption(advice.cpcb_note(reading.aqi))

# --- guidance tabs ----------------------------------------------------------
st.subheader(g["headline"])
tab1, tab2, tab3, tab4 = st.tabs(
    ["Today's routine", "Indoor air hacks", "Masks & ventilation", "Low-emission habits"]
)

with tab1:
    for time_slot, txt in g["routine"]:
        st.markdown(
            f"<div class='advicebox' style='border-color:{g['color']}'>"
            f"<b>{time_slot}</b> &nbsp; {txt}</div>",
            unsafe_allow_html=True,
        )
    if g["sensitive"]:
        st.markdown("**For your household:**")
        for s in g["sensitive"]:
            st.markdown(f"- {s}")

with tab2:
    for h in g["indoor_hacks"]:
        st.markdown(f"- {h}")
    st.markdown(
        f"- <span style='color:{g['color']}'><b>Bedroom purifier rule:</b> "
        f"{ 'run on high 1 hour before bed, low overnight' if g['tier'] in ('bad','vbad') else 'optional tonight' }</span>",
        unsafe_allow_html=True,
    )

with tab3:
    st.markdown(f"**Masks:** {g['masks']}")
    st.markdown(f"**Ventilation:** {g['ventilation']}")
    st.markdown(
        "Winter smog timing: the worst air is usually 6-10 AM (temperature "
        "inversion traps overnight pollution) and again after ~8 PM; the cleanest "
        "stretch is typically 12-4 PM when the mixing layer lifts."
    )
    if g["watch_for"]:
        st.markdown("**Warning signs - see a doctor if:**")
        for w in g["watch_for"]:
            st.markdown(f"- {w}")

with tab4:
    st.caption("Your family's share of the solution:")
    for l in g["low_emission"]:
        st.markdown(f"- {l}")

# --- session history ----------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []
now = dt.datetime.now().strftime("%H:%M")
last = st.session_state.history[-1] if st.session_state.history else None
if last is None or last["time"] != now or last["city"] != reading.city:
    st.session_state.history.append(
        {"time": now, "city": reading.city, "aqi": reading.aqi}
    )
hist = [h for h in st.session_state.history if h["city"] == reading.city]
if len(hist) >= 2 and not reading.is_demo:
    st.markdown("##### AQI trend as seen by you this session")
    st.line_chart({h["time"]: h["aqi"] for h in hist}, height=180)

# --- fetch log ----------------------------------------------------------
with st.expander("Data source log (how this reading was obtained)"):
    for src, msg in attempts:
        st.markdown(f"- `{src}`: {msg}")
    st.caption(
        "Fallback order: WAQI token -> OpenAQ key -> keyless aqicn.org live page "
        "-> bundled demo data. aqicn.org and WAQI data are CC-BY World Air "
        "Quality Index project; OpenAQ aggregates official Indian monitors."
    )

st.button("Refresh now")
