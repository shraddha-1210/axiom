# Layer 2 & 2.5: Heuristic Filter & Local AI (Cost Optimiser)

## Overview
This layer acts as the cost-saver. By analyzing lightweight perceptual aspects of an asset within a localized environment, it drops roughly 85-90% of scraped media before they need to touch expensive large APIs.

## Layer 2: pHash & Audio Fingerprinting
Operated using an event-driven mechanism (Cloud Functions Gen 2/Cloud Run) listening to the queue.
1. **Visual pHash:** 
   - Computes 64-bit `dHash` (difference hash, for structural similarity) and `aHash` (average hash, for brightness-invariant similarity) of keyframes using Python's `imagehash`.
   - Uses **Hamming Distance** for comparison against cached hashes stored in a Memorystore (Redis) instance (under 1ms lookup).
2. **Audio Fingerprinting:** 
   - Uses `Chromaprint` (AcoustID engine via `librosa`/FFmpeg) to extract a spectral frequency fingerprint.
3. **Triage Routing Matrix:**
   - **Hamming 0–8 (>95% match):** Direct Copy. Automated BLOCK/Takedown. Alert SOC. Cost: ~$0.0001
   - **Hamming 9–20 (80–95% match):** Escalate to Layer 2.5 (PaliGemma). Cost: ~$0.002
   - **Hamming 21–35 (50–80% match):** Significant Edit. Escalate to Layer 3 (Vertex AI/Gemini). Cost: $0.04-$0.15
   - **Hamming >35 (<50% match):** Discard/Archive as unrelated content. Cost: ~$0.0001

## Layer 2.5: Local PaliGemma Triage (Privacy Enclave)
For assets needing intermediate assessment (Hamming 9-20), traffic is routed to an open-weights Vision-Language Model deployed in a private VPC.
- **Architecture:** Runs locally on Google Kubernetes Engine (GKE Autopilot) with GPU nodes (NVIDIA L4) inside a VPC with no internet egress. This ensures **Data Sovereignty**.
- **Analyses:**
  - **Visual Coherence:** Looks for compression artifacts, geometric consistency on logos, and frame transition temporal flickering.
  - **OSINT Context:** Uses a smaller Gemma (2B/7B) text model to parse Telegram captions, Reddit posts, account age, and comments looking for piracy intent.
- **Outcome:** Generates a confidence score (0-100).
  - Score >= 65: Escalate to Layer 3 (approx. 8% of total scraped items).
  - Score < 65: Archive.
