# ⚡ AXIOM Cloud Setup - Quick Start (5 minutes)

## 📋 Prerequisite Accounts (All Free)
- ✅ Google Account (for Colab)
- ✅ Hugging Face Account (for model access)
- ✅ Ngrok Account (for tunnel)

---

## 🎯 Quick 5-Step Setup

### **1️⃣ Get HF Token** (1 min)
```
Go to: https://huggingface.co/settings/tokens
Click "New token" → Copy to clipboard
```

### **2️⃣ Get Ngrok Token** (1 min)
```
Go to: https://dashboard.ngrok.com/get-started/your-authtoken
Copy auth token (starts with 3Cs...)
```

### **3️⃣ Run Colab Notebook** (2 min)
Copy this to [Google Colab](https://colab.research.google.com):

```python
!pip install -U transformers accelerate uvicorn fastapi pyngrok pillow pydantic
import base64, io, torch, uvicorn, threading, time
from pyngrok import ngrok
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
from transformers import AutoProcessor, PaliGemmaForConditionalGeneration

HF_TOKEN = "YOUR_HF_TOKEN_HERE"
NGROK_TOKEN = "YOUR_NGROK_TOKEN_HERE"

processor = AutoProcessor.from_pretrained("google/paligemma-3b-mix-224", token=HF_TOKEN)
model = PaliGemmaForConditionalGeneration.from_pretrained(
    "google/paligemma-3b-mix-224", token=HF_TOKEN, torch_dtype=torch.bfloat16, device_map="auto"
).eval()

app = FastAPI()

class FramePayload(BaseModel):
    image_base64: str
    prompt: str = "caption en"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze-frame")
async def analyze_frame(payload: FramePayload):
    image = Image.open(io.BytesIO(base64.b64decode(payload.image_base64))).convert("RGB")
    model_inputs = processor(text=payload.prompt, images=image, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        generation = model.generate(**model_inputs, max_new_tokens=100)
    decoded = processor.decode(generation[0], skip_special_tokens=True)
    return {"status": "success", "analysis": decoded.replace(payload.prompt, "").strip()}

ngrok.set_auth_token(NGROK_TOKEN)
ngrok.kill()
tunnel = ngrok.connect(8000)
print(f"\n✅ URL: {tunnel.public_url}")

threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000), daemon=True).start()
while True: time.sleep(1)
```

**Copy the output URL** (e.g., `https://deskbound-unmolded-veto.ngrok-free.dev`)

### **4️⃣ Update Backend .env** (1 min)

Create/edit `/mnt/windows/AXIOM/backend/.env.colab`:
```
COLAB_NGROK_URL=https://YOUR_NGROK_URL_HERE
PALIGEMMA_ENDPOINT=${COLAB_NGROK_URL}/analyze-frame
DEBUG_CLOUD_CALLS=true
```

### **5️⃣ Start Backend** (1 min)
```bash
cd /mnt/windows/AXIOM/backend

# Install dependencies
pip install -r requirements.txt

# Start server
export $(cat .env.colab | xargs)
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## ✅ Verify It Works

```bash
# Test backend is running
curl http://localhost:8001/health

# Test cloud connection
curl http://localhost:8001/cloud/health

# Expected output:
# {"status":"ok","colab_ngrok_url":"https://...","cloud_ready":true}
```

---

## 📤 Use Cloud Endpoints

### **Analyze a Frame**
```bash
curl -X POST "http://localhost:8001/analyze-frame" \
  -F "file=@frame.jpg" \
  -F "prompt=caption en"
```

### **Detect Deepfakes**
```bash
curl -X POST "http://localhost:8001/cloud/deepfake-detection" \
  -F "file=@frame.jpg"
```

### **Check Compression Artifacts**
```bash
curl -X POST "http://localhost:8001/cloud/compression-artifacts" \
  -F "file=@frame.jpg"
```

---

## 🐍 Python Usage

```python
import requests

# Setup
BACKEND = "http://localhost:8001"

# Analyze frame
with open("frame.jpg", "rb") as f:
    resp = requests.post(
        f"{BACKEND}/analyze-frame",
        files={"file": f},
        params={"prompt": "caption en"}
    )

print(resp.json()["analysis"])  # Description of frame
print(resp.json()["cost"])       # "$0.00" ✨
```

---

## 🔧 Files Created

| File | Purpose |
|------|---------|
| `.env.colab` | Cloud configuration |
| `cloud_client.py` | Colab HTTP client |
| `cloud_embeddings.py` | Free CLIP embeddings |
| `docs/cloud_setup_guide.md` | Detailed setup guide |

---

## 💡 Pro Tips

### **Keep Colab Running**
- Colab shuts down after 30 mins inactivity
- Keep the browser tab open OR
- Use [Colab Pro](https://colab.research.google.com/signup) for $10/mo unlimited GPU

### **Stable URL (Optional)**
- Free Ngrok: URL changes each session (~$0/month)
- Ngrok Pro: Permanent URL ($5/month)
- HuggingFace Spaces: Permanent free endpoint + GPU

### **Batch Frames**
```python
# Process multiple frames with delays
for frame in ["frame1.jpg", "frame2.jpg", "frame3.jpg"]:
    result = requests.post(...)
    time.sleep(5)  # Respect rate limits
```

### **Fallback to Local CLIP**
```python
# If Colab goes down, use free local CLIP embeddings
from cloud_embeddings import generate_multimodal_embedding
# Automatically falls back to local models if cloud unavailable
```

---

## 🎯 Key Differences from Original

| Feature | Original (Vertex AI) | Cloud-Only ($0) |
|---------|-------------------|-----------------|
| Embeddings | $0.02/1K calls | **Free** (CLIP) |
| PaliGemma | Local/GPU | **Colab T4** |
| Deepfake Detection | Gemini API ($$) | **Free PaliGemma** |
| Infrastructure | GCP | **Colab + Ngrok** |
| Monthly Cost | $150-300 | **$0** ✅ |

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| **Connection refused** | Colab stopped. Restart notebook Cell 5 |
| **Timeout errors** | Colab may be slow. Increase `COLAB_TIMEOUT=180` |
| **Ngrok URL expired** | Free tier changes each session. Get new URL from Colab output |
| **"Model not loading"** | Colab may be overloaded. Clear RAM: `!rm -rf /root/.cache/huggingface` |

---

## 🎓 Next Level

Once working, consider:
1. **HuggingFace Spaces** - Permanent free endpoint (instead of Colab)
2. **Replicate** - GPU inference API with free tier
3. **Modal** - Cheap serverless GPU ($0.30-1/hour)

---

**Questions?** Check `docs/cloud_setup_guide.md` for detailed troubleshooting.
