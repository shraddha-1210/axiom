import os
import io
import base64
import requests
import json
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from PIL import Image


class PaliGemmaDecision(Enum):
    ESCALATE_LAYER3 = "ESCALATE_LAYER3"
    ARCHIVE = "ARCHIVE"


@dataclass
class PaliGemmaResult:
    decision: PaliGemmaDecision
    confidence_score: float
    visual_coherence: float
    compression_artifacts: bool
    geometric_consistency: float
    temporal_flickering: bool
    osint_piracy_intent: float
    cost: float
    details: Dict


def _detect_temporal_flickering(frame_paths: List[str], threshold: float = 0.25) -> bool:
    """
    Detects temporal flickering by measuring mean brightness deltas between
    consecutive frames.

    A sharp jump in brightness between adjacent keyframes (> threshold * 255
    gray levels) is a strong signal of re-encoding artifacts or deepfake
    frame injection.

    Args:
        frame_paths: Ordered list of extracted keyframe paths.
        threshold:   Fraction of 255 above which a delta is a flicker (default 0.25 → ~64 levels).

    Returns:
        True if any consecutive frame pair exceeds the brightness-delta threshold.
    """
    if len(frame_paths) < 2:
        return False

    try:
        import numpy as np
        brightness_values = []
        for fp in frame_paths:
            with Image.open(fp).convert("L") as img:
                arr = np.asarray(img, dtype=np.float32)
                brightness_values.append(float(arr.mean()))

        abs_threshold = threshold * 255.0
        for i in range(len(brightness_values) - 1):
            if abs(brightness_values[i + 1] - brightness_values[i]) > abs_threshold:
                return True
        return False

    except Exception as e:
        print(f"✗ Temporal flicker detection error: {e}")
        return False


def run_paligemma_triage(frame_paths: List[str], osint_context: Dict = None) -> PaliGemmaResult:
    print(f"Running PaliGemma triage on {len(frame_paths)} frames...")

    if not frame_paths:
        return _fallback_mock()

    paligemma_url = os.getenv("PALIGEMMA_URL")
    if not paligemma_url:
        print("Missing PALIGEMMA_URL config. Falling back.")
        return _fallback_mock()

    # Take the middle frame. PaliGemma is a VLM taking a single frame.
    target_frame = frame_paths[len(frame_paths) // 2]

    try:
        # Resize to save bandwidth / VRAM
        with Image.open(target_frame) as img:
            img = img.convert("RGB")
            img.thumbnail((384, 384))
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")

        payload = {
            "image_base64": encoded_string,
            "prompt": "Detect: visual coherence, compression artifacts, geometric irregularities. Return raw JSON."
        }
        r = requests.post(paligemma_url, json=payload, timeout=25)

        if r.status_code == 200:
            data = r.json()
            # If the Colab endpoint returns a dict with 'result', grab it
            analysis_text = data.get("result", "")
            if isinstance(data, dict) and "visual_coherence" in data:
                parsed = data
            else:
                # Heuristic extraction if the endpoint returns plain text
                parsed = {
                    "visual_coherence": 0.3 if "incoherent" in analysis_text.lower() else 0.8,
                    "compression_artifacts": "artifact" in analysis_text.lower(),
                    "geometric_consistency": 0.4 if "irregular" in analysis_text.lower() else 0.9,
                }

            visual_coherence = float(parsed.get("visual_coherence", 0.75))
            geometric_consistency = float(parsed.get("geometric_consistency", 0.8))
            compression_artifacts = bool(parsed.get("compression_artifacts", False))

            # Weighted confidence score 0-100
            score = (visual_coherence * 40) + (geometric_consistency * 40) + ((0 if compression_artifacts else 1) * 20)

            decision = PaliGemmaDecision.ESCALATE_LAYER3 if score >= 65 else PaliGemmaDecision.ARCHIVE

            # Fixed: compute temporal flickering from actual frame brightness deltas
            # (previously hardcoded False in both live and mock paths)
            temporal_flickering = _detect_temporal_flickering(frame_paths)

            print(f"✓ PaliGemma inference returned Score: {score:.1f}/100")
            return PaliGemmaResult(
                decision=decision,
                confidence_score=score,
                visual_coherence=visual_coherence,
                compression_artifacts=compression_artifacts,
                geometric_consistency=geometric_consistency,
                temporal_flickering=temporal_flickering,
                osint_piracy_intent=0.5,
                cost=0.002,
                details={"api_raw": parsed}
            )
        else:
            print(f"PaliGemma API Error {r.status_code}: {r.text}")
            return _fallback_mock()

    except Exception as e:
        print(f"✗ PaliGemma request failed: {e}")
        return _fallback_mock()


def _fallback_mock() -> PaliGemmaResult:
    return PaliGemmaResult(
        decision=PaliGemmaDecision.ARCHIVE,
        confidence_score=50.0,
        visual_coherence=0.7,
        compression_artifacts=False,
        geometric_consistency=0.8,
        temporal_flickering=False,   # acceptable in mock — no frames available
        osint_piracy_intent=0.3,
        cost=0.000,
        details={"mocked": True, "error": "PaliGemma endpoint unavailable"}
    )
