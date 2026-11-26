# Contributing to Urban AQI Assistant

Thanks for your interest in improving air-quality awareness for Indian
families! Contributions of all sizes are welcome.

## Ways to help

- **Report a bug or a data problem** - open an Issue with the city name, what
  you expected, and what you saw (the "Data source log" expander at the
  bottom of the app is very helpful here).
- **Add your city** - edit `cities.py` and add a dict with `name`, `state`,
  `slug` (aqicn.org city-page slug or `None`) and `coords` (lat, lon).
- **Improve advice** - the guidance text lives in `advice.py`; better,
  evidence-based suggestions for smog days are always wanted.
- **Improve the UI** - `app.py` (Streamlit) and
  `components/geolocation/index.html` (GPS component).

## Getting set up locally

```bash
git clone https://github.com/YOUR-USERNAME/urban-aqi-assistant.git
cd urban-aqi-assistant
pip install -r requirements.txt
python -m streamlit run app.py
```

The app runs keyless (overall AQI for major cities + demo data). To unlock
full live data while developing:

1. Copy `.env.example` to `.env`
2. Add your free keys (WAQI: https://aqicn.org/data-platform/token/,
   OpenAQ: https://explore.openaq.org/register)

## Security rules - please read

- **Never commit `.env` or any API key.** `.gitignore` blocks `.env`; if you
  accidentally commit a key, rotate it immediately.
- Keys are only ever loaded server-side. Code that displays, logs or echoes
  keys will not be merged.
- The deployed app's keys live in the maintainer's Streamlit Cloud secrets,
  not in this repository.

## Pull request checklist

- `python -m py_compile app.py aqi_data.py advice.py cities.py geolocation.py`
  passes.
- `pytest tests/ -q` passes (CI runs it automatically on your PR - add a
  test if you change behavior, e.g. new cities or new advice tiers).
- The app still runs: `python -m streamlit run app.py`.
- New user-facing text is simple English (many readers are non-native
  speakers) and works in both light and dark Streamlit themes.
- Custom HTML keeps accessibility: ARIA labels on new tiles, `role="status"`
  live regions for status text, and visible focus states on interactive
  elements.
- Data attributions (WAQI / aqicn.org, OpenAQ) are preserved.

## Data license note

Live air-quality values come from the World Air Quality Index project
(aqicn.org / WAQI, CC-BY) and OpenAQ. If you add a new data source, keep the
attribution visible in the app UI and README.
