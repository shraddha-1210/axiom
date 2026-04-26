import os
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

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
