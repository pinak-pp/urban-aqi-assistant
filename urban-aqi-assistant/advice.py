"""Advice engine: turns a live AQI reading + household profile into
family-safe routines, indoor air hacks and low-emission habits.

Bands follow the US EPA AQI scale (0-500) that WAQI/aqicn.org report.
"""

from aqi_data import band_for

HOUSEHOLD_LABELS = {
    "kids": "Young children (under 12)",
    "elderly": "Seniors (60+)",
    "asthma": "Asthma / COPD / heart condition",
    "pregnant": "Pregnancy",
    "none": "No sensitive members",
}

SENSITIVE_ADDENDUM = {
    "kids": (
        "Children breathe faster than adults and their lungs are still developing, "
        "so the same smog hits them harder. Keep outdoor play short and supervised, "
        "and watch for night-time coughing."
    ),
    "elderly": (
        "Seniors with heart or lung conditions should treat one band lower as their "
        "personal threshold: act on this advice as if the AQI were one category worse."
    ),
    "asthma": (
        "Keep reliever inhalers accessible for every family member who uses one, "
        "check that they are not empty, and follow the personal action plan agreed "
        "with the doctor on high-pollution days."
    ),
    "pregnant": (
        "During pregnancy, avoid prolonged outdoor exertion on smoggy days; "
        "indoor PM2.5 matters too, so run a purifier in the bedroom at night."
    ),
}

_MASK = {
    "ok": "Masks not needed.",
    "usg": "Optional N95 for sensitive members during long outdoor stretches.",
    "bad": "N95/FFP2 masks for anyone outdoors more than 15-20 minutes "
           "(school run, two-wheeler rides, bus stops).",
    "vbad": "N95/FFP2 mandatory for every necessary outdoor trip. "
            "Surgical or cloth masks filter almost no PM2.5.",
}

_VENTILATION = {
    "ok": "Open windows freely; fresh air is good.",
    "usg": "Ventilate 20-30 minutes in the early afternoon (typically the day's "
           "cleanest window), then close up before the evening smog builds.",
    "bad": "Keep windows mostly shut. If the room feels stale, one short "
           "10-15 minute flush around 2-3 PM, then re-seal.",
    "vbad": "Keep everything sealed: windows, balcony doors, and bathroom/chimney "
            "exhaust vents that let outdoor air leak in. Use AC on recirculate.",
}

_OUTDOOR = {
    "ok": "Great day for the park, cycling and outdoor sport.",
    "usg": "Fine for most families. Sensitive members should keep intense outdoor "
           "exercise short - a walk is fine, a 5 km run is not.",
    "bad": "Everyone should limit prolonged outdoor exertion. Shift sport indoors, "
           "walk shorter school-run legs, avoid evening outdoor play.",
    "vbad": "Cancel outdoor sport and play. Leave the house only when necessary. "
            "School-run by car with windows up, AC on recirculate.",
}

_INDOOR = {
    "ok": "No special indoor measures needed.",
    "usg": "Run any purifier you own in bedrooms at night; wet-mop floors instead "
           "of dry sweeping.",
    "bad": "Run purifiers in the bedroom and the room where the family spends the "
           "evening. If you do not own one, a DIY Corsi-Rosenthal box "
           "(box fan + 4 MERV-13/HEPA filters taped into a cube) costs a fraction "
           "of a branded purifier and moves much more air.",
    "vbad": "Purifiers on high around the clock. Seal window gaps and door bottoms "
            "(weather stripping, door snakes, tape on gaps). Skip incense, candles, "
            "mosquito coils, deep-frying and vacuuming without HEPA - wet-mop instead. "
            "Consider one family room as a 'clean room' where everyone sleeps on the "
            "worst nights.",
}


def _tier(aqi):
    if aqi is None:
        return "vbad"
    if aqi <= 50:
        return "ok"
    if aqi <= 100:
        return "usg"
    if aqi <= 200:
        return "bad"
    return "vbad"


def build_guidance(reading, household):
    """Returns a dict of advice blocks for the current reading."""
    aqi = reading.aqi
    tier = _tier(aqi)
    band = band_for(aqi)
    dom = reading.dominant or ""
    if dom:
        dom_label = {"pm25": "PM2.5", "pm10": "PM10", "no2": "NO2", "so2": "SO2",
                     "co": "CO", "o3": "O3"}.get(dom, dom)
    else:
        dom_label = ("PM2.5 (typical winter smog driver - unverified here; "
                     "live pollutant detail needs a free token)")

    headlines = {
        "ok": "Air is clean today - enjoy the outdoors",
        "usg": "Manageable air, mild precautions for sensitive family members",
        "bad": "Smoggy air - protect the family and cut outdoor time",
        "vbad": "Severe smog - treat outdoor air as an emergency",
    }
    health_notes = {
        "ok": "No health concerns expected at this level.",
        "usg": "Unusually sensitive people may notice mild irritation; most "
               "family members are fine.",
        "bad": "Prolonged exposure can cause coughing, throat and eye irritation, "
               "and can trigger asthma. Reduce time outdoors today.",
        "vbad": "Serious health impact for everyone, not just sensitive groups. "
                "PM2.5 at this level goes deep into lungs and blood. Minimise all "
                "outdoor exposure.",
    }

    routine = {
        "ok": [
            ("6-10 AM", "Normal morning routine; outdoor exercise fine."),
            ("10 AM-5 PM", "Best hours of the day - outdoor play, park time, laundry."),
            ("5-11 PM", "Evening walk or sport is fine."),
        ],
        "usg": [
            ("6-10 AM", "Mornings hold the day's worst smog in winter - keep outdoor "
                        "time short; walk part of the school run if desired."),
            ("12-4 PM", "Cleanest stretch: schedule outdoor play, exercise and "
                        "errands here."),
            ("5-11 PM", "Keep evening outdoor activity light; bedrooms get a purifier "
                        "if anyone is sensitive."),
        ],
        "bad": [
            ("6-10 AM", "Worst inversion hours: school run by the shortest route, "
                        "masks on, no lingering at the gate (idling cars add local PM)."),
            ("12-4 PM", "The only sensible outdoor window: 20-30 minutes of play or "
                        "walking, ideally away from main roads."),
            ("5-11 PM", "Second smog peak: stay in, seal up early, purifiers on."),
        ],
        "vbad": [
            ("6-10 AM", "Hazardous commute: N95 on before opening the door, "
                        "car windows up, AC recirculate, skip the two-wheeler if "
                        "you can."),
            ("12-4 PM", "Even the afternoon dip is bad: outdoor time only if "
                        "essential and under 15 minutes with a mask."),
            ("5-11 PM", "Full seal-down: one 'clean room', everyone sleeps with "
                        "purifiers on high."),
        ],
    }

    low_emission = {
        "ok": [
            "Good day to walk, cycle or take the metro - build the habit for smoggy days.",
            "Combine errands into one car trip instead of several.",
        ],
        "usg": [
            "Metro, bus, carpool or e-rickshaw for the school run and commute.",
            "Never idle the car at the school gate - it exposes every waiting child.",
        ],
        "bad": [
            "Shift the commute: metro/bus or carpool; two-wheelers concentrate "
            "inhaled PM at the worst hour of the day.",
            "Skip the car for short hops; walking in a mask beats driving in traffic.",
            "No wood, crop or trash burning, ever - and no leaf burning in the garden.",
        ],
        "vbad": [
            "Work from home and stagger school pickups if your employer/school allows.",
            "One family member does ALL outdoor errands in one masked trip, "
            "rather than several people going out.",
            "No generators, no burning, no idling - severe days are when local "
            "sources tip the whole neighbourhood over.",
        ],
    }

    indoor_hacks = [_INDOOR[tier]]
    if tier in ("bad", "vbad"):
        indoor_hacks += [
            "DIY air cleaner: a 20-inch box fan + 4 MERV-13 filters taped into a "
            "cube (Corsi-Rosenthal box) costs roughly Rs 3,000-5,000 and out-clean "
            "many small branded purifiers. Build one per 2 rooms.",
            "Bedroom first: family members spend 8 hours there; run a purifier on "
            "high 1 hour before sleep, low overnight.",
            "Kitchen exhaust only while cooking; close the kitchen door so the "
            "exhaust does not drag outdoor air through the house.",
            "Door snakes and weather tape on every gap - a 'sealed' room can hold "
            "PM2.5 50-80% below the street level on bad days.",
        ]
    if tier == "ok":
        indoor_hacks += [
            "Use clean days to air mattresses, quilts and winter clothing, and to "
            "check window seals before the smog season arrives.",
        ]

    watch_for = {
        "ok": [],
        "usg": ["Mild throat irritation in sensitive members is normal; it should "
                "clear indoors."],
        "bad": ["Persistent dry cough, wheezing, chest tightness or unusual "
                "tiredness in a child: see a paediatrician, do not wait it out.",
                "Asthma flare: follow the action plan, use the reliever, and "
                "contact the doctor if night symptoms appear."],
        "vbad": ["Any breathlessness, chest pain, blue lips, confusion in a senior, "
                 "or a child breathing fast at rest: seek medical care immediately.",
                 "Reduce fever-and-cough self-medication - smog symptoms overlap "
                 "with infections, a doctor should look at persistent symptoms."],
    }[tier]

    sensitive = [SENSITIVE_ADDENDUM[k] for k in household if k in SENSITIVE_ADDENDUM]

    return {
        "tier": tier,
        "headline": headlines[tier],
        "color": band["color"],
        "health_note": health_notes[tier],
        "dominant": dom_label,
        "masks": _MASK[tier],
        "ventilation": _VENTILATION[tier],
        "outdoor": _OUTDOOR[tier],
        "routine": routine[tier],
        "indoor_hacks": indoor_hacks,
        "low_emission": low_emission[tier],
        "watch_for": watch_for,
        "sensitive": sensitive,
    }


def cpcb_note(aqi):
    """Short explainer about the difference between the EPA and CPCB scales."""
    for lo, hi, label, _ in __import__("aqi_data").CPCB_BANDS:
        if aqi is not None and lo <= aqi <= hi:
            cpcb = label
            break
    else:
        cpcb = "Severe"
    return (
        f"This number is on the US EPA AQI scale (used by WAQI/aqicn.org). "
        f"India's official CPCB National AQI uses different breakpoints and would "
        f"label the same number '{cpcb}'. School closures, GRAP restrictions and "
        f"government advisories in India follow the CPCB scale - check them "
        f"separately. The health advice above works for the reported EPA value."
    )
