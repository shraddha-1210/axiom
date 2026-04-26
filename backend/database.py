import os
from pathlib import Path
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
# Try current directory first, then parent directory
env_path = Path('.env')
if not env_path.exists():
    env_path = Path('../.env')

load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# Handle missing DATABASE_URL or PostgreSQL connection issues
if not DATABASE_URL:
    print("⚠ DATABASE_URL not set, using SQLite fallback")
    DATABASE_URL = "sqlite:///./axiom.db"
elif DATABASE_URL.startswith("postgresql://"):
    # Try PostgreSQL, fallback to SQLite if psycopg2 not available
    try:
        import psycopg2
        print("✓ Using PostgreSQL database")
    except ImportError:
        print("⚠ psycopg2 not installed, using SQLite fallback for local development")
        DATABASE_URL = "sqlite:///./axiom.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AssetRecord(Base):
    __tablename__ = "assets"
    
    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, index=True)
    c2pa_manifest = Column(JSON)
    registered_at = Column(DateTime)
    file_hash = Column(String, unique=True, index=True)

class IncidentRecord(Base):
    __tablename__ = "incidents"
    
    incident_id = Column(String, primary_key=True, index=True)
    asset_id = Column(String, index=True)
    classification = Column(String)
    confidence = Column(String) # Float converted to string for ease
    gemini_report = Column(JSON)
    action_taken = Column(String)

# Initialize schema
Base.metadata.create_all(bind=engine)
