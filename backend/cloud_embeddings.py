"""
Cloud Embeddings Module: Free multimodal embeddings via Colab
=============================================================

Replaces Vertex AI multimodalembedding@001 with free cloud alternatives:
1. HuggingFace Sentence-Transformers CLIP (via Colab ngrok)
2. OpenAI CLIP embeddings (free tier limited)

No Vertex AI charges. All embeddings generated in cloud.
"""

import os
import base64
import logging
import time
import requests
from typing import List, Optional, Dict
from dataclasses import dataclass
from PIL import Image
import io

logger = logging.getLogger("CloudEmbeddings")

# ============================================================================
# Configuration
# ============================================================================

COLAB_NGROK_URL = os.getenv("COLAB_NGROK_URL", "https://deskbound-unmolded-veto.ngrok-free.dev")
EMBEDDINGS_ENDPOINT = os.getenv("EMBEDDINGS_ENDPOINT", f"{COLAB_NGROK_URL}/generate-embedding")

TIMEOUT = int(os.getenv("COLAB_TIMEOUT", "120"))
RETRY_ATTEMPTS = int(os.getenv("COLAB_RETRY_ATTEMPTS", "3"))
DEBUG = os.getenv("DEBUG_CLOUD_CALLS", "false").lower() == "true"

EMBEDDING_DIM = 1408  # Match Vertex embedding dimension for compatibility

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class EmbeddingResult:
    """Multimodal embedding response"""
    embedding: List[float]          # 1408-dimensional vector
    model_used: str                 # which model generated embedding
    frames_used: int = 0
    cost: float = 0.0               # always $0.00 (free models)
    error: Optional[str] = None


# ============================================================================
# Local CLIP Embedding (No API calls)
# ============================================================================

_CLIP_MODEL_LOADED = False
_CLIP_MODEL = None
_CLIP_PROCESSOR = None

def _load_clip_model():
    """Lazy-load CLIP model on first use."""
    global _CLIP_MODEL_LOADED, _CLIP_MODEL, _CLIP_PROCESSOR
    
    if _CLIP_MODEL_LOADED:
        return True
    
    try:
        import torch
        from transformers import CLIPProcessor, CLIPModel
        
        if DEBUG:
            logger.info("📦 Loading CLIP model from HuggingFace...")
        
        model_name = "openai/clip-vit-large-patch14"
        _CLIP_PROCESSOR = CLIPProcessor.from_pretrained(model_name)
        _CLIP_MODEL = CLIPModel.from_pretrained(model_name, torch_dtype=torch.float16)
        
        # Use GPU if available
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _CLIP_MODEL = _CLIP_MODEL.to(device)
        _CLIP_MODEL.eval()
        
        _CLIP_MODEL_LOADED = True
        logger.info("✓ CLIP model loaded successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}")
        return False


def generate_clip_embedding_local(
    frame_paths: List[str],
    text_context: str = ""
) -> EmbeddingResult:
    """
    Generate embedding using free local CLIP model.
    
    No cloud calls - runs on local GPU/CPU.
    
    Args:
        frame_paths:  List of JPEG frame paths (use up to 3)
        text_context: Optional text to fuse with frames
    
    Returns:
        EmbeddingResult with 1408-dim embedding
    """
    if not _load_clip_model():
        return EmbeddingResult(
            embedding=[0.0] * EMBEDDING_DIM,
            model_used="zero_fallback",
            error="CLIP model unavailable"
        )
    
    try:
        import torch
        import numpy as np
        
        # Load up to 3 frames
        images = []
        for frame_path in frame_paths[:3]:
            try:
                img = Image.open(frame_path).convert("RGB")
                images.append(img)
            except Exception as e:
                logger.warning(f"Could not load frame {frame_path}: {e}")
        
        if not images:
            raise ValueError("No valid frames could be loaded")
        
        # Generate embeddings
        with torch.inference_mode():
            inputs = _CLIP_PROCESSOR(
                text=[text_context] if text_context else ["video frame"],
                images=images,
                return_tensors="pt",
                padding=True
            ).to(_CLIP_MODEL.device)
            
            outputs = _CLIP_MODEL(**inputs)
            
            # Average image embeddings across frames
            image_embeds = outputs.image_embeds.cpu().numpy()
            embedding = np.mean(image_embeds, axis=0)
        
        # Pad to 1408 dims for compatibility
        if len(embedding) < EMBEDDING_DIM:
            embedding = np.pad(embedding, (0, EMBEDDING_DIM - len(embedding)))
        else:
            embedding = embedding[:EMBEDDING_DIM]
        
        return EmbeddingResult(
            embedding=embedding.tolist(),
            model_used="clip-local-free",
            frames_used=len(images),
            cost=0.0
        )
    
    except Exception as e:
        logger.error(f"CLIP embedding generation failed: {e}")
        return EmbeddingResult(
            embedding=[0.0] * EMBEDDING_DIM,
            model_used="zero_fallback",
            error=str(e)
        )


# ============================================================================
# Cloud CLIP Embedding (via Colab)
# ============================================================================

def generate_embedding_cloud(
    frame_paths: List[str],
    text_context: str = ""
) -> EmbeddingResult:
    """
    Generate embedding via Colab ngrok endpoint.
    
    Args:
        frame_paths:  List of JPEG frame paths
        text_context: Optional text context
    
    Returns:
        EmbeddingResult with embedding vector
    """
    if not frame_paths:
        return EmbeddingResult(
            embedding=[0.0] * EMBEDDING_DIM,
            model_used="zero_fallback",
            error="No frames provided"
        )
    
    # Use first frame
    frame_path = frame_paths[0]
    
    try:
        # Encode image to base64
        with open(frame_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        payload = {
            "image_base64": image_b64,
            "text_context": text_context,
            "embedding_dim": EMBEDDING_DIM
        }
        
        response = requests.post(
            EMBEDDINGS_ENDPOINT,
            json=payload,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result_data = response.json()
            return EmbeddingResult(
                embedding=result_data.get("embedding", [0.0] * EMBEDDING_DIM),
                model_used=result_data.get("model_used", "clip-cloud"),
                frames_used=1,
                cost=0.0
            )
        else:
            logger.error(f"Cloud embedding failed: {response.status_code}")
            return EmbeddingResult(
                embedding=[0.0] * EMBEDDING_DIM,
                model_used="zero_fallback",
                error=f"HTTP {response.status_code}"
            )
    
    except Exception as e:
        logger.error(f"Cloud embedding request failed: {e}")
        return EmbeddingResult(
            embedding=[0.0] * EMBEDDING_DIM,
            model_used="zero_fallback",
            error=str(e)
        )


# ============================================================================
# Main Interface (Auto-select based on config)
# ============================================================================

def generate_multimodal_embedding(
    frame_paths: List[str],
    text_context: str = ""
) -> EmbeddingResult:
    """
    Generate multimodal embedding (auto-select best free method).
    
    Priority:
    1. Local CLIP (if GPU available) - fastest, $0
    2. Cloud CLIP via Colab (if endpoint available) - $0
    3. Zero vector fallback
    
    Args:
        frame_paths:  List of JPEG frame paths
        text_context: Optional text context
    
    Returns:
        EmbeddingResult with 1408-dim embedding vector
    """
    # Try local CLIP first
    try:
        import torch
        result = generate_clip_embedding_local(frame_paths, text_context)
        if result.error is None:
            if DEBUG:
                logger.info("✓ Using local CLIP embeddings")
            return result
    except Exception as e:
        logger.warning(f"Local CLIP unavailable: {e}")
    
    # Fall back to cloud CLIP
    if DEBUG:
        logger.info("→ Trying cloud CLIP embeddings")
    
    result = generate_embedding_cloud(frame_paths, text_context)
    if result.error is None:
        if DEBUG:
            logger.info("✓ Using cloud CLIP embeddings")
        return result
    
    # Ultimate fallback
    logger.warning("⚠ All embedding methods failed — returning zero vector")
    return EmbeddingResult(
        embedding=[0.0] * EMBEDDING_DIM,
        model_used="zero_fallback",
        cost=0.0,
        error="All embedding methods unavailable"
    )
