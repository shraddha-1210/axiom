import requests
import time
import sys
import subprocess

API_URL = "http://localhost:8000"

def wait_for_api():
    print("Waiting for API to boot...")
    for _ in range(10):
        try:
            r = requests.get(f"{API_URL}/health")
            if r.status_code == 200:
                print(f"API is UP: {r.json()}")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    return False

def create_dummy_video():
    print("Creating dummy video payload for FFmpeg triage testing...")
    # Use ffmpeg to generate a 2-second black video
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", "color=c=black:s=320x240:r=30",
        "-t", "2", "-y", "/tmp/media/dummy.mp4"
    ], capture_output=True)
    return "/tmp/media/dummy.mp4"

def test_pipeline():
    if not wait_for_api():
        print("API failed to boot.")
        sys.exit(1)
        
    dummy_filepath = create_dummy_video()
    
    print("\n--- Testing Layer 1: Upload Source / C2PA ---")
    files = {'file': ('dummy.mp4', open(dummy_filepath, 'rb'), 'video/mp4')}
    r1 = requests.post(f"{API_URL}/api/upload-source?asset_id=vid_123&uploader=shivaa", files=files)
    print(r1.status_code, r1.json())
    
    print("\n--- Testing Layer 2: pHash Triage & Upstash Caching ---")
    # Triage expects the video to already be in /tmp/media
    r2 = requests.post(f"{API_URL}/api/triage?video_filename=dummy.mp4")
    print(r2.status_code, r2.json())
    
    print("\n--- Testing Layer 3: Gemini & Pinecone & NeonDB ---")
    r3 = requests.post(f"{API_URL}/api/interrogate?asset_id=vid_123&context=testing")
    print(r3.status_code, r3.json())
    
    print("\n--- Testing Async Scrapers ---")
    r4 = requests.get(f"{API_URL}/api/scrapers/trigger")
    print(r4.status_code, r4.json())
    
    print("\nAll tests completed.")

if __name__ == "__main__":
    test_pipeline()
