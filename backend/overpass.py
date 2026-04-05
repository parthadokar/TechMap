import asyncio
import httpx
from typing import List, Dict

# Mirrors tried in order — first success wins
OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# Bounding box for India: south, west, north, east
INDIA_BBOX = "6.7,68.1,37.1,97.4"

# Split India into 4 regions fetched in parallel
INDIA_REGIONS = [
    "20.0,68.1,37.1,82.7",  # Northwest
    "20.0,82.7,37.1,97.4",  # Northeast
    "6.7,68.1,20.0,82.7",   # Southwest
    "6.7,82.7,20.0,97.4",   # Southeast
]

# Metro / Tier 1 cities only — smallest set, fastest fetch (~10–15s)
METRO_CITIES: Dict[str, str] = {
    "Bengaluru":  "12.83,77.46,13.14,77.80",
    "Mumbai":     "18.85,72.75,19.27,73.05",
    "Delhi":      "28.40,76.84,28.88,77.35",
    "Hyderabad":  "17.28,78.27,17.54,78.62",
    "Chennai":    "12.90,80.17,13.23,80.31",
    "Pune":       "18.43,73.75,18.63,73.97",
    "Kolkata":    "22.45,88.25,22.65,88.45",
    "Ahmedabad":  "22.95,72.49,23.12,72.70",
    "Noida":      "28.52,77.30,28.65,77.50",
    "Gurgaon":    "28.41,76.99,28.52,77.15",
}

# Major IT cities — bboxes are "south,west,north,east"
# Fetched in parallel at startup before the full India sweep so data arrives fast
IT_CITIES: Dict[str, str] = {
    # ── Tier 1 IT hubs ────────────────────────────────────────────────────────
    "Bengaluru":          "12.83,77.46,13.14,77.80",   # largest IT city
    "Hyderabad":          "17.28,78.27,17.54,78.62",   # HITEC City
    "Pune":               "18.43,73.75,18.63,73.97",   # major IT/ITES hub
    "Mumbai":             "18.85,72.75,19.27,73.05",
    "Delhi":              "28.40,76.84,28.88,77.35",
    "Noida":              "28.52,77.30,28.65,77.50",   # NCR tech corridor
    "Gurgaon":            "28.41,76.99,28.52,77.15",   # Cyber City / DLF
    "Chennai":            "12.90,80.17,13.23,80.31",   # IT/auto hub

    # ── Tier 2 — strong IT presence ───────────────────────────────────────────
    "Kolkata":            "22.45,88.25,22.65,88.45",
    "Ahmedabad":          "22.95,72.49,23.12,72.70",
    "Kochi":              "9.90,76.23,10.07,76.37",    # Infopark / Technopark
    "Coimbatore":         "10.95,76.90,11.05,77.05",
    "Jaipur":             "26.82,75.71,26.96,75.87",
    "Chandigarh":         "30.65,76.72,30.78,76.87",
    "Indore":             "22.65,75.80,22.80,75.95",
    "Bhubaneswar":        "20.22,85.76,20.35,85.88",   # growing IT hub
    "Visakhapatnam":      "17.65,83.18,17.78,83.35",
    "Thiruvananthapuram": "8.45,76.90,8.58,77.05",     # Technopark
    "Nagpur":             "21.08,79.00,21.22,79.15",
    "Mysuru":             "12.25,76.58,12.38,76.72",   # near Bengaluru corridor
    "Lucknow":            "26.77,80.87,26.93,81.05",
    "Mangaluru":          "12.83,74.82,12.93,74.92",

    # ── Emerging IT / good for jobs ───────────────────────────────────────────
    "Surat":              "21.13,72.77,21.25,72.90",
    "Vadodara":           "22.25,73.13,22.40,73.25",
    "Nashik":             "19.97,73.73,20.05,73.83",
    "Bhopal":             "23.18,77.33,23.28,77.47",
    "Guwahati":           "26.10,91.63,26.22,91.82",
    "Patna":              "25.56,85.07,25.65,85.18",
    "Agra":               "27.14,77.95,27.22,78.07",
    "Rajkot":             "22.25,70.73,22.35,70.83",
    "Vijayawada":         "16.47,80.60,16.56,80.72",
    "Madurai":            "9.90,78.08,9.98,78.18",
    "Raipur":             "21.20,81.58,21.30,81.70",
    "Dehradun":           "30.28,77.97,30.38,78.07",
    "Faridabad":          "28.38,77.27,28.45,77.37",   # NCR south
    "Navi Mumbai":        "18.99,73.00,19.12,73.10",
    "Thane":              "19.17,72.95,19.28,73.05",
}

# Regex matches all relevant office types in one Overpass condition
_OFFICE_REGEX = (
    "^(it|software|technology|consulting|engineering|"
    "research|coworking|startup|it_consulting|tech)$"
)


def _build_query(bbox: str) -> str:
    return f"""
[out:json][timeout:90];
(
  node["office"~"{_OFFICE_REGEX}"]["name"]({bbox});
  way["office"~"{_OFFICE_REGEX}"]["name"]({bbox});
);
out center tags;
"""


def _classify(tags: Dict) -> str:
    """Classify a company into: software | itsupport | cloud | unknown"""
    office   = tags.get("office", "").lower()
    name     = tags.get("name", "").lower()
    desc     = tags.get("description", "").lower()
    industry = tags.get("industry", "").lower()
    combined = f"{office} {name} {desc} {industry}"

    cloud_kw = [
        "cloud", "saas", "aws", "azure", "gcp", "hosting", "paas",
        "devops", "kubernetes", "docker", "serverless",
    ]
    support_kw = [
        "support", "msp", "managed", "helpdesk", "repair", "network",
        "infrastructure", "maintenance", "outsourc", "bpo",
    ]
    software_kw = [
        "software", "dev", "development", "solutions", "tech", "digital",
        "app", "web", "code", "systems", "data", "ai", "ml", "analytics",
        "cyber", "security", "erp", "crm", "api", "platform", "startup",
        "fintech", "edtech", "healthtech", "iot", "blockchain",
    ]

    if any(k in combined for k in cloud_kw):
        return "cloud"
    if any(k in combined for k in support_kw):
        return "itsupport"
    if office in ("software", "it", "technology", "engineering", "research",
                  "coworking", "startup", "it_consulting", "tech", "consulting") \
            or any(k in combined for k in software_kw):
        return "software"
    return "unknown"


# Names that are clearly OSM category labels, not real companies
_GENERIC_NAMES = {
    "office", "company", "software", "it", "technology", "tech",
    "solutions", "services", "systems", "digital", "computers",
    "infotech", "information technology", "it company", "it office",
    "software company", "software office", "tech company", "consulting",
    "engineering", "research", "coworking", "startup",
}


def _is_junk(name: str, phone: str, website: str, address: str) -> bool:
    """Drop records that are bare category labels or have absolutely no useful detail."""
    name_lower = name.strip().lower()
    if name_lower in _GENERIC_NAMES:
        return True
    # Keep entries that at least have a non-trivial name even without contact info
    if len(name.strip()) < 3:
        return True
    return False


def _parse_elements(elements: list) -> List[Dict]:
    results = []
    seen: set = set()
    for el in elements:
        if el["type"] == "way":
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
        else:
            lat, lon = el.get("lat"), el.get("lon")

        if lat is None or lon is None:
            continue

        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue

        osm_id = f"{el['type']}/{el['id']}"
        if osm_id in seen:
            continue
        seen.add(osm_id)

        addr_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:suburb", ""),
            tags.get("addr:city", ""),
        ]
        address = ", ".join(p for p in addr_parts if p) or tags.get("addr:full", "")

        phone   = tags.get("phone")   or tags.get("contact:phone")   or None
        website = tags.get("website") or tags.get("contact:website") or None
        email   = tags.get("email")   or tags.get("contact:email")   or None

        if _is_junk(name, phone, website, address):
            continue

        results.append({
            "osm_id":  osm_id,
            "name":    name,
            "lat":     lat,
            "lon":     lon,
            "address": address or None,
            "phone":   phone,
            "website": website,
            "email":   email,
            "type":    _classify(tags),
        })
    return results


async def _post_with_fallback(query: str) -> dict:
    """Try each Overpass mirror in order; retry once per mirror with backoff."""
    last_err: Exception = RuntimeError("No mirrors configured")
    for url in OVERPASS_MIRRORS:
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(url, data={"data": query})
                    resp.raise_for_status()
                    return resp.json()
            except Exception as exc:
                last_err = exc
                if attempt == 0:
                    await asyncio.sleep(2)   # brief pause before retry
        print(f"[overpass] Mirror {url} failed, trying next…")
    raise RuntimeError(f"All Overpass mirrors failed: {last_err}")


async def fetch_companies_for_bbox(bbox: str) -> List[Dict]:
    data = await _post_with_fallback(_build_query(bbox))
    return _parse_elements(data.get("elements", []))


async def fetch_metro_cities() -> List[Dict]:
    """Fetch metro/Tier 1 cities only — fastest option (~10–15s)."""
    city_names = list(METRO_CITIES.keys())
    tasks = [fetch_companies_for_bbox(bbox) for bbox in METRO_CITIES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    seen: set = set()
    all_companies: List[Dict] = []
    for name, result in zip(city_names, results):
        if isinstance(result, Exception):
            print(f"[overpass] Metro city '{name}' failed: {result}")
            continue
        for c in result:
            if c["osm_id"] not in seen:
                seen.add(c["osm_id"])
                all_companies.append(c)
        print(f"[overpass] '{name}' done")

    return all_companies


async def fetch_it_cities() -> List[Dict]:
    """Fetch all IT cities in parallel — fast targeted sweep of major hubs."""
    city_names = list(IT_CITIES.keys())
    tasks = [fetch_companies_for_bbox(bbox) for bbox in IT_CITIES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    seen: set = set()
    all_companies: List[Dict] = []
    for name, result in zip(city_names, results):
        if isinstance(result, Exception):
            print(f"[overpass] City '{name}' failed: {result}")
            continue
        for c in result:
            if c["osm_id"] not in seen:
                seen.add(c["osm_id"])
                all_companies.append(c)
        print(f"[overpass] '{name}' done")

    return all_companies


async def fetch_companies() -> List[Dict]:
    """Fetch all of India by querying 4 regions in parallel — comprehensive sweep."""
    tasks = [fetch_companies_for_bbox(bbox) for bbox in INDIA_REGIONS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    seen: set = set()
    all_companies: List[Dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[overpass] Region {i} failed: {result}")
            continue
        for c in result:
            if c["osm_id"] not in seen:
                seen.add(c["osm_id"])
                all_companies.append(c)

    return all_companies
