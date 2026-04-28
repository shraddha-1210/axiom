"""
Cloud-Only Client: Direct HTTP calls to Colab ngrok endpoints
============================================================

This module replaces all local system interactions with pure HTTP API calls
to the PaliGemma inference service running on Google Colab.

No local GPU/CPU usage. All inference happens in the cloud.
"""

import os
import json
import base64
import logging
import time
import requests
from typing import Optional, Dict, List
from dataclasses import dataclass
from PIL import Image
import io

logger = logging.getLogger("CloudClient")

# ============================================================================
# Configuration
# ============================================================================

COLAB_NGROK_URL = os.getenv("COLAB_NGROK_URL", "https://deskbound-unmolded-veto.ngrok-free.dev")
COLAB_ENDPOINT = os.getenv("PALIGEMMA_ENDPOINT", f"{COLAB_NGROK_URL}/analyze-frame")
COLAB_HEALTH_CHECK = os.getenv("COLAB_HEALTH_CHECK", f"{COLAB_NGROK_URL}/health")

TIMEOUT = int(os.getenv("COLAB_TIMEOUT", "120"))
RETRY_ATTEMPTS = int(os.getenv("COLAB_RETRY_ATTEMPTS", "3"))
RETRY_DELAY = int(os.getenv("COLAB_RETRY_DELAY", "2"))
DEBUG = os.getenv("DEBUG_CLOUD_CALLS", "false").lower() == "true"

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CloudAnalysisResult:
    """Response from Colab inference endpoint"""
    status: str                      # "success" | "error"
    analysis: str                    # Model output text
    confidence: Optional[float] = None
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


# ============================================================================
# Cloud Health Check
# ============================================================================

def check_colab_health() -> bool:
    """
    Check if Colab ngrok endpoint is alive.
    
    Returns:
        True if endpoint is reachable, False otherwise.
    """
    try:
        response = requests.get(
            COLAB_HEALTH_CHECK,
            timeout=5
        )
        is_healthy = response.status_code == 200
        if DEBUG:
            logger.info(f"✓ Colab health check: {is_healthy}")
        return is_healthy
    except Exception as e:
        logger.warning(f"⚠ Colab health check failed: {e}")
        return False


# ============================================================================
# Image Encoding
# ============================================================================

def encode_image_to_base64(image_path: str) -> str:
    """
    Load image and encode to base64 for HTTP transmission.
    
    Args:
        image_path: Path to JPEG/PNG image file
        
    Returns:
        Base64-encoded image string
    """
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        raise


def encode_pil_image_to_base64(image: Image.Image) -> str:
    """
    Convert PIL Image object to base64 for HTTP transmission.
    
    Args:
        image: PIL Image object
        
    Returns:
        Base64-encoded image string
    """
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        image_data = buffer.getvalue()
        return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode PIL image: {e}")
        raise


# ============================================================================
# Main Cloud Inference Interface
# ============================================================================

def analyze_frame_cloud(
    image_path: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    pil_image: Optional[Image.Image] = None,
    prompt: str = "caption en",
    retry: bool = True
) -> CloudAnalysisResult:
    """
    Send frame to Colab for analysis via ngrok endpoint.
    
    One of image_path, image_bytes, or pil_image must be provided.
    
    Args:
        image_path:   Path to image file (local or S3)
        image_bytes:  Raw image bytes
        pil_image:    PIL Image object
        prompt:       PaliGemma prompt (default: English caption)
        retry:        Whether to retry on failure
    
    Returns:
        CloudAnalysisResult with model output
    """
    start_time = time.time()
    
    # Prepare image encoding
    try:
        if image_path:
            image_b64 = encode_image_to_base64(image_path)
        elif image_bytes:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        elif pil_image:
            image_b64 = encode_pil_image_to_base64(pil_image)
        else:
            raise ValueError("Must provide one of: image_path, image_bytes, pil_image")
    except Exception as e:
        return CloudAnalysisResult(
            status="error",
            analysis="",
            error=f"Image encoding failed: {e}",
            processing_time_ms=time.time() - start_time
        )
    
    # Prepare request payload
    payload = {
        "image_base64": image_b64,
        "prompt": prompt
    }
    
    if DEBUG:
        logger.info(f"🚀 Sending frame to Colab endpoint: {COLAB_ENDPOINT}")
        logger.info(f"   Prompt: {prompt}")
    
    # Retry logic
    last_error = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = requests.post(
                COLAB_ENDPOINT,
                json=payload,
                timeout=TIMEOUT,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result_data = response.json()
                processing_time = time.time() - start_time
                
                if DEBUG:
                    logger.info(f"✓ Cloud analysis complete ({processing_time:.2f}s)")
                
                return CloudAnalysisResult(
                    status=result_data.get("status", "unknown"),
                    analysis=result_data.get("analysis", ""),
                    processing_time_ms=processing_time * 1000,
                    raw_response=result_data
                )
            else:
                last_error = f"HTTP {response.status_code}: {response.text}"
                if DEBUG:
                    logger.warning(f"⚠ Attempt {attempt+1}/{RETRY_ATTEMPTS} failed: {last_error}")
        
        except requests.Timeout:
            last_error = f"Timeout after {TIMEOUT}s (Colab may be busy)"
            if DEBUG:
                logger.warning(f"⚠ Attempt {attempt+1}/{RETRY_ATTEMPTS} timed out")
        
        except requests.ConnectionError as e:
            last_error = f"Connection failed: {e}"
            if DEBUG:
                logger.warning(f"⚠ Attempt {attempt+1}/{RETRY_ATTEMPTS} - connection error: {e}")
        
        except Exception as e:
            last_error = str(e)
            if DEBUG:
                logger.error(f"⚠ Attempt {attempt+1}/{RETRY_ATTEMPTS} - unexpected error: {e}")
        
        # Retry delay (except on last attempt)
        if attempt < RETRY_ATTEMPTS - 1:
            if DEBUG:
                logger.info(f"⏳ Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
    
    # All retries failed
    processing_time = time.time() - start_time
    return CloudAnalysisResult(
        status="error",
        analysis="",
        error=last_error or "Unknown error after all retries",
        processing_time_ms=processing_time * 1000
    )


def batch_analyze_frames_cloud(
    frame_paths: List[str],
    prompt: str = "caption en"
) -> List[CloudAnalysisResult]:
    """
    Analyze multiple frames sequentially (respects Colab rate limits).
    
    Args:
        frame_paths: List of image file paths
        prompt:      PaliGemma prompt
    
    Returns:
        List of CloudAnalysisResult objects
    """
    results = []
    for i, frame_path in enumerate(frame_paths):
        if DEBUG:
            logger.info(f"Processing frame {i+1}/{len(frame_paths)}: {frame_path}")
        
        result = analyze_frame_cloud(image_path=frame_path, prompt=prompt)
        results.append(result)
        
        # Small delay between requests to avoid overwhelming Colab
        if i < len(frame_paths) - 1:
            time.sleep(0.5)
    
    return results


# ============================================================================
# Specialized Cloud Analyzers
# ============================================================================

def detect_deepfake_signals_cloud(frame_path: str) -> CloudAnalysisResult:
    """
    Use PaliGemma to detect deepfake/AI-morphing signals in a frame.
    
    Args:
        frame_path: Path to video frame
    
    Returns:
        CloudAnalysisResult with forensic analysis
    """
    prompt = "Is this image a deepfake? Analyze facial features, temporal artifacts, skin texture, eye blinking."
    return analyze_frame_cloud(image_path=frame_path, prompt=prompt)


def detect_compression_artifacts_cloud(frame_path: str) -> CloudAnalysisResult:
    """
    Use PaliGemma to detect compression/encoding artifacts.
    
    Args:
        frame_path: Path to video frame
    
    Returns:
        CloudAnalysisResult with compression analysis
    """
    prompt = "Analyze this image for compression artifacts, DCT blockiness, color banding, edge irregularities."
    return analyze_frame_cloud(image_path=frame_path, prompt=prompt)


def detect_logo_manipulation_cloud(frame_path: str) -> CloudAnalysisResult:
    """
    Use PaliGemma to detect logo inpainting/manipulation.
    
    Args:
        frame_path: Path to video frame
    
    Returns:
        CloudAnalysisResult with logo analysis
    """
    prompt = "Identify any logos, brand marks, or text in this image. Describe their placement, clarity, and any signs of editing or inpainting."
    return analyze_frame_cloud(image_path=frame_path, prompt=prompt)


def generate_frame_caption_cloud(frame_path: str) -> CloudAnalysisResult:
    """
    Generate natural language caption for a frame (default behavior).
    
    Args:
        frame_path: Path to video frame
    
    Returns:
        CloudAnalysisResult with caption
    """
    prompt = "caption en"  # Standard PaliGemma English caption
    return analyze_frame_cloud(image_path=frame_path, prompt=prompt)


# ============================================================================
# Integration with AXIOM Pipeline
# ============================================================================

def cloud_triage_decision(
    frame_paths: List[str],
    osint_context: Optional[Dict] = None
) -> Dict:
    """
    Make triage decision based on cloud analysis of frames.
    
    Returns:
        {
            "decision": "ARCHIVE" | "REVIEW" | "ESCALATE",
            "confidence": 0.0-1.0,
            "signals": [...],
            "details": {...}
        }
    """
    if not frame_paths:
        return {
            "decision": "ARCHIVE",
            "confidence": 0.0,
            "error": "No frames provided"
        }
    
    # Analyze representative frame
    representative_frame = frame_paths[len(frame_paths) // 2]
    
    # Get caption
    caption_result = generate_frame_caption_cloud(representative_frame)
    if caption_result.status != "success":
        return {
            "decision": "REVIEW",
            "confidence": 0.5,
            "error": caption_result.error
        }
    
    # Get deepfake signals
    deepfake_result = detect_deepfake_signals_cloud(representative_frame)
    
    signals = {
        "caption": caption_result.analysis,
        "deepfake_analysis": deepfake_result.analysis if deepfake_result.status == "success" else ""
    }
    
    # Simple heuristic: if deepfake keywords found, escalate
    deepfake_keywords = ["deepfake", "morphed", "synthetic", "ai-generated", "manipulated", "edited"]
    has_deepfake_signals = any(
        keyword in deepfake_result.analysis.lower()
        for keyword in deepfake_keywords
    ) if deepfake_result.status == "success" else False
    
    if has_deepfake_signals:
        decision = "ESCALATE"
        confidence = 0.85
    else:
        decision = "ARCHIVE"
        confidence = 0.6
    
    return {
        "decision": decision,
        "confidence": confidence,
        "signals": signals
    }
