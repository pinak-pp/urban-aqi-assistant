# Urban Air Quality Assistant - India

A family-focused web app for beating severe winter smog in Indian cities:
live real-time AQI, pollutant breakdown, personalised low-emission routines
and indoor air hacks.

Built with Python + Streamlit.

## Contributing

This project is open source (MIT license - see `LICENSE`). Contributions are
welcome: adding cities, improving advice, fixing bugs - see `CONTRIBUTING.md`
for setup and the security rules around API keys.

## What it does

- Live air quality for 40+ Indian cities (real-time fetch, 10-minute cache)
- **GPS mode**: "Locate me (GPS)" finds the nearest monitoring stations to
  your actual position - no city picking needed
- Big-picture AQI card with health category and color coding (US EPA scale)
- Pollutant breakdown: PM2.5, PM10, NO2, SO2, CO, O3 sub-indices
- Personalised advice based on your household (young kids, seniors,
  asthma/COPD, pregnancy)
- Today's routine: time-blocked guidance for morning school run, outdoor
  play windows, evening seal-down
- Indoor air hacks: ventilation timing, DIY Corsi-Rosenthal box-fan filter,
  room sealing, purifier strategy
- Low-emission habits your family can adopt
- CPCB vs EPA scale explainer (Indian government advisories use CPCB NAQI)
- Session AQI trend chart from your own readings
- **69 automated tests** + GitHub Actions CI running on every push
- **Accessibility**: ARIA labels, screen-reader live regions, keyboard-focus
  styles on the custom GPS component, theme-aware high-contrast text

## Quick start (local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

69 automated tests cover the data layer (band boundaries, EPA breakpoint
conversion, WAQI geo-feed fallback, aqicn.org page parsing, the fallback
orchestrator, reverse geocoding), the advice engine (tier thresholds,
escalation logic, household addenda) and the city catalog. All tests are
network-free (HTTP is mocked), so they run anywhere in under a second:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -q
```

GitHub Actions (`.github/workflows/tests.yml`) runs the same suite on every
push and pull request - contributors see a green/red check on their PRs.

Opens at http://localhost:8501. No API key needed to start: the app scrapes
live overall AQI from aqicn.org keylessly (verified for major cities), and
falls back to clearly-labeled sample data for other cities.

## Real-time data sources (fallback order)

| Priority | Source | Key | What it gives |
|---|---|---|---|
| 1 | WAQI API (aqicn.org) | free token | overall AQI + full pollutant sub-indices, any city |
| 2 | OpenAQ v3 | free key | official CPCB station PM2.5/PM10 concentrations (converted to EPA AQI) |
| 3 | aqicn.org city page | none | keyless live overall AQI (major cities) |
| 4 | bundled sample data | none | demo values, clearly labeled |

To unlock sources 1 and 2:

- WAQI token (free): https://aqicn.org/data-platform/token/
- OpenAQ key (free): https://explore.openaq.org/register

### Making the keys permanent (recommended, and required for GPS mode)

In the app folder, create a file named `.env` (copy `.env.example`), open it
and paste your keys after the `=` signs:

```
WAQI_TOKEN=paste-your-waqi-token-here
OPENAQ_API_KEY=paste-your-openaq-key-here
```

The app loads it automatically on every start - no re-typing. **There are no
key input fields in the app UI: keys are read server-side only and are never
displayed, echoed or editable from the browser.** When keys are active the
sidebar shows a green "API keys active (server-side)" status line - nothing
more.

`.env` is listed in `.gitignore`, so it will never be committed to git.

The lookup order is: real environment variable -> `.env` file ->
Streamlit Cloud secrets. Alternatives that also work permanently:

- environment variables before launch:
  `export WAQI_TOKEN=... OPENAQ_API_KEY=...` (Windows: `set`)
- on Streamlit Community Cloud: App settings -> Secrets (see below) - the
  right place for deployed apps, since the deployed repo has no `.env`

## Publishing the web app (free, ~10 minutes)

### Option A: Streamlit Community Cloud (recommended, free forever)

1. Create a GitHub repository and push this folder's files
   (`app.py`, `aqi_data.py`, `advice.py`, `cities.py`, `geolocation.py`,
   `components/geolocation/index.html`, `sample_data.json`,
   `requirements.txt`).
   **Do NOT push a `.env` file** - `.gitignore` already blocks it, but
   double-check with `git status` before pushing. Keys belong in Cloud
   secrets (step 4), never in the repo.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click "New app", pick your repo, main file `app.py`, deploy.
4. Add your keys in the app's **Settings -> Secrets** so live data (and GPS
   mode) works for every visitor:

   ```toml
   WAQI_TOKEN = "your-token"
   OPENAQ_API_KEY = "your-key"
   ```

   Secrets live only on Streamlit's servers. They are not part of the repo,
   not visible to visitors, and are never sent to the browser - the app
   reads them with `st.secrets` on the server.

5. You get a permanent public URL like
   `https://<your-app>.streamlit.app` - share it with family and friends.

Notes for the public deployment:
- The keyless live scrape (aqicn.org) works from Streamlit Cloud; verify
  once after deploying.
- With no secrets configured the app still works: keyless live AQI for
  major cities, demo pollutant panel elsewhere. GPS mode, however, needs
  at least one key (it queries nearest stations by coordinates).
- **GPS/Geolocation requires HTTPS** (browsers block it on plain HTTP).
  Streamlit Cloud serves HTTPS automatically, so "Locate me (GPS)" works
  out of the box; localhost also works. The browser asks the user for
  permission, and coordinates are used only within that session.

### Option B: your own server

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

behind nginx/Caddy, or dockerize with
`docker run -p 8501:8501 -v $PWD:/app python:3.12 sh -c "cd /app && pip install -r requirements.txt && streamlit run app.py"`.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI |
| `aqi_data.py` | data layer: WAQI (incl. geo feed), OpenAQ v3, keyless aqicn.org scrape, demo fallback, reverse geocoding, EPA/CPCB bands |
| `advice.py` | advice engine: routines, indoor hacks, masks, ventilation, low-emission habits |
| `cities.py` | curated Indian city catalog (slugs + coordinates) |
| `geolocation.py` + `components/geolocation/` | custom "Locate me (GPS)" Streamlit component |
| `sample_data.json` | demo data (typical severe winter smog day) |

## Privacy & key safety

- API keys are stored server-side only (`.env` locally, Cloud secrets when
  deployed). There is no key input UI, and keys never appear in any page,
  request or error message sent to visitors.
- GPS coordinates are requested by the user's browser with a permission
  prompt, sent to the Streamlit server for that session only, and never
  stored or logged after the session ends.

## Accuracy notes

- WAQI/aqicn.org values use the **US EPA AQI scale**. India's official CPCB
  National AQI uses different breakpoints; the app shows a comparison note.
- Government measures (GRAP stages, school closures) follow CPCB - always
  cross-check official channels on severe days.
- The app is informational and is not medical advice.

## Credits

- World Air Quality Index project (WAQI / aqicn.org) - real-time data, CC-BY
- OpenAQ - aggregation of official Indian monitoring stations (CPCB)
- Streamlit - app framework
