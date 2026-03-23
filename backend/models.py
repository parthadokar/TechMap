from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base


class Company(Base):
    __tablename__ = "companies"

    id           = Column(Integer, primary_key=True, index=True)
    osm_id       = Column(String, unique=True, index=True)
    name         = Column(String, nullable=False)
    lat          = Column(Float, nullable=False)
    lon          = Column(Float, nullable=False)
    address      = Column(String, nullable=True)
    phone        = Column(String, nullable=True)
    website      = Column(String, nullable=True)
    email        = Column(String, nullable=True)
    type         = Column(String, nullable=True)  # subtype: software/itsupport/cloud/unknown
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
