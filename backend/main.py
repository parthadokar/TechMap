import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func

import models
import database
import overpass
import nominatim
import github_api

# ---------------------------------------------------------------------------
# Global seeding state
# ---------------------------------------------------------------------------

_seeding = False   # True while a refresh is in progress

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist
    models.Base.metadata.create_all(bind=database.engine)

    # If DB is empty, seed in the background so the server starts immediately
    db = database.SessionLocal()
    try:
        is_empty = db.scalars(select(models.Company)).first() is None
    finally:
        db.close()

    if is_empty:
        print("[startup] DB is empty — phase 1: IT cities, phase 2: full India …")
        asyncio.create_task(_do_seed_staged(database.SessionLocal()))

    yield  # application runs here — API is available immediately


app = FastAPI(title="TechMap API", lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CompanyOut(BaseModel):
    id:      int
    osm_id:  str
    name:    str
    lat:     float
    lon:     float
    address: Optional[str]
    phone:   Optional[str]
    website: Optional[str]
    email:   Optional[str]
    type:    Optional[str]

    model_config = {"from_attributes": True}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upsert_companies(db: Session, companies: list):
    for c in companies:
        existing = db.scalars(
            select(models.Company).where(models.Company.osm_id == c["osm_id"])
        ).first()
        if existing:
            for k, v in c.items():
                setattr(existing, k, v)
        else:
            db.add(models.Company(**c))
    db.commit()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/companies", response_model=List[CompanyOut])
def list_companies(
    type: Optional[str] = Query(None, description="Filter by subtype: software|itsupport|cloud|unknown"),
    db:   Session       = Depends(database.get_db),
):
    stmt = select(models.Company)
    if type:
        stmt = stmt.where(models.Company.type == type)
    return db.scalars(stmt).all()


@app.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(database.get_db)):
    company = db.get(models.Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


async def _do_seed_staged(db: Session):
    """Two-phase startup seed: IT cities first (fast), then full India (comprehensive)."""
    global _seeding
    _seeding = True
    try:
        print(f"[seed] Phase 1 — fetching {len(overpass.IT_CITIES)} IT cities in parallel…")
        cities = await overpass.fetch_it_cities()
        _upsert_companies(db, cities)
        print(f"[seed] Phase 1 done — {len(cities)} companies from IT cities")

        print("[seed] Phase 2 — full India regional sweep…")
        india = await overpass.fetch_companies()
        _upsert_companies(db, india)
        print(f"[seed] Phase 2 done — {len(india)} companies total")
    except Exception as e:
        print(f"[seed] Error: {e}")
    finally:
        _seeding = False
        db.close()


async def _do_refresh(db: Session):
    """Full India refresh (used by /refresh endpoint)."""
    global _seeding
    _seeding = True
    print("[refresh] Full India fetch from Overpass …")
    try:
        companies = await overpass.fetch_companies()
        _upsert_companies(db, companies)
        print(f"[refresh] Upserted {len(companies)} companies.")
    except Exception as e:
        print(f"[refresh] Error: {e}")
    finally:
        _seeding = False
        db.close()


async def _do_refresh_cities(db: Session):
    """IT cities only refresh — much faster than full India."""
    global _seeding
    _seeding = True
    print(f"[refresh/cities] Fetching {len(overpass.IT_CITIES)} IT cities…")
    try:
        companies = await overpass.fetch_it_cities()
        _upsert_companies(db, companies)
        print(f"[refresh/cities] Upserted {len(companies)} companies.")
    except Exception as e:
        print(f"[refresh/cities] Error: {e}")
    finally:
        _seeding = False
        db.close()


async def _do_refresh_metro(db: Session):
    """Metro/Tier 1 cities only — fastest refresh option."""
    global _seeding
    _seeding = True
    print(f"[refresh/metro] Fetching {len(overpass.METRO_CITIES)} metro cities…")
    try:
        companies = await overpass.fetch_metro_cities()
        _upsert_companies(db, companies)
        print(f"[refresh/metro] Upserted {len(companies)} companies.")
    except Exception as e:
        print(f"[refresh/metro] Error: {e}")
    finally:
        _seeding = False
        db.close()


async def _do_refresh_github(db: Session):
    """Fetch Indian tech orgs from GitHub and upsert into DB."""
    global _seeding
    _seeding = True
    print("[refresh/github] Fetching Indian tech orgs from GitHub…")
    try:
        companies = await github_api.fetch_indian_tech_orgs()
        _upsert_companies(db, companies)
        print(f"[refresh/github] Upserted {len(companies)} companies.")
    except Exception as e:
        print(f"[refresh/github] Error: {e}")
    finally:
        _seeding = False
        db.close()


@app.post("/refresh", status_code=202)
async def refresh_companies(background_tasks: BackgroundTasks):
    """Full India refresh from Overpass (~1–2 min)."""
    db = database.SessionLocal()
    background_tasks.add_task(_do_refresh, db)
    return {"status": "full refresh started"}


@app.post("/refresh/cities", status_code=202)
async def refresh_cities(background_tasks: BackgroundTasks):
    """Refresh IT cities only (~30–45s)."""
    db = database.SessionLocal()
    background_tasks.add_task(_do_refresh_cities, db)
    return {"status": f"city refresh started ({len(overpass.IT_CITIES)} cities)"}


@app.post("/refresh/metro", status_code=202)
async def refresh_metro(background_tasks: BackgroundTasks):
    """Refresh metro/Tier 1 cities only — fastest option (~10–15s)."""
    db = database.SessionLocal()
    background_tasks.add_task(_do_refresh_metro, db)
    return {"status": f"metro refresh started ({len(overpass.METRO_CITIES)} cities)"}


@app.post("/refresh/github", status_code=202)
async def refresh_github(background_tasks: BackgroundTasks):
    """Fetch Indian tech orgs from GitHub API and merge into DB."""
    db = database.SessionLocal()
    background_tasks.add_task(_do_refresh_github, db)
    return {"status": "GitHub fetch started — check logs for progress"}


class CityResult(BaseModel):
    companies:     List[CompanyOut]
    bounds:        dict
    center:        dict
    display_name:  str
    fetched:       int


@app.get("/search", response_model=CityResult)
async def search_city(
    city: str     = Query(..., description="City name to search within India"),
    db:   Session = Depends(database.get_db),
):
    """
    Geocode a city via Nominatim, fetch IT companies from Overpass for its
    bounding box, upsert into DB, and return the companies with map bounds.
    """
    location = await nominatim.geocode_city(city)
    if not location:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found in India")

    # Query the DB first — the bulk fetch already covers all of India
    stmt = (
        select(models.Company)
        .where(models.Company.lat >= location["south"])
        .where(models.Company.lat <= location["north"])
        .where(models.Company.lon >= location["west"])
        .where(models.Company.lon <= location["east"])
    )
    city_companies = db.scalars(stmt).all()

    # Only call Overpass if the DB has nothing for this city yet
    fetched = 0
    if not city_companies:
        bbox_str = f"{location['south']},{location['west']},{location['north']},{location['east']}"
        try:
            new_companies = await overpass.fetch_companies_for_bbox(bbox_str)
            _upsert_companies(db, new_companies)
            fetched = len(new_companies)
            city_companies = db.scalars(stmt).all()
        except Exception as e:
            print(f"[search] Overpass unavailable for {city}: {e}")

    return {
        "companies":    city_companies,
        "bounds":       {"south": location["south"], "north": location["north"],
                         "west":  location["west"],  "east":  location["east"]},
        "center":       {"lat": location["lat"], "lon": location["lon"]},
        "display_name": location["display_name"],
        "fetched":      fetched,
    }


@app.delete("/companies", status_code=200)
def delete_all_companies(db: Session = Depends(database.get_db)):
    """Delete all companies from the database."""
    count = db.scalar(select(func.count(models.Company.id)))
    db.query(models.Company).delete()
    db.commit()
    return {"deleted": count}


@app.get("/status")
def status(db: Session = Depends(database.get_db)):
    """Returns current seeding state and total company count."""
    count = db.scalar(select(func.count(models.Company.id)))
    return {"seeding": _seeding, "count": count}


@app.get("/health")
def health():
    return {"ok": True}
