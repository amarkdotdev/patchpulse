"""Database setup and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Database URL from env, default to SQLite for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./patchpulse.db")

# SQLite requires special connection args
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

# Create engine
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

