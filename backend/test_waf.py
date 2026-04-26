from fastapi.testclient import TestClient
from main import app
from waf import MALICIOUS_IPS, GEO_BLOCKED_IPS

client = TestClient(app)

def test_waf_rate_limit():
    print("Testing Rate Limiter (5 requests/min allowed)...")
    success_count = 0
    blocked = False
    for i in range(7):
        response = client.post(
            "/api/upload-source?asset_id=vid_rate&uploader=test", 
            files={'file': ('dummy.mp4', b"dummy content", 'video/mp4')}
        )
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            print(f"Request {i+1} blocked: 429 Rate Limit Exceeded")
            blocked = True
            
    assert success_count <= 5, "WAF failed to rate limit!"
    assert blocked, "WAF did not return 429"
    print("Rate Limiter working correctly.\n")

def test_waf_malicious_ip():
    print("Testing IP Reputation Blocker...")
    test_ip = list(MALICIOUS_IPS)[0]
    response = client.post(
        "/api/upload-source?asset_id=vid_ip&uploader=test", 
        files={'file': ('dummy.mp4', b"dummy content", 'video/mp4')},
        headers={"x-forwarded-for": test_ip}
    )
    assert response.status_code == 403
    assert "WAF Blocked" in response.json()["detail"]
    print("IP Reputation Blocker working correctly (403 Forbidden).\n")

def test_waf_geo_block():
    print("Testing Geo-Blocker...")
    test_ip = list(GEO_BLOCKED_IPS)[0]
    response = client.post(
        "/api/upload-source?asset_id=vid_geo&uploader=test", 
        files={'file': ('dummy.mp4', b"dummy content", 'video/mp4')},
        headers={"x-forwarded-for": test_ip}
    )
    assert response.status_code == 403
    assert "Region not allowed" in response.json()["detail"]
    print("Geo-Blocker working correctly (403 Forbidden).\n")

if __name__ == "__main__":
    test_waf_rate_limit()
    test_waf_malicious_ip()
    test_waf_geo_block()
    print("All WAF Simulator Tests Passed!")
