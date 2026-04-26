import os
import imagehash
from PIL import Image
import ffmpeg
import redis

# Initialize Upstash Redis Connection
upstash_url = os.getenv("UPSTASH_REDIS_URL")
r = None
if upstash_url:
    try:
        r = redis.Redis.from_url(upstash_url)
    except Exception as e:
        print(f"Error connecting to Upstash Redis: {e}")

def extract_keyframes(video_path: str, output_dir: str):
    """
    Extracts purely I-frames (keyframes) using FFmpeg to save local compute.
    """
    os.makedirs(output_dir, exist_ok=True)
    try:
        (
            ffmpeg
            .input(video_path)
            .filter('select', 'eq(pict_type,I)')
            .output(os.path.join(output_dir, 'frame_%03d.jpg'), vsync='vfr', qscale=2)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.jpg')]
    except ffmpeg.Error as e:
        print('FFmpeg Error:', e.stderr.decode('utf8'))
        return []

def is_duplicate_hash(hsh: str) -> bool:
    if not r: return False
    return r.exists(f"phash:{hsh}") > 0

def cache_hash(hsh: str):
    if not r: return
    r.set(f"phash:{hsh}", "1")

def compute_phash_for_frames(frame_paths: list):
    """
    Computes perceptual hashes (dHash and aHash) for visual similarity matching.
    """
    hashes = []
    for fp in frame_paths:
        try:
            img = Image.open(fp).convert('L') # Grayscale
            dhash = str(imagehash.dhash(img, hash_size=8))
            ahash = str(imagehash.average_hash(img, hash_size=8))
            
            hashes.append({
                "frame": os.path.basename(fp),
                "dhash": dhash,
                "ahash": ahash,
                "is_cached_hit": is_duplicate_hash(dhash) or is_duplicate_hash(ahash)
            })
            
            # Upsert for future runs
            cache_hash(dhash)
            cache_hash(ahash)
            
        except Exception as e:
            print(f"Error hashing {fp}: {e}")
    return hashes

def calculate_hamming_distance(hash1: str, hash2: str) -> int:
    h1 = imagehash.hex_to_hash(hash1)
    h2 = imagehash.hex_to_hash(hash2)
    return h1 - h2
