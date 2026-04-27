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

def run_paligemma_triage(frame_paths: List[str], osint_context: Dict = None) -> PaliGemmaResult:
    print(f"Running PaliGemma triage on {len(frame_paths)} frames...")
    
    if not frame_paths:
        return _fallback_mock()

    paligemma_url = os.getenv("PALIGEMMA_URL")
    if not paligemma_url:
        print("Missing PALIGEMMA_URL config. Falling back.")
        return _fallback_mock()

    # Take the middle frame. Paligemma is a VLM taking a single frame
    target_frame = frame_paths[len(frame_paths) // 2]
    
    try:
        # Resize to save bandwidth / VRAM 
        with Image.open(target_frame) as img:
            img = img.convert("RGB")
            img.thumbnail((384, 384))
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
        payload = {"image_base64": encoded_string, "prompt": "Detect: visual coherence, compression artifacts, geometric irregularities. Return raw JSON."}
        r = requests.post(paligemma_url, json=payload, timeout=25)
        
        if r.status_code == 200:
            data = r.json()
            # Depending on how the colab is coded, if it returns dict with 'result', grab it
            analysis_text = data.get("result", "")
            if isinstance(data, dict) and "visual_coherence" in data:
                parsed = data
            else:
                # Basic heuristic extraction if it returns string
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
            
            print(f"✓ PaliGemma inference returned Score: {score:.1f}/100")
            return PaliGemmaResult(
                decision=decision,
                confidence_score=score,
                visual_coherence=visual_coherence,
                compression_artifacts=compression_artifacts,
                geometric_consistency=geometric_consistency,
                temporal_flickering=False,
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
        temporal_flickering=False,
        osint_piracy_intent=0.3,
        cost=0.000,
        details={"mocked": True, "error": "PaliGemma endpoint unavailable"}
    )

