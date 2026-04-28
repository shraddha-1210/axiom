# ☁️ AXIOM Cloud-Only Backend Setup (Zero Cost)

## 🎯 Overview

This guide shows how to run **AXIOM backend entirely on free cloud services** with **zero Google Cloud credits needed**.

**Architecture:**
```
AXIOM Backend (Backend folder)
         ↓
    cloud_client.py
         ↓
  Colab ngrok Tunnel
         ↓
  PaliGemma on T4 GPU (free)
```

---

## 🚀 Step-by-Step Setup

### **Step 1: Start Colab Notebook with PaliGemma**

Open [Google Colab](https://colab.research.google.com) and run this notebook:

```python
# ============================================================================
# Cell 1: Install Dependencies
# ============================================================================
!pip install -U transformers accelerate uvicorn fastapi pyngrok pillow nest_asyncio pydantic

import io
import base64
import torch
import uvicorn
import nest_asyncio
from pyngrok import ngrok
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from PIL import Image
from transformers import AutoProcessor, PaliGemmaForConditionalGeneration

# ============================================================================
# Cell 2: Set Credentials & Load Model
# ============================================================================
HF_TOKEN = "YOUR_HUGGINGFACE_TOKEN"  # Get from huggingface.co/settings/tokens
NGROK_TOKEN = "YOUR_NGROK_TOKEN"     # Get from dashboard.ngrok.com

print("⏳ Loading PaliGemma 3B in bfloat16...")
processor = AutoProcessor.from_pretrained("google/paligemma-3b-mix-224", token=HF_TOKEN)
model = PaliGemmaForConditionalGeneration.from_pretrained(
    "google/paligemma-3b-mix-224",
    token=HF_TOKEN,
    torch_dtype=torch.bfloat16,  # CRITICAL: Prevents OOM
    device_map="auto"
).eval()
print("✓ Model loaded!")

# ============================================================================
# Cell 3: Define FastAPI App
# ============================================================================
app = FastAPI(title="AXIOM Vision Node")

class FramePayload(BaseModel):
    image_base64: str
    prompt: str = "caption en"

@app.get("/health")
def health():
    return {"status": "ok", "model": "PaliGemma-3B"}

@app.post("/analyze-frame")
async def analyze_frame(payload: FramePayload):
    try:
        image_bytes = base64.b64decode(payload.image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        model_inputs = processor(
            text=payload.prompt,
            images=image,
            return_tensors="pt"
        ).to(model.device)
        
        with torch.inference_mode():
            generation = model.generate(**model_inputs, max_new_tokens=100)
        
        decoded_text = processor.decode(generation[0], skip_special_tokens=True)
        clean_result = decoded_text.replace(payload.prompt, "").strip()
        
        return {"status": "success", "analysis": clean_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Cell 4: Start Ngrok Tunnel & Server
# ============================================================================
ngrok.set_auth_token(NGROK_TOKEN)
ngrok.kill()  # Kill any existing tunnels
tunnel = ngrok.connect(8000)
print(f"\n✅ COLAB NGROK URL: {tunnel.public_url}")
print(f"   Save this URL! You'll use it in your backend .env file.\n")

import threading
def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

# Keep tunnel alive
import time
while True:
    time.sleep(1)
```

**After running:** You'll get a URL like:
```
✅ COLAB NGROK URL: https://deskbound-unmolded-veto.ngrok-free.dev
```

### **Step 2: Configure Backend .env**

In your AXIOM backend folder, update `.env.colab`:

```bash
# ============================================================================
# AXIOM Cloud-Only Configuration
# ============================================================================

# Colab Ngrok Tunnel (from Step 1)
COLAB_NGROK_URL=https://deskbound-unmolded-veto.ngrok-free.dev

# API Endpoints
PALIGEMMA_ENDPOINT=${COLAB_NGROK_URL}/analyze-frame
EMBEDDINGS_ENDPOINT=${COLAB_NGROK_URL}/generate-embedding

# Mode
INFERENCE_MODE=cloud-only
USE_VERTEX_AI=false
USE_LOCAL_MODELS=false

# Colab Timeout (Colab can be slow on first request)
COLAB_TIMEOUT=120
COLAB_RETRY_ATTEMPTS=3
DEBUG_CLOUD_CALLS=true
```

### **Step 3: Install Backend Dependencies**

```bash
cd backend

# Install cloud-only requirements
pip install -r requirements.txt

# Add cloud dependencies (if not already there)
pip install requests pydantic pillow
```

### **Step 4: Test Cloud Connections**

```bash
# Check if Colab endpoint is reachable
curl https://deskbound-unmolded-veto.ngrok-free.dev/health

# Expected output:
# {"status":"ok","model":"PaliGemma-3B"}
```

### **Step 5: Start AXIOM Backend**

```bash
# Load cloud-only env config
export $(cat .env.colab | xargs)

# Start FastAPI server
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 📡 Using Cloud Endpoints

### **Cloud-Only Frame Analysis**

```bash
# Upload frame for analysis
curl -X POST "http://localhost:8001/analyze-frame" \
  -F "file=@/path/to/frame.jpg" \
  -F "prompt=caption en"

# Response:
{
  "status": "success",
  "analysis": "A video frame showing a cricket match with batsmen batting",
  "processing_time_ms": "2500.3",
  "model": "PaliGemma-3B (Colab T4 GPU)",
  "cost": "$0.00"
}
```

### **Deepfake Detection**

```bash
curl -X POST "http://localhost:8001/cloud/deepfake-detection" \
  -F "file=@/path/to/frame.jpg"

# Response:
{
  "status": "success",
  "deepfake_analysis": "No obvious deepfake indicators detected. Face boundaries appear natural...",
  "processing_time_ms": "3100.5",
  "cost": "$0.00"
}
```

### **Compression Artifact Analysis**

```bash
curl -X POST "http://localhost:8001/cloud/compression-artifacts" \
  -F "file=@/path/to/frame.jpg"
```

### **Check Cloud Health**

```bash
curl http://localhost:8001/cloud/health

# Response:
{
  "status": "ok",
  "colab_ngrok_url": "https://deskbound-unmolded-veto.ngrok-free.dev",
  "cloud_ready": true
}
```

---

## 🐍 Python Client Example

```python
import requests
import base64

BACKEND_URL = "http://localhost:8001"
COLAB_URL = "https://deskbound-unmolded-veto.ngrok-free.dev"

def analyze_frame_via_cloud(image_path: str, prompt: str = "caption en"):
    """Send frame to backend, which forwards to Colab."""
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        params = {"prompt": prompt}
        
        response = requests.post(
            f"{BACKEND_URL}/analyze-frame",
            files=files,
            params=params
        )
    
    return response.json()

def detect_deepfake(image_path: str):
    """Deepfake detection via cloud."""
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(
            f"{BACKEND_URL}/cloud/deepfake-detection",
            files=files
        )
    
    return response.json()

# Usage
result = analyze_frame_via_cloud("frame.jpg", "caption en")
print(f"Analysis: {result['analysis']}")
print(f"Cost: {result['cost']}")  # Always $0.00

result = detect_deepfake("frame.jpg")
print(f"Deepfake Analysis: {result['deepfake_analysis']}")
```

---

## 📊 Cost Breakdown

| Component | Local | Vertex AI | Cloud-Only |
|-----------|-------|-----------|-----------|
| **PaliGemma Inference** | $0 (GPU time) | N/A | **$0** ✓ |
| **Multimodal Embeddings** | N/A | $0.02/1K | **$0** (CLIP free) |
| **Deepfake Detection** | $0 (local) | N/A | **$0** ✓ |
| **Per 10K videos** | $0 | $150-300 | **$0** ✓ |
| **Colab GPU** | Free (40 hrs/mo) | N/A | **Free** ✓ |
| **Ngrok Tunnel** | $0 (free tier) | N/A | **$0** ✓ |
| **Backend FastAPI** | $0 (localhost) | N/A | **$0** ✓ |

---

## ⚠️ Important Notes

### **Colab Session Timeout**
- Colab disconnects after **30 mins of inactivity**
- Keep the Colab notebook tab open
- Or use Colab Pro ($10/mo) for longer sessions

### **Ngrok URL Changes**
- Free tier Ngrok URL changes when you reconnect
- Update `.env.colab` with the new URL
- Pro tip: Use Ngrok Pro ($5/mo) for stable URLs

### **Rate Limits**
- Colab T4 GPU can handle ~5-10 frames/min
- Backend limits: 20/min for `/analyze-frame`
- Batch multiple frames with delays

### **Fallback Strategy**
```python
# If Colab is down, use free Huggingface Spaces instead:

HUGGINGFACE_SPACES_URL = "https://username-paligemma-space.hf.space"
# Deploy PaliGemma to HF Spaces for permanent free endpoint
```

---

## 🔄 Integration with Existing Layers

### **Layer 2 (Triage) → Cloud**
```python
# triage.py - USE CLOUD CLIENT
from cloud_client import batch_analyze_frames_cloud

frame_paths = extract_keyframes(filepath)
results = batch_analyze_frames_cloud(frame_paths, 
    prompt="Analyze visual coherence for compression artifacts")
```

### **Layer 3 (Embeddings) → Cloud**
```python
# layer3_orchestrator.py
from cloud_embeddings import generate_multimodal_embedding

embedding = generate_multimodal_embedding(
    frame_paths, 
    text_context="video caption"
)
# Uses free CLIP or cloud CLIP, never Vertex AI
```

---

## 🧪 Testing Checklist

- [ ] Colab notebook running with ngrok tunnel active
- [ ] `.env.colab` has correct ngrok URL
- [ ] Backend `/cloud/health` returns `"cloud_ready": true`
- [ ] `/analyze-frame` processes sample image successfully
- [ ] Cost always shows `$0.00`
- [ ] Processing times are <5 seconds per frame
- [ ] No "Vertex AI" or local system calls in logs

---

## 🆘 Troubleshooting

### **"Connection refused" to ngrok URL**
```
❌ Error: Connection failure
✅ Solution: 
  1. Check Colab notebook is still running
  2. Verify ngrok tunnel is active (Cell 4 output)
  3. Update .env.colab with new URL
  4. Restart backend: python -m uvicorn main:app --reload
```

### **"Timeout after 120s"**
```
❌ Error: COLAB_TIMEOUT exceeded
✅ Solution:
  1. First request may be slow (model loading). Increase COLAB_TIMEOUT to 180
  2. Ngrok free tier has variable latency
  3. Use Ngrok Pro or deploy to permanent cloud service
```

### **ngrok URL keeps changing**
```
❌ Problem: Free Ngrok tunnel changes each session
✅ Solutions:
  1. Use Ngrok Pro ($5/mo) for permanent URL
  2. Deploy to Huggingface Spaces (free, permanent)
  3. Use Replicate.com API (free tier available)
```

---

## 🚀 Next Steps

1. **Permanent Endpoint:** Deploy to HuggingFace Spaces instead of Colab
2. **Batch Processing:** Queue frames in Redis, process async
3. **Multi-GPU:** Use multiple Colab TPs in parallel
4. **Hybrid:** Keep Layer 2.5 local, Layer 3+ cloud

