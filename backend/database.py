import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file (current dir then parent)
env_path = Path('.env')
if not env_path.exists():
    env_path = Path('../.env')
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("⚠ DATABASE_URL not set, using SQLite fallback")
    DATABASE_URL = "sqlite:///./axiom.db"
elif DATABASE_URL.startswith("postgresql://"):
    try:
        import psycopg2
        print("✓ Using PostgreSQL database")
    except ImportError:
        print("⚠ psycopg2 not installed, using SQLite fallback for local development")
        DATABASE_URL = "sqlite:///./axiom.db"

# Layer 4: connection resilience
# pool_pre_ping: test every connection before use (detects NeonDB auto-suspends)
# pool_recycle: drop connections older than 5 minutes (NeonDB serverless timeout)
# connect_args: sets a 10-second socket-level connect timeout so health checks fail fast
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 10},
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AssetRecord(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, index=True)
    c2pa_manifest = Column(JSON)
    registered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_hash = Column(String, unique=True, index=True)
    # Layer 3 — Pinecone cross-reference
    embedding_id = Column(String, nullable=True, index=True)


class IncidentRecord(Base):
    __tablename__ = "incidents"

    incident_id = Column(String, primary_key=True, index=True)
    asset_id = Column(String, index=True)
    classification = Column(String)
    confidence = Column(String)          # stored as string for portability
    gemini_report = Column(JSON)         # full structured Gemini output
    action_taken = Column(String)
    # Layer 3 additions
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    layer3_signals = Column(JSON, nullable=True)  # ForensicSignals dict


# Additive schema migration — create_all is safe: adds new columns, never drops existing ones
Base.metadata.create_all(bind=engine)
