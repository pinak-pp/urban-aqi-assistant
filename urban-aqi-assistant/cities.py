"""Curated catalog of Indian cities for the Urban AQI Assistant.

`slug`   : aqicn.org city-page slug usable for keyless live scraping
           (None means the city needs a WAQI token / OpenAQ key for live data).
`coords` : approximate city center (lat, lon) used for OpenAQ station search.
"""

CITIES = [
    # --- Major winter-smog cities (keyless live scraping verified) ---
    {"name": "Delhi", "state": "Delhi", "slug": "delhi", "coords": (28.61, 77.21)},
    {"name": "Mumbai", "state": "Maharashtra", "slug": "mumbai", "coords": (19.08, 72.88)},
    {"name": "Kolkata", "state": "West Bengal", "slug": "kolkata", "coords": (22.57, 88.36)},
    {"name": "Chennai", "state": "Tamil Nadu", "slug": "chennai", "coords": (13.08, 80.27)},
    {"name": "Hyderabad", "state": "Telangana", "slug": "hyderabad", "coords": (17.39, 78.49)},
    {"name": "Kanpur", "state": "Uttar Pradesh", "slug": "kanpur", "coords": (26.45, 80.33)},
    {"name": "Ahmedabad", "state": "Gujarat", "slug": "ahmedabad", "coords": (23.02, 72.57)},
    # --- Cities with an aqicn.org page (live when the city feed is active) ---
    {"name": "Pune", "state": "Maharashtra", "slug": "pune", "coords": (18.52, 73.86)},
    {"name": "Bengaluru", "state": "Karnataka", "slug": "bengaluru", "coords": (12.97, 77.59)},
    {"name": "Lucknow", "state": "Uttar Pradesh", "slug": "lucknow", "coords": (26.85, 80.95)},
    {"name": "Patna", "state": "Bihar", "slug": "patna", "coords": (25.59, 85.14)},
    {"name": "Jaipur", "state": "Rajasthan", "slug": "jaipur", "coords": (26.91, 75.79)},
    {"name": "Ghaziabad", "state": "Uttar Pradesh", "slug": "ghaziabad", "coords": (28.67, 77.42)},
    {"name": "Bhopal", "state": "Madhya Pradesh", "slug": "bhopal", "coords": (23.26, 77.41)},
    {"name": "Nagpur", "state": "Maharashtra", "slug": "nagpur", "coords": (21.15, 79.09)},
    {"name": "Agra", "state": "Uttar Pradesh", "slug": "agra", "coords": (27.18, 78.02)},
    {"name": "Moradabad", "state": "Uttar Pradesh", "slug": "moradabad", "coords": (28.84, 78.77)},
    {"name": "Chandigarh", "state": "Chandigarh", "slug": "chandigarh", "coords": (30.73, 76.78)},
    {"name": "Kochi", "state": "Kerala", "slug": "kochi", "coords": (9.93, 76.27)},
    {"name": "Thiruvananthapuram", "state": "Kerala", "slug": "thiruvananthapuram", "coords": (8.52, 76.94)},
    {"name": "Visakhapatnam", "state": "Andhra Pradesh", "slug": "visakhapatnam", "coords": (17.69, 83.22)},
    {"name": "Srinagar", "state": "Jammu & Kashmir", "slug": "srinagar", "coords": (34.08, 74.80)},
    {"name": "Nashik", "state": "Maharashtra", "slug": "nashik", "coords": (19.99, 73.79)},
    {"name": "Aurangabad", "state": "Maharashtra", "slug": "aurangabad", "coords": (19.88, 75.34)},
    # --- Token-only cities (live data via a free WAQI token or OpenAQ key) ---
    {"name": "Gurugram", "state": "Haryana", "slug": None, "coords": (28.46, 77.03)},
    {"name": "Noida", "state": "Uttar Pradesh", "slug": None, "coords": (28.54, 77.39)},
    {"name": "Faridabad", "state": "Haryana", "slug": None, "coords": (28.41, 77.31)},
    {"name": "Varanasi", "state": "Uttar Pradesh", "slug": None, "coords": (25.32, 82.97)},
    {"name": "Amritsar", "state": "Punjab", "slug": None, "coords": (31.63, 74.87)},
    {"name": "Ludhiana", "state": "Punjab", "slug": None, "coords": (30.90, 75.85)},
    {"name": "Indore", "state": "Madhya Pradesh", "slug": None, "coords": (22.72, 75.86)},
    {"name": "Surat", "state": "Gujarat", "slug": None, "coords": (21.17, 72.83)},
    {"name": "Vijayawada", "state": "Andhra Pradesh", "slug": None, "coords": (16.51, 80.65)},
    {"name": "Coimbatore", "state": "Tamil Nadu", "slug": None, "coords": (11.02, 76.96)},
    {"name": "Mysuru", "state": "Karnataka", "slug": None, "coords": (12.30, 76.64)},
    {"name": "Madurai", "state": "Tamil Nadu", "slug": None, "coords": (9.93, 78.12)},
    {"name": "Guwahati", "state": "Assam", "slug": None, "coords": (26.14, 91.74)},
    {"name": "Dehradun", "state": "Uttarakhand", "slug": None, "coords": (30.32, 78.03)},
    {"name": "Jodhpur", "state": "Rajasthan", "slug": None, "coords": (26.24, 73.02)},
    {"name": "Kota", "state": "Rajasthan", "slug": None, "coords": (25.21, 75.86)},
    {"name": "Bhubaneswar", "state": "Odisha", "slug": None, "coords": (20.30, 85.82)},
    {"name": "Ranchi", "state": "Jharkhand", "slug": None, "coords": (23.34, 85.31)},
    {"name": "Raipur", "state": "Chhattisgarh", "slug": None, "coords": (21.25, 81.63)},
]

CITY_NAMES = [c["name"] for c in CITIES]


def get_city(name):
    for c in CITIES:
        if c["name"].lower() == str(name).lower():
            return c
    return None


def waqi_slug(name):
    """City name form that works well with the WAQI feed API."""
    return str(name).lower().replace(" ", "-")
