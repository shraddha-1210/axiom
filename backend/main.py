from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import json
import base64

from provenance import c2pa_engine
from triage import extract_keyframes, compute_phash_for_frames
from gemini_interrogator import analyze_video_frames_for_fraud
from scrapers import orchestrator

from database import SessionLocal, AssetRecord, IncidentRecord
import vector_store

app = FastAPI(
    title="AXIOM MVP API ($0 Hacker Stack Edition)",
    description="Backend API combining NeonDB, Upstash, Pinecone, Colab, and Gemini.",
    version="2.0.0"
)

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("/tmp/media", exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": os.getenv("ENVIRONMENT")}

@app.post("/api/upload-source")
async def upload_source(asset_id: str, uploader: str, file: UploadFile = File(...)):
    """Layer 1 - Provenance: Secure File Uploads and local C2PA Manifest Signing."""
    filepath = f"/tmp/media/{file.filename}"
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
        
    manifest, signature = c2pa_engine.create_and_sign_manifest(filepath, asset_id, uploader)
    
    # Store manifest in NeonDB PostgreSQL
    db = SessionLocal()
    try:
        new_asset = AssetRecord(
            id=asset_id,
            owner_id=uploader,
            c2pa_manifest=manifest,
            file_hash=manifest["file_sha256"]
        )
        db.add(new_asset)
        db.commit()
    except Exception as e:
        print(f"NeonDB Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    # Mocking Semantic Embedding Generation for Layer 3a
    mock_embedding = [0.1] * 1408
    vector_store.store_embedding(asset_id, mock_embedding)

    return {
        "message": "Source uploaded & signed successfully",
        "manifest": manifest,
        "hsm_signature": signature 
    }

@app.post("/api/triage")
def run_triage(video_filename: str):
    """Layer 2 - pHash: Triage Engine with Redis Cache checking."""
    filepath = f"/tmp/media/{video_filename}"
    frame_dir = f"/tmp/media/frames_{video_filename}"
    
    if not os.path.exists(filepath):
        return {"error": "File not found locally"}

    frames = extract_keyframes(filepath, frame_dir)
    hashes = compute_phash_for_frames(frames)
    
    # Check cache hits
    hits = sum(1 for h in hashes if h.get("is_cached_hit"))
    if hits > 0:
        return {"message": "Direct Copy Match on Triage", "action": "BLOCK", "hits": hits}
        
    return {
        "message": "Triage clear, Escalate to Layer 2.5", 
        "frames_extracted": len(frames),
        "hashes": hashes
    }

@app.post("/api/paligemma")
def run_paligemma(frame_path: str):
    """Layer 2.5 - Local AI validation using Colab Ngrok Endpoint."""
    paligemma_url = os.getenv("PALIGEMMA_URL")
    if not paligemma_url or not os.path.exists(frame_path):
        return {"error": "Config or frame missing"}
        
    with open(frame_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    try:
        # Pinging the Colab backend
        payload = {"image": encoded_string}
        r = requests.post(paligemma_url, json=payload, timeout=5)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": f"Colab request failed: {e}"}

@app.post("/api/interrogate")
def interrogate(asset_id: str, context: str = ""):
    """Layer 3 - Gemini: Interrogation and logging incidents into Neon DB."""
    # Find nearest vector via Pinecone
    nearest = vector_store.search_nearest_assets([0.1]*1408)
    
    gemini_result = analyze_video_frames_for_fraud([], source_context=context)
    
    classification = gemini_result.get("classification", "UNKNOWN")
    confidence = gemini_result.get("confidence", "0.0")
    
    db = SessionLocal()
    try:
        incident = IncidentRecord(
            incident_id=f"inc_{os.urandom(4).hex()}",
            asset_id=asset_id,
            classification=classification,
            confidence=str(confidence),
            gemini_report=gemini_result,
            action_taken=gemini_result.get("recommended_action", "REVIEW")
        )
        db.add(incident)
        db.commit()
    except Exception as e:
        print(f"NeonDB Error: {e}")
        db.rollback()
    finally:
        db.close()

    return {"message": "Interrogation Logged", "gemini_report": gemini_result, "nearest_sematic_match": nearest}

@app.get("/api/scrapers/trigger")
def run_scrapers(background_tasks: BackgroundTasks):
    results = orchestrator.run_all()
    return {"message": "Scraping successfully triggered", "items_found": len(results)}
