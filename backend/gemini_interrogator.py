"""
Layer 3B: Gemini 1.5 Pro Vision — Forensic Frame Interrogator

Upgrades from the previous text-only stub to a true multimodal analysis:
- Uploads JPEG keyframes via the Gemini File API (real image ingestion)
- Enforces a strict forensic JSON schema for structured output
- Cross-modal context injection (audio match + Hamming distance + OSINT)
- Auto-cleans uploaded File API resources after inference
- Graceful JSON fallback if the model wraps output in markdown fences
"""

import os
import re
import json
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger("GeminiInterrogator")

# ---------------------------------------------------------------------------
# Gemini SDK setup
# ---------------------------------------------------------------------------
try:
    import google.generativeai as genai
    _api_key = os.getenv("GEMINI_API_KEY")
    if _api_key:
        genai.configure(api_key=_api_key)
        logger.info("✓ Gemini API configured")
    else:
        logger.warning("⚠ GEMINI_API_KEY not set — interrogator will return error results")
    GENAI_AVAILABLE = bool(_api_key)
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("⚠ google-generativeai not installed")

# Generation config: low temperature for deterministic forensic output
_GEN_CONFIG = {
    "temperature": 0.05,
    "top_p": 0.95,
    "top_k": 32,
    "max_output_tokens": 2048,
}

# Max frames to upload — caps cost at ~$0.013 per interrogation (5 × $0.00265/img)
MAX_FRAMES = 5

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ForensicSignals:
    splice_detected: bool = False
    gan_artifacts: bool = False
    diffusion_watermark: bool = False
    logo_inpainting: bool = False
    temporal_inconsistency: bool = False


@dataclass
class GeminiResult:
    classification: str                            # TRUSTED | FRAUD_AI_MORPHED | DIRECT_COPY | SPLICE_EDIT
    confidence: float                              # 0.0 – 1.0
    forensic_signals: ForensicSignals = field(default_factory=ForensicSignals)
    modifications_detected: List[str] = field(default_factory=list)
    recommended_action: str = "REVIEW"             # ARCHIVE | REVIEW | TAKEDOWN
    gemini_cost: float = 0.0
    raw_response: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_video_frames_for_fraud(
    frame_paths: List[str],
    source_context: str = "",
    triage_context: Optional[Dict] = None,
) -> GeminiResult:
    """
    Sends keyframes to Gemini 1.5 Pro Vision for forensic analysis.

    Args:
        frame_paths:     List of JPEG keyframe paths to upload.
        source_context:  OSINT caption / source URL text string.
        triage_context:  Dict with signals from lower layers:
                         {audio_match, hamming_distance, visual_similarity,
                          osint_piracy_intent, platform}

    Returns:
        GeminiResult with classification, forensic signals, and cost.
    """
    if not GENAI_AVAILABLE:
        return GeminiResult(
            classification="UNKNOWN",
            confidence=0.0,
            error="Gemini API not configured",
        )

    ctx = triage_context or {}

    # Sample frames
    sampled = _sample_frames(frame_paths, MAX_FRAMES)
    uploaded_files = []

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=_GEN_CONFIG,
        )

        # Build prompt parts
        parts = []

        # Upload frames via File API
        for fp in sampled:
            try:
                gfile = genai.upload_file(fp, mime_type="image/jpeg")
                uploaded_files.append(gfile)
                parts.append(gfile)
                logger.debug("  Uploaded frame: %s → %s", fp, gfile.name)
            except Exception as exc:
                logger.warning("  ⚠ Could not upload frame %s: %s", fp, exc)

        if not parts:
            logger.warning("⚠ No frames uploaded — falling back to text-only analysis")

        # Cross-modal context block
        cross_modal_block = _build_cross_modal_block(source_context, ctx)

        # System / forensic prompt
        prompt_text = _build_forensic_prompt(cross_modal_block, bool(parts))
        parts.append(prompt_text)

        # Call Gemini
        response = model.generate_content(parts)
        raw_text = response.text

        # Parse structured JSON (with markdown-fence fallback)
        parsed = _parse_json_response(raw_text)

        # Build typed result
        signals_dict = parsed.get("forensic_signals", {})
        forensic = ForensicSignals(
            splice_detected=bool(signals_dict.get("splice_detected", False)),
            gan_artifacts=bool(signals_dict.get("gan_artifacts", False)),
            diffusion_watermark=bool(signals_dict.get("diffusion_watermark", False)),
            logo_inpainting=bool(signals_dict.get("logo_inpainting", False)),
            temporal_inconsistency=bool(signals_dict.get("temporal_inconsistency", False)),
        )

        cost = len(uploaded_files) * 0.00265  # Gemini 1.5 Pro image pricing
        logger.info(
            "✓ Gemini interrogation complete: %s (confidence=%.2f, cost=$%.5f)",
            parsed.get("classification", "UNKNOWN"),
            float(parsed.get("confidence", 0.0)),
            cost,
        )

        return GeminiResult(
            classification=parsed.get("classification", "UNKNOWN"),
            confidence=float(parsed.get("confidence", 0.0)),
            forensic_signals=forensic,
            modifications_detected=parsed.get("modifications_detected", []),
            recommended_action=parsed.get("recommended_action", "REVIEW"),
            gemini_cost=cost,
            raw_response=raw_text,
        )

    except Exception as exc:
        logger.error("✗ Gemini interrogation failed: %s", exc)
        return GeminiResult(
            classification="UNKNOWN",
            confidence=0.0,
            error=str(exc),
        )

    finally:
        # Always clean up uploaded File API resources to avoid quota leak
        for gfile in uploaded_files:
            try:
                genai.delete_file(gfile.name)
            except Exception:
                pass  # Best-effort cleanup


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sample_frames(paths: List[str], n: int) -> List[str]:
    """Returns n evenly-spaced paths from the list."""
    if not paths:
        return []
    if len(paths) <= n:
        return paths
    step = len(paths) // n
    return [paths[i * step] for i in range(n)]


def _build_cross_modal_block(source_context: str, ctx: Dict) -> str:
    """Formats the cross-modal signal context block injected into the prompt."""
    lines = []
    if source_context:
        lines.append(f"Source / caption: {source_context}")
    if "platform" in ctx:
        lines.append(f"Platform: {ctx['platform']}")
    if "hamming_distance" in ctx:
        lines.append(f"Visual Hamming distance to nearest registered asset: {ctx['hamming_distance']}/64")
    if "visual_similarity" in ctx:
        lines.append(f"Visual similarity: {ctx['visual_similarity']:.1f}%")
    if "audio_match" in ctx:
        lines.append(f"Audio fingerprint match: {'YES' if ctx['audio_match'] else 'NO'}")
    if "osint_piracy_intent" in ctx:
        score = ctx["osint_piracy_intent"]
        level = "HIGH" if score > 0.6 else "MODERATE" if score > 0.3 else "LOW"
        lines.append(f"OSINT piracy intent score: {score:.2f} ({level})")
    return "\n".join(lines) if lines else "No additional context."


def _build_forensic_prompt(cross_modal_block: str, has_frames: bool) -> str:
    frame_note = (
        "Analyse the attached video keyframes." if has_frames
        else "No frames could be uploaded — reason from the context signals below only."
    )
    return f"""You are an expert digital forensics AI embedded in a Security Operations Centre.

{frame_note}

Cross-modal signals from upstream pipeline layers:
{cross_modal_block}

Detect any of the following forensic indicators:
- Temporal splicing / jump cuts inconsistent with natural recording
- GAN / diffusion model artefacts (unnatural textures, hair, background bleed)
- Diffusion watermarks or spectral patterns
- Logo inpainting or overlaid brand substitution
- Temporal flickering or frame inconsistency suggesting re-encoding

Return ONLY a raw JSON object — do NOT wrap in markdown fences.
Schema:
{{
  "classification": "TRUSTED | FRAUD_AI_MORPHED | DIRECT_COPY | SPLICE_EDIT",
  "confidence": <float 0.0-1.0>,
  "forensic_signals": {{
    "splice_detected": <bool>,
    "gan_artifacts": <bool>,
    "diffusion_watermark": <bool>,
    "logo_inpainting": <bool>,
    "temporal_inconsistency": <bool>
  }},
  "modifications_detected": ["<description of each anomaly found>"],
  "recommended_action": "ARCHIVE | REVIEW | TAKEDOWN"
}}"""


def _parse_json_response(text: str) -> Dict:
    """
    Parses Gemini JSON output.
    Handles two cases:
    1. Clean JSON (preferred path).
    2. JSON wrapped in ```json ... ``` markdown fences (graceful fallback).
    """
    # Attempt 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: strip markdown fences and retry
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Attempt 3: find first { ... } block
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error("✗ Could not parse Gemini JSON response:\n%s", text[:500])
    return {
        "classification": "UNKNOWN",
        "confidence": 0.0,
        "forensic_signals": {},
        "modifications_detected": ["JSON parse failure"],
        "recommended_action": "REVIEW",
    }
