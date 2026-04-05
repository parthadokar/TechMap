"""
GitHub API integration — finds Indian tech organisations and maps them.

Strategy:
  1. Search GitHub for orgs located in India (up to 1,000 results)
  2. Fetch full details for each org
  3. Resolve their location text → lat/lon via a fast lookup table first,
     then Nominatim as a fallback (rate-limited to 1 req/s)
  4. Return records compatible with the Company model
"""

import asyncio
import os
import re
from typing import Dict, List, Optional, Tuple

import httpx

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = "https://api.github.com"

# Pre-built lat/lon for every city we know — avoids Nominatim calls for the
# vast majority of GitHub location strings.
_CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "bengaluru":        (12.9716, 77.5946),
    "bangalore":        (12.9716, 77.5946),
    "mumbai":           (19.0760, 72.8777),
    "bombay":           (19.0760, 72.8777),
    "delhi":            (28.7041, 77.1025),
    "new delhi":        (28.6139, 77.2090),
    "hyderabad":        (17.3850, 78.4867),
    "chennai":          (13.0827, 80.2707),
    "madras":           (13.0827, 80.2707),
    "pune":             (18.5204, 73.8567),
    "kolkata":          (22.5726, 88.3639),
    "calcutta":         (22.5726, 88.3639),
    "ahmedabad":        (23.0225, 72.5714),
    "noida":            (28.5355, 77.3910),
    "gurgaon":          (28.4595, 77.0266),
    "gurugram":         (28.4595, 77.0266),
    "kochi":            (9.9312,  76.2673),
    "cochin":           (9.9312,  76.2673),
    "coimbatore":       (11.0168, 76.9558),
    "jaipur":           (26.9124, 75.7873),
    "chandigarh":       (30.7333, 76.7794),
    "indore":           (22.7196, 75.8577),
    "bhubaneswar":      (20.2961, 85.8245),
    "visakhapatnam":    (17.6868, 83.2185),
    "vizag":            (17.6868, 83.2185),
    "thiruvananthapuram": (8.5241, 76.9366),
    "trivandrum":       (8.5241,  76.9366),
    "nagpur":           (21.1458, 79.0882),
    "mysuru":           (12.2958, 76.6394),
    "mysore":           (12.2958, 76.6394),
    "lucknow":          (26.8467, 80.9462),
    "mangaluru":        (12.9141, 74.8560),
    "mangalore":        (12.9141, 74.8560),
    "surat":            (21.1702, 72.8311),
    "vadodara":         (22.3072, 73.1812),
    "baroda":           (22.3072, 73.1812),
    "nashik":           (19.9975, 73.7898),
    "bhopal":           (23.2599, 77.4126),
    "guwahati":         (26.1445, 91.7362),
    "patna":            (25.5941, 85.1376),
    "faridabad":        (28.4089, 77.3178),
    "thane":            (19.2183, 72.9781),
    "navi mumbai":      (19.0330, 73.0297),
    "agra":             (27.1767, 78.0081),
    "rajkot":           (22.3039, 70.8022),
    "vijayawada":       (16.5062, 80.6480),
    "madurai":          (9.9252,  78.1198),
    "raipur":           (21.2514, 81.6296),
    "dehradun":         (30.3165, 78.0322),
    "mohali":           (30.7046, 76.7179),
    "panchkula":        (30.6942, 76.8606),
    "kolhapur":         (16.7050, 74.2433),
    "hubli":            (15.3647, 75.1240),
    "dharwad":          (15.4589, 75.0078),
    "warangal":         (17.9784, 79.5941),
    "tiruchirappalli":  (10.7905, 78.7047),
    "trichy":           (10.7905, 78.7047),
    "salem":            (11.6643, 78.1460),
    "tirunelveli":      (8.7139,  77.7567),
    "jabalpur":         (23.1815, 79.9864),
}

# Tokens that mean the location is not a specific Indian city
_SKIP_TOKENS = {
    "india", "remote", "worldwide", "global", "world", "online",
    "distributed", "anywhere", "earth", "internet",
}


def _headers() -> Dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _resolve_location(location: str) -> Optional[Tuple[float, float]]:
    """
    Try to resolve a GitHub location string to (lat, lon) using the lookup
    table. Returns None if the location is ambiguous or outside India.
    """
    if not location:
        return None

    loc = location.lower().strip()

    # Skip vague / non-city locations
    if loc in _SKIP_TOKENS:
        return None

    # Direct match
    if loc in _CITY_COORDS:
        return _CITY_COORDS[loc]

    # Match if any known city appears as a word in the location string
    # e.g. "Bangalore, Karnataka, India" → "bangalore"
    for city, coords in _CITY_COORDS.items():
        pattern = rf"\b{re.escape(city)}\b"
        if re.search(pattern, loc):
            return coords

    return None


async def _search_page(
    client: httpx.AsyncClient, page: int
) -> List[Dict]:
    resp = await client.get(
        f"{BASE_URL}/search/users",
        params={"q": "location:India type:org", "per_page": 100, "page": page},
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


async def _fetch_org(
    client: httpx.AsyncClient,
    login: str,
    sem: asyncio.Semaphore,
) -> Optional[Dict]:
    async with sem:
        try:
            resp = await client.get(
                f"{BASE_URL}/orgs/{login}", headers=_headers()
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None


def _to_company(data: Dict) -> Optional[Dict]:
    name = (data.get("name") or data.get("login", "")).strip()
    if not name or len(name) < 2:
        return None

    coords = _resolve_location(data.get("location") or "")
    if coords is None:
        return None

    lat, lon = coords

    blog = (data.get("blog") or "").strip()
    website = blog if blog.startswith("http") else None

    return {
        "osm_id":  f"github/{data['login']}",
        "name":    name,
        "lat":     lat,
        "lon":     lon,
        "address": data.get("location") or None,
        "phone":   None,
        "website": website,
        "email":   data.get("email") or None,
        "type":    "software",   # GitHub orgs are tech by definition
    }


async def fetch_indian_tech_orgs() -> List[Dict]:
    """
    Main entry point — returns company dicts ready for DB upsert.
    """
    if not GITHUB_TOKEN:
        print("[github] No GITHUB_TOKEN set — skipping (rate limit: 60 req/hr)")
        return []

    # ── 1. Collect org logins via search (max 10 pages × 100 = 1,000) ────────
    logins: List[str] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        for page in range(1, 11):
            try:
                items = await _search_page(client, page)
                if not items:
                    break
                logins.extend(i["login"] for i in items)
                print(f"[github] Search page {page}: {len(items)} orgs")
                if len(items) < 100:
                    break
                await asyncio.sleep(0.5)   # stay within secondary rate limits
            except Exception as e:
                print(f"[github] Search page {page} error: {e}")
                break

    print(f"[github] Total orgs found: {len(logins)}")

    # ── 2. Fetch org details concurrently (max 20 in flight at once) ─────────
    sem = asyncio.Semaphore(20)
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [_fetch_org(client, login, sem) for login in logins]
        raw = await asyncio.gather(*tasks)

    # ── 3. Resolve locations + build company records ──────────────────────────
    companies: List[Dict] = []
    for data in raw:
        if data is None:
            continue
        company = _to_company(data)
        if company:
            companies.append(company)

    print(f"[github] Resolved {len(companies)} companies with Indian city locations")
    return companies
