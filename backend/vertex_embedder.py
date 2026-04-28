"""
Layer 3A: Vertex AI Semantic Embedding Engine
Generates 1408-dimensional multimodal embeddings for cross-modal similarity search.

Primary model  : multimodalembedding@001  (image + text, 1408 dims)
Text fallback  : textembedding-gecko@003  (text-only, padded to 1408 dims)
Storage        : Pinecone vector store (via vector_store.py)
"""

import os
import base64
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger("VertexEmbedder")

# ---------------------------------------------------------------------------
# Lazy Vertex AI client — only initialise when a real call is needed
# ---------------------------------------------------------------------------
_vertex_initialised = False

def _ensure_vertex():
    """Initialise Vertex AI SDK once per process."""
    global _vertex_initialised
    if _vertex_initialised:
        return True
    try:
        import vertexai
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID", "axiom-project")
        region  = os.getenv("VERTEX_REGION", "us-central1")
        vertexai.init(project=project, location=region)
        _vertex_initialised = True
        logger.info("✓ Vertex AI initialised (project=%s, region=%s)", project, region)
        return True
    except Exception as exc:
        logger.warning("⚠ Vertex AI not available: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

EMBEDDING_DIM = 1408  # multimodalembedding@001 output dimension


@dataclass
class EmbeddingResult:
    embedding: List[float]          # 1408-dimensional float vector
    model_used: str                 # which model produced the embedding
    frames_used: int = 0            # number of frames encoded
    cost: float = 0.0               # estimated USD cost
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_multimodal_embedding(
    frame_paths: List[str],
    text_context: str = "",
) -> EmbeddingResult:
    """
    Generates a 1408-dim embedding from keyframes + text context.

    Strategy:
    1. Try Vertex AI multimodalembedding@001 with up to 3 representative frames.
    2. Fall back to textembedding-gecko@003 (text-only, zero-padded to 1408 dims)
       if Vertex is unavailable or frame list is empty.
    3. Final fallback: return a zero vector so the pipeline never crashes.

    Args:
        frame_paths:  Ordered list of extracted keyframe JPEG paths.
        text_context: OSINT caption / source URL string for text fusion.

    Returns:
        EmbeddingResult with the embedding vector and metadata.
    """
    # Select up to 3 representative frames (start, middle, end)
    sampled = _sample_frames(frame_paths, n=3)

    if sampled and _ensure_vertex():
        result = _embed_multimodal(sampled, text_context)
        if result is not None:
            return result

    # Text-only fallback
    if text_context and _ensure_vertex():
        result = _embed_text_fallback(text_context)
        if result is not None:
            return result

    # Hard fallback — zero vector (won't crash downstream Pinecone upsert)
    logger.warning("⚠ All embedding attempts failed — returning zero vector")
    return EmbeddingResult(
        embedding=[0.0] * EMBEDDING_DIM,
        model_used="zero_fallback",
        cost=0.0,
        error="All embedding providers unavailable"
    )


def store_embedding_with_metadata(
    asset_id: str,
    embedding_result: EmbeddingResult,
    metadata: Optional[Dict] = None,
) -> bool:
    """
    Upserts the embedding into Pinecone with rich metadata for filtering.

    Metadata fields stored alongside the vector:
        - model_used, frames_used, cost
        - classification, platform, osint_score, hamming_distance (caller-supplied)

    Args:
        asset_id:         Pinecone vector ID.
        embedding_result: Output of generate_multimodal_embedding().
        metadata:         Optional dict with classification / OSINT signals.

    Returns:
        True on success, False on failure.
    """
    try:
        import vector_store  # local module

        full_metadata = {
            "model": embedding_result.model_used,
            "frames": embedding_result.frames_used,
            "embed_cost": embedding_result.cost,
        }
        if metadata:
            full_metadata.update(metadata)

        vector_store.store_embedding_with_metadata(asset_id, embedding_result.embedding, full_metadata)
        logger.info("✓ Stored embedding for asset %s (model=%s)", asset_id, embedding_result.model_used)
        return True

    except Exception as exc:
        logger.error("✗ Failed to store embedding for %s: %s", asset_id, exc)
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sample_frames(frame_paths: List[str], n: int = 3) -> List[str]:
    """Returns n evenly-spaced frames from the list."""
    if not frame_paths:
        return []
    if len(frame_paths) <= n:
        return frame_paths
    step = len(frame_paths) // n
    return [frame_paths[i * step] for i in range(n)]


def _load_frame_as_b64(path: str) -> Optional[str]:
    """Reads a JPEG file and returns its base64 string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as exc:
        logger.warning("⚠ Could not read frame %s: %s", path, exc)
        return None


def _embed_multimodal(frame_paths: List[str], text_context: str) -> Optional[EmbeddingResult]:
    """
    Calls Vertex AI multimodalembedding@001.
    Encodes up to 3 JPEG frames as base64 Image parts + optional text segment.
    """
    try:
        from vertexai.vision_models import MultiModalEmbeddingModel, Image as VImage

        model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")

        # Load frames
        images = []
        for fp in frame_paths:
            b64 = _load_frame_as_b64(fp)
            if b64:
                images.append(VImage(image_bytes=base64.b64decode(b64)))

        if not images:
            return None

        # Vertex multimodal embedding accepts one image at a time; average embeddings
        embeddings = []
        for img in images:
            resp = model.get_embeddings(image=img, contextual_text=text_context or None)
            embeddings.append(resp.image_embedding)

        # Average across frames
        avg = [sum(col) / len(col) for col in zip(*embeddings)]

        # Cost: ~$0.0013 per image (Vertex multimodal embedding pricing)
        cost = len(images) * 0.0013

        logger.info("✓ Multimodal embedding generated (%d frames, cost=$%.6f)", len(images), cost)
        return EmbeddingResult(
            embedding=avg,
            model_used="multimodalembedding@001",
            frames_used=len(images),
            cost=cost,
        )

    except Exception as exc:
        logger.warning("⚠ multimodalembedding@001 failed: %s", exc)
        return None


def _embed_text_fallback(text: str) -> Optional[EmbeddingResult]:
    """
    Falls back to textembedding-gecko@003 (768 dims) and zero-pads to 1408.
    Useful when no frames are available but OSINT context text is present.
    """
    try:
        from vertexai.language_models import TextEmbeddingModel

        model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        result = model.get_embeddings([text])
        vec = result[0].values  # 768 dims

        # Pad to 1408 to match Pinecone index dimension
        padded = list(vec) + [0.0] * (EMBEDDING_DIM - len(vec))

        cost = 0.0001  # negligible text embedding cost
        logger.info("✓ Text embedding fallback used (gecko@003, padded to %d dims)", EMBEDDING_DIM)
        return EmbeddingResult(
            embedding=padded,
            model_used="textembedding-gecko@003",
            frames_used=0,
            cost=cost,
        )

    except Exception as exc:
        logger.warning("⚠ textembedding-gecko@003 failed: %s", exc)
        return None
