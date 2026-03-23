from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import os
# In Docker the DB lives in /app/data (a named volume) so it persists across restarts.
# Locally it falls back to ./devmap.db as before.
DB_PATH = os.environ.get("DB_PATH", "./devmap.db")
SQLITE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
