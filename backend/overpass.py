import httpx
from typing import List, Dict

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bounding box for India: south, west, north, east
INDIA_BBOX = "6.7,68.1,37.1,97.4"

QUERY = f"""
[out:json][timeout:180];
(
  node["office"="it"]["name"]({INDIA_BBOX});
  way["office"="it"]["name"]({INDIA_BBOX});
  node["office"="software"]["name"]({INDIA_BBOX});
  way["office"="software"]["name"]({INDIA_BBOX});
  node["office"="technology"]["name"]({INDIA_BBOX});
  way["office"="technology"]["name"]({INDIA_BBOX});
);
out center tags;
"""


def _classify(tags: Dict) -> str:
    """
    Classify a company into a subtype based on OSM tags.

    Returns one of: software | itsupport | cloud | unknown
    """
    office = tags.get("office", "").lower()
    name   = tags.get("name", "").lower()
    desc   = tags.get("description", "").lower()
    combined = f"{office} {name} {desc}"

    cloud_keywords = ["cloud", "saas", "aws", "azure", "gcp", "hosting", "paas"]
    support_keywords = ["support", "msp", "managed", "helpdesk", "repair", "service", "network", "infrastructure"]
    software_keywords = ["software", "dev", "development", "solutions", "tech", "digital", "app", "web", "code", "systems"]

    if any(k in combined for k in cloud_keywords):
        return "cloud"
    if any(k in combined for k in support_keywords):
        return "itsupport"
    if office in ("software", "it", "technology") or any(k in combined for k in software_keywords):
        return "software"
    return "unknown"


def _build_query(bbox: str) -> str:
    return f"""
[out:json][timeout:90];
(
  node["office"="it"]["name"]({bbox});
  way["office"="it"]["name"]({bbox});
  node["office"="software"]["name"]({bbox});
  way["office"="software"]["name"]({bbox});
  node["office"="technology"]["name"]({bbox});
  way["office"="technology"]["name"]({bbox});
);
out center tags;
"""


# Names that are clearly OSM category labels, not real companies
_GENERIC_NAMES = {
    "office", "company", "software", "it", "technology", "tech",
    "solutions", "services", "systems", "digital", "computers",
    "infotech", "information technology", "it company", "it office",
    "software company", "software office", "tech company",
}


def _is_junk(name: str, phone: str, website: str, address: str) -> bool:
    """
    Return True if this record should be dropped.

    Drops when EITHER:
      - The name is a bare generic label (no real identity), OR
      - All three contact/location fields are missing (nothing useful to show)
    """
    name_lower = name.strip().lower()
    is_generic = name_lower in _GENERIC_NAMES

    has_any_detail = any([phone, website, address])

    return is_generic or not has_any_detail


def _parse_elements(elements: list) -> List[Dict]:
    results = []
    seen = set()
    for el in elements:
        if el["type"] == "way":
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
        else:
            lat, lon = el.get("lat"), el.get("lon")

        if lat is None or lon is None:
            continue

        tags  = el.get("tags", {})
        name  = tags.get("name", "").strip()
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

        phone   = tags.get("phone") or tags.get("contact:phone") or None
        website = tags.get("website") or tags.get("contact:website") or None
        email   = tags.get("email") or tags.get("contact:email") or None

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


async def fetch_companies_for_bbox(bbox: str) -> List[Dict]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(OVERPASS_URL, data={"data": _build_query(bbox)})
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    return _parse_elements(elements)


async def fetch_companies() -> List[Dict]:
    return await fetch_companies_for_bbox(INDIA_BBOX)
