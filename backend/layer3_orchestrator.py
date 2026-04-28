"""
Layer 3 Orchestrator — Deep Semantic Interrogation
===================================================
Single entry point for Layer 3. Executed when Layer 2 / 2.5 decides to escalate.

Pipeline:
  1. Generate real Vertex AI multimodal embedding from frames + OSINT text
  2. Search Pinecone for the 5 nearest registered protected assets
  3. Run Gemini 1.5 Pro Vision forensic frame analysis with cross-modal context
  4. Merge all signals into a final Layer3Result
  5. Log incident to NeonDB
  6. Store embedding in Pinecone with classification metadata
"""

import os
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("Layer3Orchestrator")

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Layer3Result:
    # Final verdict
    classification: str                     # TRUSTED | FRAUD_AI_MORPHED | DIRECT_COPY | SPLICE_EDIT
    confidence: float                       # 0.0 – 1.0
    recommended_action: str                 # ARCHIVE | REVIEW | TAKEDOWN

    # Forensic detail
    forensic_signals: Dict = field(default_factory=dict)
    modifications_detected: List[str] = field(default_factory=list)

    # Vector similarity
    nearest_matches: List[Dict] = field(default_factory=list)   # [{id, score}, ...]
    vector_similarity_score: float = 0.0    # top-1 Pinecone cosine score

    # Upstream context (passed through for logging)
    hamming_distance: int = 64
    visual_similarity: float = 0.0
    audio_match: bool = False
    osint_piracy_intent: float = 0.0

    # Cost accounting
    embedding_cost: float = 0.0
    gemini_cost: float = 0.0
    total_cost: float = 0.0

    # Incident ID written to NeonDB
    incident_id: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_layer3_interrogation(
    filepath: str,
    asset_id: str,
    frame_paths: Optional[List[str]] = None,
    triage_context: Optional[Dict] = None,
) -> Layer3Result:
    """
    Executes the complete Layer 3 deep-semantic interrogation pipeline.

    Args:
        filepath:       Path to the video file being analysed.
        asset_id:       Unique asset identifier (used for NeonDB + Pinecone).
        frame_paths:    Pre-extracted JPEG keyframe paths (optional — will
                        be derived from filepath if not supplied).
        triage_context: Dict with upstream signals:
                        {audio_match, hamming_distance, visual_similarity,
                         osint_piracy_intent, platform, osint_caption}

    Returns:
        Layer3Result with all signals merged.
    """
    ctx = triage_context or {}
    logger.info("\n%s\nLAYER 3 INTERROGATION: %s\n%s", "="*60, asset_id, "="*60)

    # -----------------------------------------------------------------------
    # Step 0 — Resolve frame paths if not supplied
    # -----------------------------------------------------------------------
    if not frame_paths:
        frame_dir = f"/tmp/media/frames_{asset_id}"
        if os.path.isdir(frame_dir):
            frame_paths = sorted([
                os.path.join(frame_dir, f)
                for f in os.listdir(frame_dir)
                if f.endswith(".jpg")
            ])
        else:
            frame_paths = []

    # -----------------------------------------------------------------------
    # Step 1 — Generate Vertex AI multimodal embedding
    # -----------------------------------------------------------------------
    logger.info("[1/4] Generating Vertex AI embedding (%d frames)...", len(frame_paths))
    from vertex_embedder import generate_multimodal_embedding, store_embedding_with_metadata

    osint_text = ctx.get("osint_caption") or ctx.get("caption", "")
    embedding_result = generate_multimodal_embedding(frame_paths, text_context=osint_text)
    embedding_cost = embedding_result.cost
    logger.info("  ✓ Embedding: model=%s, cost=$%.6f", embedding_result.model_used, embedding_cost)

    # -----------------------------------------------------------------------
    # Step 2 — Pinecone nearest-neighbour search
    # -----------------------------------------------------------------------
    logger.info("[2/4] Pinecone nearest-neighbour search...")
    import vector_store

    nearest_matches = vector_store.search_nearest_assets(
        embedding_result.embedding, top_k=5
    )
    top_score = nearest_matches[0]["score"] if nearest_matches else 0.0
    if nearest_matches:
        logger.info("  ✓ Nearest match: %s (score=%.3f)", nearest_matches[0]["id"], top_score)
    else:
        logger.info("  ⚠ No nearest matches found in Pinecone")

    # -----------------------------------------------------------------------
    # Step 3 — Gemini 1.5 Pro Vision forensic interrogation
    # -----------------------------------------------------------------------
    logger.info("[3/4] Gemini 1.5 Pro Vision interrogation...")
    from gemini_interrogator import analyze_video_frames_for_fraud

    gemini_result = analyze_video_frames_for_fraud(
        frame_paths=frame_paths,
        source_context=osint_text,
        triage_context={**ctx, "nearest_vector_score": top_score},
    )
    gemini_cost = gemini_result.gemini_cost
    logger.info(
        "  ✓ Gemini: %s (confidence=%.2f, cost=$%.5f)",
        gemini_result.classification, gemini_result.confidence, gemini_cost,
    )

    # -----------------------------------------------------------------------
    # Step 4 — Merge all signals into final verdict
    # -----------------------------------------------------------------------
    logger.info("[4/4] Merging signals and logging incident...")

    # Boost confidence when upstream signals agree with Gemini
    adjusted_confidence = _adjust_confidence(gemini_result.confidence, ctx, top_score)

    total_cost = embedding_cost + gemini_cost
    result = Layer3Result(
        classification=gemini_result.classification,
        confidence=adjusted_confidence,
        recommended_action=gemini_result.recommended_action,
        forensic_signals=_signals_to_dict(gemini_result.forensic_signals),
        modifications_detected=gemini_result.modifications_detected,
        nearest_matches=nearest_matches,
        vector_similarity_score=top_score,
        hamming_distance=ctx.get("hamming_distance", 64),
        visual_similarity=ctx.get("visual_similarity", 0.0),
        audio_match=ctx.get("audio_match", False),
        osint_piracy_intent=ctx.get("osint_piracy_intent", 0.0),
        embedding_cost=embedding_cost,
        gemini_cost=gemini_cost,
        total_cost=total_cost,
    )

    # -----------------------------------------------------------------------
    # Log to NeonDB
    # -----------------------------------------------------------------------
    incident_id = _log_incident(asset_id, result)
    result.incident_id = incident_id

    # -----------------------------------------------------------------------
    # Store embedding in Pinecone with classification metadata
    # -----------------------------------------------------------------------
    store_embedding_with_metadata(
        asset_id=asset_id,
        embedding_result=embedding_result,
        metadata={
            "classification": result.classification,
            "confidence": round(result.confidence, 4),
            "recommended_action": result.recommended_action,
            "hamming_distance": result.hamming_distance,
            "osint_score": round(result.osint_piracy_intent, 4),
            "platform": ctx.get("platform", "unknown"),
        },
    )

    logger.info(
        "\n  ═══════════════════════════════\n"
        "  LAYER 3 RESULT\n"
        "  Classification : %s\n"
        "  Confidence     : %.1f%%\n"
        "  Action         : %s\n"
        "  Total Cost     : $%.6f\n"
        "  ═══════════════════════════════",
        result.classification, result.confidence * 100,
        result.recommended_action, total_cost,
    )

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _adjust_confidence(base: float, ctx: Dict, vector_score: float) -> float:
    """
    Slightly adjusts Gemini's raw confidence based on corroborating upstream signals.
    Uses a weighted average: 60% Gemini, 20% vector similarity, 20% OSINT.
    """
    osint_score = ctx.get("osint_piracy_intent", 0.0)

    # Normalise vector cosine score (0-1) to a confidence-compatible range
    # Pinecone returns cosine similarity 0-1; treat high similarity as high risk.
    vec_confidence = min(vector_score, 1.0)

    adjusted = (base * 0.6) + (vec_confidence * 0.2) + (osint_score * 0.2)
    return round(min(adjusted, 1.0), 4)


def _signals_to_dict(signals) -> Dict:
    """Converts a ForensicSignals dataclass to a plain dict for JSON serialisation."""
    try:
        import dataclasses
        return dataclasses.asdict(signals)
    except Exception:
        return {}


def _log_incident(asset_id: str, result: Layer3Result) -> Optional[str]:
    """Writes a full incident record to NeonDB and returns the incident_id."""
    try:
        from database import SessionLocal, IncidentRecord
        incident_id = f"inc_{os.urandom(4).hex()}"

        db = SessionLocal()
        try:
            incident = IncidentRecord(
                incident_id=incident_id,
                asset_id=asset_id,
                classification=result.classification,
                confidence=str(round(result.confidence, 4)),
                gemini_report={
                    "classification": result.classification,
                    "confidence": result.confidence,
                    "forensic_signals": result.forensic_signals,
                    "modifications_detected": result.modifications_detected,
                    "recommended_action": result.recommended_action,
                    "nearest_matches": result.nearest_matches,
                    "costs": {
                        "embedding": result.embedding_cost,
                        "gemini": result.gemini_cost,
                        "total": result.total_cost,
                    },
                },
                action_taken=result.recommended_action,
                detected_at=datetime.now(timezone.utc),
                layer3_signals=result.forensic_signals,
            )
            db.add(incident)
            db.commit()
            logger.info("  ✓ Incident logged: %s", incident_id)
            return incident_id
        except Exception as exc:
            logger.error("  ✗ NeonDB incident log failed: %s", exc)
            db.rollback()
            return None
        finally:
            db.close()

    except Exception as exc:
        logger.error("  ✗ Could not import database module: %s", exc)
        return None
