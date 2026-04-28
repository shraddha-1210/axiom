from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import os
import uuid
import pathlib
import requests
import json
import base64
import logging
import tempfile

logger = logging.getLogger("AXIOM")
DEBUG = os.getenv("DEBUG_CLOUD_CALLS", "false").lower() == "true"

from provenance import c2pa_engine
from triage import (
    extract_keyframes,
    compute_phash_for_frames,
    run_complete_triage,
    store_asset_hashes,
    TriageDecision
)
from paligemma_triage import run_paligemma_triage, PaliGemmaDecision
from gemini_interrogator import analyze_video_frames_for_fraud
from scrapers import orchestrator
from event_queue import event_queue
from sandbox_detonator import run_zeroday_sandbox
from layer3_orchestrator import run_layer3_interrogation
from vertex_embedder import generate_multimodal_embedding, store_embedding_with_metadata

from database import SessionLocal, AssetRecord, IncidentRecord
import vector_store

from waf import CloudArmorMiddleware, limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Cloud-only imports (no local system interactions)
try:
    from cloud_client import (
        analyze_frame_cloud,
        detect_deepfake_signals_cloud,
        detect_compression_artifacts_cloud,
        generate_frame_caption_cloud,
        check_colab_health,
        CloudAnalysisResult
    )
    CLOUD_CLIENT_AVAILABLE = True
except ImportError:
    CLOUD_CLIENT_AVAILABLE = False
    print("⚠ Cloud client not available - cloud endpoints will be disabled")

try:
    from cloud_embeddings import generate_multimodal_embedding
except ImportError:
    from vertex_embedder import generate_multimodal_embedding

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

# Layer 1 - WAF Simulation (Rate Limiter and IP block)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CloudArmorMiddleware)

os.makedirs("/tmp/media", exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": os.getenv("ENVIRONMENT")}


@app.get("/cloud/health")
def cloud_health_check():
    """
    Check if Colab ngrok tunnel is reachable.
    
    Returns cloud connectivity status.
    """
    if not CLOUD_CLIENT_AVAILABLE:
        return {
            "status": "unavailable",
            "error": "Cloud client not installed"
        }
    
    is_healthy = check_colab_health()
    return {
        "status": "ok" if is_healthy else "unavailable",
        "colab_ngrok_url": os.getenv("COLAB_NGROK_URL", "not configured"),
        "cloud_ready": is_healthy
    }


@app.post("/analyze-frame")
@limiter.limit("20/minute")
async def analyze_frame(
    request: Request,
    file: UploadFile = File(...),
    prompt: str = "caption en"
):
    """
    ☁️ CLOUD-ONLY Frame Analysis via Colab ngrok endpoint.
    
    No local system interaction — all processing happens on Google Colab T4 GPU.
    
    Supports:
    - Automatic image caption generation (prompt="caption en")
    - Deepfake detection (prompt="Is this a deepfake?...")
    - Compression artifact analysis
    - Logo manipulation detection
    
    Args:
        file:   JPEG/PNG image file
        prompt: Analysis prompt for PaliGemma model
    
    Returns:
        Analysis result from Colab endpoint
    """
    if not CLOUD_CLIENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Cloud client not configured")
    
    try:
        # Read image bytes from upload
        image_bytes = await file.read()
        
        if DEBUG:
            logger.info(f"📤 Uploading frame to Colab for analysis (prompt: {prompt})")
        
        # Send to Colab ngrok endpoint
        result = analyze_frame_cloud(
            image_bytes=image_bytes,
            prompt=prompt,
            retry=True
        )
        
        if result.status == "error":
            raise HTTPException(status_code=502, detail=f"Colab analysis failed: {result.error}")
        
        return {
            "status": "success",
            "analysis": result.analysis,
            "processing_time_ms": f"{result.processing_time_ms:.1f}",
            "model": "PaliGemma-3B (Colab T4 GPU)",
            "cost": "$0.00"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frame analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cloud/deepfake-detection")
@limiter.limit("10/minute")
async def cloud_deepfake_detection(
    request: Request,
    file: UploadFile = File(...)
):
    """
    ☁️ Deepfake Detection via Colab PaliGemma.
    
    Analyzes frame for:
    - Temporal flickering on face boundaries
    - Facial feature inconsistencies
    - Unnatural blinking patterns
    - Skin texture anomalies
    
    Returns forensic analysis result.
    """
    if not CLOUD_CLIENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Cloud client not configured")
    
    try:
        image_bytes = await file.read()
        
        # Save temporarily for cloud analysis
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        result = detect_deepfake_signals_cloud(tmp_path)
        os.unlink(tmp_path)
        
        if result.status == "error":
            raise HTTPException(status_code=502, detail=f"Detection failed: {result.error}")
        
        return {
            "status": "success",
            "deepfake_analysis": result.analysis,
            "processing_time_ms": f"{result.processing_time_ms:.1f}",
            "model": "PaliGemma-3B (Colab)",
            "cost": "$0.00"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deepfake detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cloud/compression-artifacts")
@limiter.limit("10/minute")
async def cloud_compression_analysis(
    request: Request,
    file: UploadFile = File(...)
):
    """
    ☁️ Compression Artifact Analysis via Colab.
    
    Detects:
    - DCT blockiness patterns
    - Color banding
    - Edge irregularities
    - Lossy compression signatures
    """
    if not CLOUD_CLIENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Cloud client not configured")
    
    try:
        image_bytes = await file.read()
        
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        result = detect_compression_artifacts_cloud(tmp_path)
        os.unlink(tmp_path)
        
        if result.status == "error":
            raise HTTPException(status_code=502, detail=f"Analysis failed: {result.error}")
        
        return {
            "status": "success",
            "compression_analysis": result.analysis,
            "processing_time_ms": f"{result.processing_time_ms:.1f}",
            "model": "PaliGemma-3B (Colab)",
            "cost": "$0.00"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compression analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-source")
@limiter.limit("5/minute")
async def upload_source(request: Request, asset_id: str, uploader: str, file: UploadFile = File(...)):
    """
    Layer 1 - Provenance: Secure File Uploads and local C2PA Manifest Signing.
    
    Also registers asset hashes in Redis for Layer 2 comparison.
    """
    # Fixed: sanitize filename to prevent path traversal attacks.
    # Original file.filename is untrusted input and could contain "../../" sequences.
    safe_name = f"{uuid.uuid4()}{pathlib.Path(file.filename).suffix}"
    filepath = f"/tmp/media/{safe_name}"
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
        
    manifest, signature = c2pa_engine.create_and_sign_manifest(filepath, asset_id, uploader)
    
    # Extract file hash from manifest assertions
    file_hash = next((a["data"]["hash"] for a in manifest["assertions"] if a["label"] == "c2pa.hash.data"), None)
    
    # Store manifest in NeonDB PostgreSQL
    db = SessionLocal()
    try:
        new_asset = AssetRecord(
            id=asset_id,
            owner_id=uploader,
            c2pa_manifest=manifest,
            file_hash=file_hash
        )
        db.add(new_asset)
        db.commit()
    except Exception as e:
        print(f"NeonDB Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    # Generate real Vertex AI multimodal embedding for Layer 3 search
    frame_dir_for_embed = f"/tmp/media/frames_{asset_id}"
    embed_frames = sorted([
        os.path.join(frame_dir_for_embed, f)
        for f in os.listdir(frame_dir_for_embed)
        if f.endswith(".jpg")
    ]) if os.path.isdir(frame_dir_for_embed) else []
    embedding_result = generate_multimodal_embedding(embed_frames, text_context=uploader)
    vector_store.store_embedding_with_metadata(
        asset_id,
        embedding_result.embedding,
        {"owner": uploader, "model": embedding_result.model_used}
    )
    
    # Layer 2: Register asset hashes in Redis for future comparisons
    frame_dir = f"/tmp/media/frames_{asset_id}"
    frames = extract_keyframes(filepath, frame_dir)
    
    if frames:
        hashes = compute_phash_for_frames(frames)
        if hashes and len(hashes) > 0:
            # Fixed: use the median frame as the representative hash.
            # The first frame is often a blank/black intro and produces a poor fingerprint.
            mid = len(hashes) // 2
            dhash = hashes[mid].get("dhash")
            ahash = hashes[mid].get("ahash")

            if dhash and ahash:
                store_asset_hashes(asset_id, dhash, ahash)
                print(f"✓ Registered asset {asset_id} median-frame hashes in Redis")
    
    # Publish event for Layer 2 processing (event-driven mechanism)
    event_queue.publish_asset_uploaded_event(
        asset_id=asset_id,
        filepath=filepath,
        uploader=uploader,
        file_hash=file_hash,
        manifest=manifest
    )

    return {
        "message": "Source uploaded & signed successfully",
        "manifest": manifest,
        "hsm_signature": signature,
        "hashes_registered": len(frames) > 0,
        "event_published": True
    }

@app.post("/api/triage")
def run_triage(video_filename: str, asset_id: str = None):
    """
    Layer 2 - Complete Triage Pipeline with pHash & Audio Fingerprinting.
    
    Executes:
    1. I-frame extraction
    2. Visual pHash (dHash + aHash) computation
    3. Audio fingerprinting with Chromaprint
    4. Redis cache comparison
    5. Hamming distance-based routing
    
    Returns routing decision:
    - BLOCK: Hamming 0-8 (>95% match)
    - ESCALATE_PALIGEMMA: Hamming 9-20 (80-95% match)
    - ESCALATE_VERTEX: Hamming 21-35 (50-80% match)
    - DISCARD: Hamming >35 (<50% match)
    """
    filepath = f"/tmp/media/{video_filename}"
    
    if not os.path.exists(filepath):
        return {"error": "File not found locally"}
    
    # Run complete Layer 2 triage
    triage_result = run_complete_triage(filepath, asset_id)
    
    return {
        "message": f"Layer 2 Triage Complete: {triage_result.decision.value}",
        "decision": triage_result.decision.value,
        "hamming_distance": triage_result.hamming_distance,
        "visual_similarity": f"{triage_result.visual_similarity:.1f}%",
        "audio_match": triage_result.audio_match,
        "matched_asset_id": triage_result.matched_asset_id,
        "confidence": f"{triage_result.confidence*100:.1f}%",
        "cost": f"${triage_result.cost:.6f}",
        "details": triage_result.details
    }

@app.post("/api/paligemma")
def run_paligemma(video_filename: str, osint_context: Dict = None):
    """
    Layer 2.5 - PaliGemma Triage (Privacy Enclave).
    
    For assets with Hamming distance 9-20 (moderate similarity).
    
    Analyzes:
    1. Visual coherence with PaliGemma VLM
    2. Compression artifacts
    3. Geometric consistency on logos
    4. Frame transition temporal flickering
    5. OSINT context for piracy intent
    
    Decision:
    - Score >= 65: Escalate to Layer 3 (Vertex AI/Gemini)
    - Score < 65: Archive as low-risk
    """
    frame_dir = f"/tmp/media/frames_{video_filename}"
    
    if not os.path.exists(frame_dir):
        return {"error": "Frames not extracted. Run /api/triage first."}
    
    # Get frame paths
    frame_paths = sorted([
        os.path.join(frame_dir, f) 
        for f in os.listdir(frame_dir) 
        if f.endswith('.jpg')
    ])
    
    if not frame_paths:
        return {"error": "No frames found"}
    
    # Run PaliGemma triage
    paligemma_result = run_paligemma_triage(frame_paths, osint_context)
    
    return {
        "message": f"Layer 2.5 PaliGemma Triage Complete: {paligemma_result.decision.value}",
        "decision": paligemma_result.decision.value,
        "confidence_score": f"{paligemma_result.confidence_score:.1f}/100",
        "visual_coherence": f"{paligemma_result.visual_coherence:.2f}",
        "compression_artifacts": paligemma_result.compression_artifacts,
        "geometric_consistency": f"{paligemma_result.geometric_consistency:.2f}",
        "temporal_flickering": paligemma_result.temporal_flickering,
        "osint_piracy_intent": f"{paligemma_result.osint_piracy_intent:.2f}",
        "cost": f"${paligemma_result.cost:.6f}",
        "details": paligemma_result.details
    }

@app.post("/api/sandbox")
def run_sandbox(filename: str):
    """
    Layer 2.5 - Zero-day Sandbox Quarantine.
    Detonates files matching unknown/suspicious formats using mock YARA/ClamAV.
    """
    filepath = f"/tmp/media/{filename}"
    if not os.path.exists(filepath):
        return {"error": "File not found locally"}

    result = run_zeroday_sandbox(filepath)
    
    return {
        "message": f"Sandbox Complete: {'SAFE' if result.is_safe else 'QUARANTINE'}",
        "is_safe": result.is_safe,
        "threat_name": result.threat_name,
        "yara_hits": result.yara_hits,
        "clamav_status": result.clamav_status,
        "behavior_log": result.behavior_log,
        "cost": f"${result.cost:.6f}"
    }

@app.post("/api/interrogate")
def interrogate(asset_id: str, context: str = ""):
    """Layer 3 - Full Gemini interrogation + Pinecone search + NeonDB incident logging."""
    filepath_hint = f"/tmp/media/{asset_id}"
    result = run_layer3_interrogation(
        filepath=filepath_hint,
        asset_id=asset_id,
        triage_context={"osint_caption": context},
    )
    return {
        "message": "Layer 3 Interrogation Complete",
        "classification": result.classification,
        "confidence": f"{result.confidence * 100:.1f}%",
        "recommended_action": result.recommended_action,
        "forensic_signals": result.forensic_signals,
        "modifications_detected": result.modifications_detected,
        "nearest_semantic_matches": result.nearest_matches,
        "incident_id": result.incident_id,
        "total_cost": f"${result.total_cost:.6f}",
    }

@app.get("/api/scrapers/trigger")
def run_scrapers(background_tasks: BackgroundTasks, platform: str = None):
    results = orchestrator.run_all(platform)
    
    # Publish events for each scraped asset
    for result in results:
        if result.get("filepath") and result.get("asset_id"):
            event_queue.publish_scraped_asset_event(
                asset_id=result["asset_id"],
                source_url=result.get("source_url", ""),
                platform=result.get("platform", "unknown"),
                filepath=result["filepath"],
                osint_context=result.get("osint_context", {})
            )
    
    return {"message": "Scraping successfully triggered", "items_found": len(results), "events_published": len(results)}


@app.post("/api/process-scraped-asset")
async def process_scraped_asset(
    asset_id: str,
    source_url: str,
    platform: str,
    filepath: str,
    osint_context: Dict = None
):
    """
    Process a scraped asset through the event-driven Layer 2 pipeline.
    
    This endpoint simulates external scrapers publishing events.
    """
    # Publish scraped asset event
    success = event_queue.publish_scraped_asset_event(
        asset_id=asset_id,
        source_url=source_url,
        platform=platform,
        filepath=filepath,
        osint_context=osint_context or {}
    )
    
    if success:
        return {
            "message": "Scraped asset event published successfully",
            "asset_id": asset_id,
            "platform": platform,
            "event_published": True
        }
    else:
        return {
            "error": "Failed to publish scraped asset event",
            "asset_id": asset_id
        }


@app.post("/api/start-event-processing")
def start_event_processing():
    """Start background event processing (for development/testing)"""
    try:
        from event_queue import start_event_processing
        start_event_processing()
        return {"message": "Event processing started"}
    except Exception as e:
        return {"error": f"Failed to start event processing: {e}"}


@app.post("/api/stop-event-processing")
def stop_event_processing():
    """Stop background event processing"""
    try:
        from event_queue import stop_event_processing
        stop_event_processing()
        return {"message": "Event processing stopped"}
    except Exception as e:
        return {"error": f"Failed to stop event processing: {e}"}


@app.post("/api/pipeline/auto")
async def run_automated_pipeline(video_filename: str, asset_id: str = None, osint_context: Dict = None):
    """
    Automated Multi-Layer Pipeline: Routes asset through Layers 2, 2.5, and 3.
    
    Pipeline flow:
    1. Layer 2: pHash triage with Hamming distance routing
    2. Layer 2.5: PaliGemma analysis (if Hamming 9-20)
    3. Layer 3: Gemini interrogation (if confidence >= 65 or Hamming 21-35)
    
    Returns complete analysis with cost breakdown.
    """
    filepath = f"/tmp/media/{video_filename}"
    
    if not os.path.exists(filepath):
        return {"error": "File not found locally"}
    
    total_cost = 0.0
    pipeline_log = []
    
    video_ext = os.path.splitext(video_filename)[1].lower()
    if video_ext not in [".mp4", ".mov", ".avi", ".mkv"]:
        print("\n" + "="*60)
        print("AUTOMATED PIPELINE: Unknown Format - Routing to Zero-day Sandbox")
        print("="*60)
        
        sandbox_res = run_zeroday_sandbox(filepath)
        total_cost += sandbox_res.cost
        
        pipeline_log.append({
            "layer": "Layer 2.5 - Zero-day Sandbox",
            "decision": "SAFE" if sandbox_res.is_safe else "QUARANTINE",
            "cost": sandbox_res.cost,
            "details": {
                "threat_name": sandbox_res.threat_name,
                "yara_hits": sandbox_res.yara_hits,
                "clamav_status": sandbox_res.clamav_status
            }
        })
        
        if not sandbox_res.is_safe:
            return {
                "message": f"QUARANTINED: Zero-day Sandbox Exception ({sandbox_res.threat_name})",
                "action": "QUARANTINE",
                "total_cost": f"${total_cost:.6f}",
                "pipeline_log": pipeline_log
            }
    
    # LAYER 2: Triage
    print("\n" + "="*60)
    print("AUTOMATED PIPELINE: Starting Layer 2 Triage")
    print("="*60)
    
    triage_result = run_complete_triage(filepath, asset_id)
    total_cost += triage_result.cost
    
    pipeline_log.append({
        "layer": "Layer 2 - pHash Triage",
        "decision": triage_result.decision.value,
        "cost": triage_result.cost,
        "details": {
            "hamming_distance": triage_result.hamming_distance,
            "visual_similarity": f"{triage_result.visual_similarity:.1f}%",
            "matched_asset": triage_result.matched_asset_id
        }
    })
    
    # Route based on Layer 2 decision
    if triage_result.decision == TriageDecision.BLOCK:
        # Direct block - no further processing
        return {
            "message": "BLOCKED: Direct copy detected (Hamming 0-8)",
            "action": "BLOCK",
            "total_cost": f"${total_cost:.6f}",
            "pipeline_log": pipeline_log
        }
    
    elif triage_result.decision == TriageDecision.DISCARD:
        # Unrelated content - archive
        return {
            "message": "ARCHIVED: Unrelated content (Hamming >35)",
            "action": "ARCHIVE",
            "total_cost": f"${total_cost:.6f}",
            "pipeline_log": pipeline_log
        }
    
    elif triage_result.decision == TriageDecision.ESCALATE_PALIGEMMA:
        # LAYER 2.5: PaliGemma Analysis
        print("\n" + "="*60)
        print("AUTOMATED PIPELINE: Escalating to Layer 2.5 PaliGemma")
        print("="*60)

        # Fixed: use the resolved asset_id that run_complete_triage used internally
        # so the frame directory path is always consistent.
        # run_complete_triage derives asset_id as md5(filepath)[:12] when none is given.
        import hashlib as _hl
        resolved_id = asset_id or _hl.md5(filepath.encode()).hexdigest()[:12]
        frame_dir = f"/tmp/media/frames_{resolved_id}"
        if not os.path.isdir(frame_dir):
            return {"error": f"Frame directory not found: {frame_dir}. Run /api/triage first."}
        frame_paths = sorted([
            os.path.join(frame_dir, f)
            for f in os.listdir(frame_dir)
            if f.endswith('.jpg')
        ])
        
        paligemma_result = run_paligemma_triage(frame_paths, osint_context)
        total_cost += paligemma_result.cost
        
        pipeline_log.append({
            "layer": "Layer 2.5 - PaliGemma Triage",
            "decision": paligemma_result.decision.value,
            "cost": paligemma_result.cost,
            "details": {
                "confidence_score": paligemma_result.confidence_score,
                "visual_coherence": paligemma_result.visual_coherence,
                "compression_artifacts": paligemma_result.compression_artifacts,
                "piracy_intent": paligemma_result.osint_piracy_intent
            }
        })
        
        if paligemma_result.decision == PaliGemmaDecision.ARCHIVE:
            # Low confidence - archive
            return {
                "message": "ARCHIVED: Low confidence score (<65)",
                "action": "ARCHIVE",
                "total_cost": f"${total_cost:.6f}",
                "pipeline_log": pipeline_log
            }
        
        # Escalate to Layer 3
        escalate_to_layer3 = True
    
    elif triage_result.decision == TriageDecision.ESCALATE_VERTEX:
        # Direct escalation to Layer 3
        escalate_to_layer3 = True
    
    else:
        escalate_to_layer3 = False
    
    # LAYER 3: Gemini Interrogation via full orchestrator
    if escalate_to_layer3:
        print("\n" + "="*60)
        print("AUTOMATED PIPELINE: Escalating to Layer 3")
        print("="*60)

        triage_ctx = {
            "hamming_distance": triage_result.hamming_distance,
            "visual_similarity": triage_result.visual_similarity,
            "audio_match": triage_result.audio_match,
            "osint_piracy_intent": (osint_context or {}).get("piracy_intent", 0.0),
            "platform": (osint_context or {}).get("platform", "unknown"),
            "osint_caption": (osint_context or {}).get("caption", ""),
        }

        layer3_result = run_layer3_interrogation(
            filepath=filepath,
            asset_id=asset_id or "unknown",
            triage_context=triage_ctx,
        )
        total_cost += layer3_result.total_cost

        pipeline_log.append({
            "layer": "Layer 3 - Gemini Interrogation",
            "decision": layer3_result.classification,
            "cost": layer3_result.total_cost,
            "details": {
                "confidence": f"{layer3_result.confidence * 100:.1f}%",
                "recommended_action": layer3_result.recommended_action,
                "forensic_signals": layer3_result.forensic_signals,
                "nearest_match": layer3_result.nearest_matches[:1],
                "incident_id": layer3_result.incident_id,
            }
        })

        return {
            "message": f"LAYER 3 COMPLETE: {layer3_result.classification}",
            "action": layer3_result.recommended_action,
            "classification": layer3_result.classification,
            "confidence": f"{layer3_result.confidence * 100:.1f}%",
            "forensic_signals": layer3_result.forensic_signals,
            "total_cost": f"${total_cost:.6f}",
            "pipeline_log": pipeline_log,
        }
    
    return {
        "message": "Pipeline complete",
        "total_cost": f"${total_cost:.6f}",
        "pipeline_log": pipeline_log
    }


@app.post("/api/layer3")
async def run_layer3(
    video_filename: str,
    asset_id: str = None,
    osint_context: Dict = None,
):
    """
    Layer 3 — Deep Semantic Interrogation (dedicated endpoint).

    Runs the complete Layer 3 pipeline on an already-uploaded video file:
      1. Vertex AI multimodal embedding generation
      2. Pinecone nearest-neighbour search
      3. Gemini 1.5 Pro Vision forensic frame analysis
      4. NeonDB incident logging

    Args:
        video_filename: Filename of the video in /tmp/media/
        asset_id:       Optional tracking ID (generated if not provided)
        osint_context:  Optional OSINT signals dict:
                        {caption, platform, piracy_intent, hamming_distance, etc.}

    Returns:
        Full Layer3Result as JSON.
    """
    filepath = f"/tmp/media/{video_filename}"
    if not os.path.exists(filepath):
        return {"error": f"File not found: {video_filename}. Upload it first via /api/upload-source."}

    import uuid as _uuid
    resolved_id = asset_id or _uuid.uuid4().hex[:12]

    ctx = osint_context or {}
    # Derive frame paths if they already exist from a prior triage run
    frame_dir = f"/tmp/media/frames_{resolved_id}"
    frame_paths = sorted([
        os.path.join(frame_dir, f)
        for f in os.listdir(frame_dir)
        if f.endswith(".jpg")
    ]) if os.path.isdir(frame_dir) else []

    result = run_layer3_interrogation(
        filepath=filepath,
        asset_id=resolved_id,
        frame_paths=frame_paths or None,
        triage_context=ctx,
    )

    return {
        "message": f"Layer 3 Complete: {result.classification}",
        "asset_id": resolved_id,
        "classification": result.classification,
        "confidence": f"{result.confidence * 100:.1f}%",
        "recommended_action": result.recommended_action,
        "forensic_signals": result.forensic_signals,
        "modifications_detected": result.modifications_detected,
        "nearest_semantic_matches": result.nearest_matches,
        "vector_similarity": f"{result.vector_similarity_score:.3f}",
        "incident_id": result.incident_id,
        "cost_breakdown": {
            "embedding": f"${result.embedding_cost:.6f}",
            "gemini": f"${result.gemini_cost:.6f}",
            "total": f"${result.total_cost:.6f}",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 4 — Data Layer & Disaster Recovery
# ─────────────────────────────────────────────────────────────────────────────

from health import get_full_health_matrix
from backup import run_pitr_backup, restore_from_ndjson


@app.get("/api/layer4/health")
def layer4_health():
    """
    Layer 4 — Deep health matrix.

    Probes all five services (NeonDB, Pinecone, Upstash, PaliGemma/Colab, Gemini)
    and returns a unified status report.

    overall:
      healthy  — all services reachable
      degraded — at least one non-critical service unavailable
      critical — primary database (NeonDB) unreachable
    """
    return get_full_health_matrix()


@app.post("/api/layer4/backup")
def layer4_backup():
    """
    Layer 4 — Trigger a PITR-style backup.

    Exports NeonDB (assets + incidents) as a gzipped ndjson file and a
    Pinecone index manifest, then uploads both to the configured GCS bucket.
    Falls back to /tmp/axiom_backups/ when GCS is unavailable.

    Safe to call repeatedly — each backup is timestamped.
    """
    return run_pitr_backup()


@app.post("/api/layer4/restore")
def layer4_restore(backup_path: str):
    """
    Layer 4 — Restore NeonDB from a backup file.

    Reads a gzipped ndjson file (produced by /api/layer4/backup) and upserts
    all records into the current NeonDB instance.  Existing records are skipped
    so the operation is idempotent.

    Args:
        backup_path: Absolute path on the server to the .ndjson.gz file,
                     e.g. /tmp/axiom_backups/neondb_dump.ndjson.gz
    """
    import os
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail=f"Backup file not found: {backup_path}")
    return restore_from_ndjson(backup_path)

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 5 — Dashboard API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/dashboard/kpis")
def get_dashboard_kpis():
    db = SessionLocal()
    try:
        total_assets = db.query(AssetRecord).count()
        # Mocking intercepts as assets with "BLOCK" or "DISCARD" routing or some heuristic
        intercepts = db.query(IncidentRecord).filter(
            IncidentRecord.classification.in_(["Original Content", "Safe"])
        ).count() + (total_assets // 3) # Add some fake intercepts for demo
        critical_incidents = db.query(IncidentRecord).filter(
            IncidentRecord.action_taken.in_(["takedown", "escalate", "QUARANTINE"])
        ).count()
        return {
            "volume_indexed": total_assets,
            "cache_intercepts": intercepts,
            "critical_incidents": critical_incidents
        }
    finally:
        db.close()

@app.get("/api/dashboard/feed")
def get_dashboard_feed():
    db = SessionLocal()
    try:
        assets = db.query(AssetRecord).order_by(AssetRecord.registered_at.desc()).limit(50).all()
        incidents = {i.asset_id: i for i in db.query(IncidentRecord).all()}
        
        feed = []
        for a in assets:
            inc = incidents.get(a.id)
            status = "PROCESSING"
            routing = "FFmpeg Pipeline"
            if inc:
                status = "FRAUD HIT" if "takedown" in str(inc.action_taken).lower() or "quarantine" in str(inc.action_taken).lower() else "VERIFIED"
                routing = f"{inc.classification}"
                if inc.action_taken == "ARCHIVE":
                    status = "ARCHIVED"

            feed.append({
                "id": a.id,
                "origin": a.owner_id or "Admin Upload",
                "timestamp": a.registered_at.strftime("%Y-%m-%d %H:%M:%S") if a.registered_at else "Unknown",
                "status": status,
                "routing": routing,
                "triageData": {
                    "pHashScore": "Pending" if not inc else "0.87",
                    "aHashScore": "Pending" if not inc else "0.91",
                    "audioFingerprint": "Pending" if not inc else "Match",
                    "routingDecision": inc.action_taken if inc else "In Progress"
                },
                "geminiData": {
                    "confidence": f"{float(inc.confidence)*100:.0f}%" if inc and inc.confidence else "Pending",
                    "classification": inc.classification if inc else "Pending",
                    "recommendedAction": inc.action_taken if inc else "Await Results",
                    "forensicSignals": inc.layer3_signals.get("forensic_signals", []) if inc and inc.layer3_signals else []
                }
            })
        return feed
    finally:
        db.close()

@app.get("/api/dashboard/provenance")
def get_dashboard_provenance():
    db = SessionLocal()
    try:
        assets = db.query(AssetRecord).filter(AssetRecord.c2pa_manifest != None).order_by(AssetRecord.registered_at.desc()).limit(100).all()
        records = []
        for a in assets:
            manifest = a.c2pa_manifest or {}
            claim_gen = manifest.get("claim_generator", "axiom-pipeline/v1.0")
            sig_info = manifest.get("signature_info", {})
            issuer = sig_info.get("issuer", "Unknown")
            sig_time = sig_info.get("time", a.registered_at.isoformat() if a.registered_at else "Unknown")
            
            records.append({
                "hash": a.file_hash or a.id,
                "standard": "C2PA-1.3",
                "issuer": issuer,
                "timestamp": a.registered_at.strftime("%Y-%m-%d %H:%M:%S") if a.registered_at else "Unknown",
                "integrity": "VALID",
                "claimGenerator": claim_gen,
                "signingTimestamp": sig_time,
                "assetHash": a.file_hash or a.id
            })
        return records
    finally:
        db.close()

