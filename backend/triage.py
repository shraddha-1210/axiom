"""
Layer 2: Heuristic Filter & pHash Triage Engine
Cost Optimizer - Filters 85-90% of scraped media at near-zero cost

This module implements:
1. FFmpeg I-frame extraction (keyframes only)
2. Visual pHash (dHash + aHash) computation
3. Audio fingerprinting with Chromaprint
4. Redis cache-based deduplication
5. Hamming distance-based routing decisions
"""

import os
import uuid
import struct
import base64
import imagehash
from PIL import Image
import ffmpeg
import redis
import subprocess
import json
import hashlib
from typing import List, Dict, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

# Initialize Upstash Redis Connection
upstash_url = os.getenv("UPSTASH_REDIS_URL")
r = None
if upstash_url:
    try:
        r = redis.Redis.from_url(upstash_url, decode_responses=True)
        print("✓ Connected to Upstash Redis for Layer 2 cache")
    except Exception as e:
        print(f"✗ Error connecting to Upstash Redis: {e}")


class TriageDecision(Enum):
    """Routing decisions based on Hamming distance thresholds"""
    BLOCK = "BLOCK"  # Hamming 0-8: Direct copy, auto-block
    ESCALATE_PALIGEMMA = "ESCALATE_PALIGEMMA"  # Hamming 9-20: Moderate similarity
    ESCALATE_VERTEX = "ESCALATE_VERTEX"  # Hamming 21-35: Significant edit
    DISCARD = "DISCARD"  # Hamming >35: Unrelated content


@dataclass
class TriageResult:
    """Result of Layer 2 triage analysis"""
    decision: TriageDecision
    hamming_distance: int
    visual_similarity: float
    audio_match: bool
    matched_asset_id: Optional[str]
    confidence: float
    cost: float
    details: Dict


# ============================================================================
# LAYER 2.1: FFmpeg I-Frame Extraction
# ============================================================================

def extract_keyframes(video_path: str, output_dir: str, max_frames: int = 30) -> List[str]:
    """
    Extracts I-frames (keyframes) only using FFmpeg for cost optimization.
    A 60fps 30-second video has 1,800 frames but only ~15-30 I-frames.
    
    Args:
        video_path: Path to input video file
        output_dir: Directory to save extracted frames
        max_frames: Maximum number of frames to extract (default: 30)
    
    Returns:
        List of paths to extracted frame images
    """
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Extract I-frames only (keyframes)
        (
            ffmpeg
            .input(video_path)
            .filter('select', 'eq(pict_type,I)')
            .output(
                os.path.join(output_dir, 'frame_%04d.jpg'),
                vsync='vfr',
                qscale=2,
                frames=max_frames
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        
        frames = sorted([
            os.path.join(output_dir, f) 
            for f in os.listdir(output_dir) 
            if f.endswith('.jpg')
        ])
        
        print(f"✓ Extracted {len(frames)} I-frames from {os.path.basename(video_path)}")
        return frames
        
    except ffmpeg.Error as e:
        print(f'✗ FFmpeg Error: {e.stderr.decode("utf8") if e.stderr else str(e)}')
        return []


def extract_audio_track(video_path: str, output_path: str) -> Optional[str]:
    """
    Extracts audio track from video for fingerprinting.
    Converts to mono WAV at 11025 Hz for Chromaprint compatibility.
    
    Args:
        video_path: Path to input video file
        output_path: Path to save extracted audio (WAV format)
    
    Returns:
        Path to extracted audio file or None if extraction fails
    """
    try:
        (
            ffmpeg
            .input(video_path)
            .output(
                output_path,
                vn=None,  # No video
                ar=11025,  # Sample rate for Chromaprint
                ac=1,  # Mono channel
                format='wav'
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        
        print(f"✓ Extracted audio track to {os.path.basename(output_path)}")
        return output_path
        
    except ffmpeg.Error as e:
        print(f'✗ Audio extraction error: {e.stderr.decode("utf8") if e.stderr else str(e)}')
        return None


# ============================================================================
# LAYER 2.2: Visual pHash Computation (dHash + aHash)
# ============================================================================

def compute_phash_for_frame(frame_path: str) -> Dict[str, str]:
    """
    Computes both dHash and aHash for a single frame.
    
    dHash (Difference Hash): Detects structural similarity
    aHash (Average Hash): Detects brightness-invariant similarity
    
    Args:
        frame_path: Path to frame image
    
    Returns:
        Dictionary with dhash and ahash values
    """
    try:
        img = Image.open(frame_path).convert('L')  # Grayscale
        
        # 64-bit dHash (structural similarity)
        dhash = str(imagehash.dhash(img, hash_size=8))
        
        # 64-bit aHash (brightness-invariant)
        ahash = str(imagehash.average_hash(img, hash_size=8))
        
        return {
            "frame": os.path.basename(frame_path),
            "dhash": dhash,
            "ahash": ahash
        }
        
    except Exception as e:
        print(f"✗ Error hashing {frame_path}: {e}")
        return {"frame": os.path.basename(frame_path), "dhash": None, "ahash": None}


def compute_phash_for_frames(frame_paths: List[str]) -> List[Dict]:
    """
    Computes perceptual hashes for all frames.
    
    Args:
        frame_paths: List of paths to frame images
    
    Returns:
        List of hash dictionaries with cache hit information
    """
    hashes = []
    
    for fp in frame_paths:
        hash_data = compute_phash_for_frame(fp)
        
        if hash_data["dhash"] and hash_data["ahash"]:
            # Check if this hash exists in cache (indicates duplicate)
            dhash_cached = is_duplicate_hash(hash_data["dhash"])
            ahash_cached = is_duplicate_hash(hash_data["ahash"])
            
            hash_data["is_cached_hit"] = dhash_cached or ahash_cached
            hash_data["dhash_cached"] = dhash_cached
            hash_data["ahash_cached"] = ahash_cached
            
            # Cache these hashes for future comparisons
            cache_hash(hash_data["dhash"], "dhash")
            cache_hash(hash_data["ahash"], "ahash")
            
            hashes.append(hash_data)
    
    return hashes


# ============================================================================
# LAYER 2.3: Audio Fingerprinting with Chromaprint
# ============================================================================

def compute_audio_fingerprint(audio_path: str) -> Optional[Dict]:
    """
    Computes Chromaprint audio fingerprint using fpcalc.
    Chromaprint analyzes spectral characteristics and produces a compact
    fingerprint robust to encoding changes and bitrate compression.
    
    Args:
        audio_path: Path to audio file (WAV format)
    
    Returns:
        Dictionary with fingerprint and duration, or None if computation fails
    """
    try:
        # Use fpcalc (Chromaprint command-line tool)
        result = subprocess.run(
            ['fpcalc', '-json', audio_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            fingerprint_data = json.loads(result.stdout)
            print(f"✓ Computed audio fingerprint (duration: {fingerprint_data.get('duration', 0)}s)")
            return fingerprint_data
        else:
            print(f"✗ fpcalc error: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("✗ fpcalc not found. Install chromaprint: apt-get install libchromaprint-tools")
        return None
    except subprocess.TimeoutExpired:
        print("✗ Audio fingerprinting timed out")
        return None
    except Exception as e:
        print(f"✗ Audio fingerprinting error: {e}")
        return None


def compare_audio_fingerprints(fp1: str, fp2: str) -> float:
    """
    Compares two Chromaprint fingerprints and returns similarity score.

    Fixed: Chromaprint fingerprints are base64-encoded arrays of 32-bit
    integers.  The previous implementation split on ',' (a comma), which
    produces meaningless single-character tokens and always returns ~0.

    Correct approach: decode each fingerprint to an int32 array, XOR
    corresponding elements, count matching bits, and express as a ratio
    of total bits (bit-level Jaccard similarity on the overlapping prefix).

    Args:
        fp1: Base64-encoded Chromaprint fingerprint string
        fp2: Base64-encoded Chromaprint fingerprint string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not fp1 or not fp2:
        return 0.0

    try:
        # Chromaprint base64 uses standard alphabet with possible padding
        def _decode(fp: str) -> list:
            # Add padding if needed
            padded = fp + "=" * (4 - len(fp) % 4) if len(fp) % 4 else fp
            raw = base64.b64decode(padded)
            n = len(raw) // 4
            return list(struct.unpack(f"{n}I", raw[:n * 4]))

        ints1 = _decode(fp1)
        ints2 = _decode(fp2)

        # Compare only the overlapping prefix
        compare_len = min(len(ints1), len(ints2), 120)  # ~4s of audio coverage
        if compare_len == 0:
            return 0.0

        matching_bits = 0
        total_bits = compare_len * 32
        for i in range(compare_len):
            differing = bin(ints1[i] ^ ints2[i]).count('1')
            matching_bits += 32 - differing

        return matching_bits / total_bits

    except Exception as e:
        print(f"✗ Audio fingerprint comparison error: {e}")
        return 0.0


# ============================================================================
# LAYER 2.4: Redis Cache Operations
# ============================================================================

def is_duplicate_hash(hsh: str) -> bool:
    """
    Checks if a hash exists in the **scan-dedup** Redis namespace.

    Fixed: uses the 'scanphash:' prefix instead of 'phash:' to avoid
    namespace collision with registered-asset keys ('asset:id:dhash').
    Previously, re-scanning the same video would always show cache hits
    because 'phash:{hash}' was populated on the first run and then matched
    on subsequent runs, producing false duplicate signals unrelated to any
    protected registered asset.

    Args:
        hsh: Hash string to check

    Returns:
        True if hash exists in scan-dedup cache, False otherwise
    """
    if not r or not hsh:
        return False

    try:
        return r.exists(f"scanphash:{hsh}") > 0
    except Exception as e:
        print(f"✗ Redis check error: {e}")
        return False


def cache_hash(hsh: str, hash_type: str = "dhash", ttl: int = 2592000):
    """
    Stores a hash in the scan-dedup Redis namespace with TTL (default: 30 days).

    Args:
        hsh: Hash string to cache
        hash_type: Type of hash (dhash, ahash, audio)
        ttl: Time to live in seconds (default: 30 days)
    """
    if not r or not hsh:
        return

    try:
        # Fixed: use 'scanphash:' namespace (separate from 'asset:id:dhash')
        key = f"scanphash:{hsh}"
        r.setex(key, ttl, hash_type)
    except Exception as e:
        print(f"✗ Redis cache error: {e}")


def get_registered_asset_hashes() -> List[Dict]:
    """
    Retrieves all registered asset hashes from Redis cache.
    
    Returns:
        List of dictionaries containing asset_id and hash values
    """
    if not r:
        return []
    
    try:
        # Scan for all asset hash keys
        asset_keys = []
        cursor = 0
        
        while True:
            cursor, keys = r.scan(cursor, match="asset:*:dhash", count=100)
            asset_keys.extend(keys)
            if cursor == 0:
                break
        
        assets = []
        for key in asset_keys:
            asset_id = key.split(':')[1]
            dhash = r.get(key)
            ahash = r.get(f"asset:{asset_id}:ahash")
            audio_fp = r.get(f"asset:{asset_id}:audio_fp")
            
            if dhash:
                assets.append({
                    "asset_id": asset_id,
                    "dhash": dhash,
                    "ahash": ahash,
                    "audio_fp": audio_fp
                })
        
        return assets
        
    except Exception as e:
        print(f"✗ Error retrieving registered assets: {e}")
        return []


# 1 year TTL for registered protected-asset hashes.
_ASSET_HASH_TTL = 60 * 60 * 24 * 365


def store_asset_hashes(asset_id: str, dhash: str, ahash: str, audio_fp: Optional[str] = None):
    """
    Stores registered asset hashes in Redis for future comparisons.

    Fixed: added 1-year TTL to prevent unbounded Redis memory growth on
    the Upstash free tier. Previously these keys had no expiry.

    Args:
        asset_id: Unique identifier for the asset
        dhash: Difference hash value
        ahash: Average hash value
        audio_fp: Audio fingerprint (optional)
    """
    if not r:
        return

    try:
        r.setex(f"asset:{asset_id}:dhash", _ASSET_HASH_TTL, dhash)
        r.setex(f"asset:{asset_id}:ahash", _ASSET_HASH_TTL, ahash)

        if audio_fp:
            r.setex(f"asset:{asset_id}:audio_fp", _ASSET_HASH_TTL, audio_fp)

        print(f"✓ Stored hashes for asset {asset_id} (TTL: 1 year)")

    except Exception as e:
        print(f"✗ Error storing asset hashes: {e}")


# ============================================================================
# LAYER 2.5: Hamming Distance Calculation & Routing
# ============================================================================

def calculate_hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculates Hamming distance between two perceptual hashes.
    Hamming distance = number of differing bits.
    
    Args:
        hash1: First hash string
        hash2: Second hash string
    
    Returns:
        Hamming distance (0 = identical, 64 = completely different)
    """
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except Exception as e:
        print(f"✗ Hamming distance calculation error: {e}")
        return 64  # Maximum distance


def find_best_match(scraped_hashes: List[Dict], registered_assets: List[Dict]) -> Tuple[Optional[str], int, float]:
    """
    Finds the best matching registered asset for scraped content.
    
    Args:
        scraped_hashes: List of hashes from scraped video frames
        registered_assets: List of registered asset hashes from cache
    
    Returns:
        Tuple of (matched_asset_id, min_hamming_distance, similarity_percentage)
    """
    if not scraped_hashes or not registered_assets:
        return None, 64, 0.0
    
    best_match_id = None
    min_distance = 64
    
    # Compare each scraped frame against all registered assets
    for scraped in scraped_hashes:
        if not scraped.get("dhash"):
            continue
        
        for asset in registered_assets:
            # Compare dHash
            dhash_dist = calculate_hamming_distance(scraped["dhash"], asset["dhash"])
            
            # Compare aHash
            ahash_dist = calculate_hamming_distance(
                scraped.get("ahash", "0" * 16),
                asset.get("ahash", "0" * 16)
            )
            
            # Use minimum distance from both hash types
            current_dist = min(dhash_dist, ahash_dist)
            
            if current_dist < min_distance:
                min_distance = current_dist
                best_match_id = asset["asset_id"]
    
    # Calculate similarity percentage
    similarity = ((64 - min_distance) / 64) * 100
    
    return best_match_id, min_distance, similarity


def determine_triage_decision(hamming_distance: int) -> TriageDecision:
    """
    Determines routing decision based on Hamming distance threshold.
    
    Routing Matrix:
    - Hamming 0-8 (>95% match): BLOCK - Direct copy
    - Hamming 9-20 (80-95% match): ESCALATE_PALIGEMMA - Moderate similarity
    - Hamming 21-35 (50-80% match): ESCALATE_VERTEX - Significant edit
    - Hamming >35 (<50% match): DISCARD - Unrelated content
    
    Args:
        hamming_distance: Calculated Hamming distance
    
    Returns:
        TriageDecision enum value
    """
    if hamming_distance <= 8:
        return TriageDecision.BLOCK
    elif hamming_distance <= 20:
        return TriageDecision.ESCALATE_PALIGEMMA
    elif hamming_distance <= 35:
        return TriageDecision.ESCALATE_VERTEX
    else:
        return TriageDecision.DISCARD


def calculate_cost(decision: TriageDecision) -> float:
    """
    Returns the processing cost for each triage decision.
    
    Args:
        decision: TriageDecision enum value
    
    Returns:
        Cost in USD
    """
    cost_map = {
        TriageDecision.BLOCK: 0.0001,
        TriageDecision.ESCALATE_PALIGEMMA: 0.002,
        TriageDecision.ESCALATE_VERTEX: 0.10,  # Average of $0.04-$0.15
        TriageDecision.DISCARD: 0.0001
    }
    return cost_map.get(decision, 0.0)


# ============================================================================
# LAYER 2.6: Complete Triage Pipeline
# ============================================================================

def run_complete_triage(video_path: str, asset_id: str = None) -> TriageResult:
    """
    Executes complete Layer 2 triage pipeline:
    1. Extract I-frames
    2. Compute visual pHash (dHash + aHash)
    3. Extract and fingerprint audio
    4. Compare against registered assets
    5. Determine routing decision
    
    Args:
        video_path: Path to video file to analyze
        asset_id: Optional asset ID for tracking
    
    Returns:
        TriageResult with decision and analysis details
    """
    print(f"\n{'='*60}")
    print(f"LAYER 2 TRIAGE: {os.path.basename(video_path)}")
    print(f"{'='*60}")
    
    # Generate unique ID for this analysis.
    # Fixed: replaced MD5 with uuid4 — MD5 is deprecated for security-sensitive use.
    if not asset_id:
        asset_id = uuid.uuid4().hex[:12]
    
    # Step 1: Extract keyframes
    frame_dir = f"/tmp/media/frames_{asset_id}"
    frames = extract_keyframes(video_path, frame_dir)
    
    if not frames:
        return TriageResult(
            decision=TriageDecision.DISCARD,
            hamming_distance=64,
            visual_similarity=0.0,
            audio_match=False,
            matched_asset_id=None,
            confidence=0.0,
            cost=0.0001,
            details={"error": "Failed to extract frames"}
        )
    
    # Step 2: Compute visual hashes
    print(f"\n[Visual Analysis]")
    scraped_hashes = compute_phash_for_frames(frames)
    
    # Step 3: Extract and fingerprint audio
    print(f"\n[Audio Analysis]")
    audio_path = f"/tmp/media/audio_{asset_id}.wav"
    audio_file = extract_audio_track(video_path, audio_path)
    audio_fingerprint = None
    
    if audio_file:
        audio_fingerprint = compute_audio_fingerprint(audio_file)
    
    # Step 4: Compare against registered assets
    print(f"\n[Similarity Matching]")
    registered_assets = get_registered_asset_hashes()
    
    if not registered_assets:
        print("⚠ No registered assets found in cache")
        matched_id, hamming_dist, similarity = None, 64, 0.0
    else:
        matched_id, hamming_dist, similarity = find_best_match(scraped_hashes, registered_assets)
        print(f"✓ Best match: {matched_id or 'None'} (Hamming: {hamming_dist}, Similarity: {similarity:.1f}%)")
    
    # Step 5: Determine routing decision
    decision = determine_triage_decision(hamming_dist)
    cost = calculate_cost(decision)
    
    # Calculate confidence based on multiple factors
    confidence = similarity / 100.0
    
    # Check audio match if available
    audio_match = False
    if audio_fingerprint and matched_id:
        # Compare audio fingerprints
        matched_audio_fp = r.get(f"asset:{matched_id}:audio_fp") if r else None
        if matched_audio_fp and audio_fingerprint.get('fingerprint'):
            audio_similarity = compare_audio_fingerprints(
                audio_fingerprint['fingerprint'],
                matched_audio_fp
            )
            audio_match = audio_similarity > 0.85
            confidence = (confidence + audio_similarity) / 2  # Average visual and audio confidence
    
    print(f"\n[Triage Decision]")
    print(f"Decision: {decision.value}")
    print(f"Confidence: {confidence*100:.1f}%")
    print(f"Cost: ${cost:.6f}")
    print(f"{'='*60}\n")
    
    return TriageResult(
        decision=decision,
        hamming_distance=hamming_dist,
        visual_similarity=similarity,
        audio_match=audio_match,
        matched_asset_id=matched_id,
        confidence=confidence,
        cost=cost,
        details={
            "frames_analyzed": len(frames),
            "hashes_computed": len(scraped_hashes),
            "audio_fingerprinted": audio_fingerprint is not None,
            "registered_assets_checked": len(registered_assets)
        }
    )
