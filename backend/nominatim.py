import httpx
from typing import Optional

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


async def geocode_city(city: str) -> Optional[dict]:
    """
    Geocode a city name within India using Nominatim (OSM).
    Returns bounding box + center, or None if not found.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            NOMINATIM_URL,
            params={
                "q": city,
                "format": "json",
                "limit": 1,
                "countrycodes": "in",   # restrict to India
                "addressdetails": 0,
            },
            headers={"User-Agent": "TechMap/1.0 (techmap@local)"},
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        return None

    r = results[0]
    # Nominatim boundingbox order: [south, north, west, east]
    bb = r["boundingbox"]
    south, north, west, east = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])

    # Clamp to India's bbox just in case
    south = max(south, 6.7)
    north = min(north, 37.1)
    west  = max(west,  68.1)
    east  = min(east,  97.4)

    return {
        "south":        south,
        "north":        north,
        "west":         west,
        "east":         east,
        "lat":          float(r["lat"]),
        "lon":          float(r["lon"]),
        "display_name": r.get("display_name", city),
    }
