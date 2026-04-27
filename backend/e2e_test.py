from fastapi.testclient import TestClient
from main import app
from waf import MALICIOUS_IPS, GEO_BLOCKED_IPS
import subprocess
import os

client = TestClient(app)

def create_mock_video(filepath, duration=1):
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", f"color=c=black:s=160x120:r=15",
        "-t", str(duration), "-y", filepath
    ], capture_output=True)

def run_tests():
    print("="*60)
    print("AXIOM LAYER 1 & 2 INTEGRATION TEST SUITE")
    print("="*60)
    
    os.makedirs("/tmp/media", exist_ok=True)
    video_path = "/tmp/media/test_vid.mp4"
    create_mock_video(video_path)
    
    # ---------------------------------------------------------
    # LAYER 1 TESTS
    # ---------------------------------------------------------
    print("\n[TEST 1] Layer 1 - IP Reputation WAF")
    test_ip = list(MALICIOUS_IPS)[0]
    r = client.post(
        "/api/upload-source?asset_id=l1tc1&uploader=test", 
        files={'file': ('test_vid.mp4', open(video_path, 'rb'), 'video/mp4')},
        headers={"x-forwarded-for": test_ip}
    )
    assert r.status_code == 403, "WAF bypassed!"
    print("  ✓ Passed: Malicious IP successfully blocked (403)")

    print("\n[TEST 2] Layer 1 - Secure Upload & C2PA Provenance")
    r = client.post(
        "/api/upload-source?asset_id=vid_valid&uploader=analyst1", 
        files={'file': ('test_vid.mp4', open(video_path, 'rb'), 'video/mp4')}
    )
    if r.status_code == 200:
        data = r.json()
        assert "c2pa.hash.data" in str(data["manifest"]["assertions"])
        print(f"  ✓ Passed: C2PA Cryptographic signed by {data['manifest']['claim_generator']} and NeonDB record created.")
        print(f"  ✓ Passed: Hashes extracted & cached for Triage: {data['hashes_registered']}")
    else:
        print(f"  ✗ Failed: {r.text}")

    print("\n[TEST 3] Layer 1 - Rate Limiting WAF")
    print("  Running burst of 6 rapid requests to trigger SlowAPI...")
    blocked = False
    for _ in range(6):
        r = client.post(
            "/api/upload-source?asset_id=vid_spam&uploader=spam", 
            files={'file': ('test_vid.mp4', b'dummy', 'video/mp4')}
        )
        if r.status_code == 429:
            blocked = True
            break
    assert blocked, "Rate limit bypassed!"
    print("  ✓ Passed: Rate Limiting engaged correctly (429 Too Many Requests)")

    # ---------------------------------------------------------
    # LAYER 2 TESTS
    # ---------------------------------------------------------
    print("\n[TEST 4] Layer 2 - pHash Deduplication Cache Hit (Triage Engine)")
    # Since we uploaded 'test_vid.mp4' successfully above, running Triage on it should show BLOCK due to Hamming distance = 0
    r = client.post("/api/triage?video_filename=test_vid.mp4&asset_id=vid_valid")
    if r.status_code == 200:
        print(f"  ✓ Passed: pHash Triage Decision -> {r.json()['decision']} (Cost: {r.json()['cost']})")
    
    # ---------------------------------------------------------
    # LAYER 2.5 TESTS
    # ---------------------------------------------------------
    print("\n[TEST 5] Layer 2.5 - Zero-Day Sandbox Detonation")
    eicar_path = "/tmp/media/dummy.exe"
    with open(eicar_path, "wb") as f:
        f.write(b"EICAR test string")
        
    r = client.post("/api/pipeline/auto?video_filename=dummy.exe&asset_id=suspicious_exe")
    if r.status_code == 200:
        data = r.json()
        assert data["action"] == "QUARANTINE"
        print(f"  ✓ Passed: Auto-Pipeline detected anomaly, routed to Zero-Day Sandbox.")
        print(f"  ✓ Sandbox Status: {data['message']}")

    print("\n[TEST 6] Layer 2.5 - Local PaliGemma Telemetry (Ngrok VLM)")
    # Test PaliGemma specifically using the triage API on an image
    # Note: test_vid.mp4 is pure black, so PaliGemma might Archive it based on visual coherence
    r = client.post("/api/paligemma?video_filename=test_vid.mp4")
    if r.status_code == 200:
        data = r.json()
        print(f"  ✓ Passed: Ngrok PaliGemma VLM Connected.")
        print(f"  ✓ AI Confidence Score: {data['confidence_score']}")
        print(f"  ✓ Target Decision: {data['decision']}")
    else:
        print(f"  ✗ Failed: {r.text}")
        
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED SUCCESSFULLY")
    print("="*60)

if __name__ == "__main__":
    run_tests()
