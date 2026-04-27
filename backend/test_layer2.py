import os
from PIL import Image
from paligemma_triage import run_paligemma_triage
from sandbox_detonator import run_zeroday_sandbox

def test_paligemma():
    print("\n--- Testing Layer 2.5 PaliGemma (Ngrok Colab) ---")
    test_img_path = "/tmp/media/test_paligemma.jpg"
    
    # Create simple dummy image
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save(test_img_path)
    
    # Run the triage
    result = run_paligemma_triage([test_img_path])
    print(f"PaliGemma Decision: {result.decision.value}")
    print(f"PaliGemma Score: {result.confidence_score}")
    print(f"Visual Coherence: {result.visual_coherence}")
    print(f"Raw Details: {result.details}")

def test_sandbox():
    print("\n--- Testing Zero-Day Sandbox (EICAR) ---")
    test_eicar_path = "/tmp/media/test_eicar.exe"
    
    with open(test_eicar_path, "wb") as f:
        f.write(b"EICAR test string")
        
    result = run_zeroday_sandbox(test_eicar_path)
    print(f"Sandbox Safe: {result.is_safe}")
    print(f"Threat Name: {result.threat_name}")
    print(f"YARA Hits: {result.yara_hits}")

if __name__ == "__main__":
    test_paligemma()
    test_sandbox()
