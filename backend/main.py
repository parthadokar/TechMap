import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

import models
import database
import overpass
import nominatim

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
        print("[startup] DB is empty — seeding from Overpass in background …")
        asyncio.create_task(_do_refresh(database.SessionLocal()))

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


async def _do_refresh(db: Session):
    print("[refresh] Fetching from Overpass API …")
    try:
        companies = await overpass.fetch_companies()
        _upsert_companies(db, companies)
        print(f"[refresh] Upserted {len(companies)} companies.")
    except Exception as e:
        print(f"[refresh] Error: {e}")
    finally:
        db.close()


@app.post("/refresh", status_code=202)
async def refresh_companies(background_tasks: BackgroundTasks):
    """Re-fetch from Overpass API and update the SQLite database."""
    db = database.SessionLocal()
    background_tasks.add_task(_do_refresh, db)
    return {"status": "refresh started — check back in ~30 seconds"}


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

    bbox_str = f"{location['south']},{location['west']},{location['north']},{location['east']}"

    # Fetch fresh data for this city — fall back to DB if Overpass is unavailable
    fetched = []
    try:
        fetched = await overpass.fetch_companies_for_bbox(bbox_str)
        _upsert_companies(db, fetched)
    except Exception as e:
        print(f"[search] Overpass unavailable for {city}: {e} — serving from DB")

    # Return all companies within this bbox from DB
    stmt = (
        select(models.Company)
        .where(models.Company.lat >= location["south"])
        .where(models.Company.lat <= location["north"])
        .where(models.Company.lon >= location["west"])
        .where(models.Company.lon <= location["east"])
    )
    city_companies = db.scalars(stmt).all()

    return {
        "companies":    city_companies,
        "bounds":       {"south": location["south"], "north": location["north"],
                         "west":  location["west"],  "east":  location["east"]},
        "center":       {"lat": location["lat"], "lon": location["lon"]},
        "display_name": location["display_name"],
        "fetched":      len(fetched),
    }


@app.get("/health")
def health():
    return {"ok": True}
