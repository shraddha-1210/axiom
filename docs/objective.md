# AXIOM: Objective & Overview

## Project Objective
AXIOM is a multi-layered, B2B enterprise middleware platform engineered to defend the integrity and ownership of high-value digital media assets in real time. Built to sit between an organization's secure content vault and the open internet, it operates invisibly to end users but handles critical content protection workflows.

## Core Philosophy
The platform operates on **Assumed Breach** and **Tiered Triage** principles:
- **Assumed Breach:** Every externally scraped asset is treated as a potential threat.
- **Tiered Triage:** Content is pushed through progressively more expensive detection layers, eliminating 98% of threats at near-zero cost using heuristics before heavyweight AI models (Vertex AI, Gemini) are invoked.

## Key Features & Differentiators
1. **Defeats GenAI & Perceptual Edits:** SHA-256 hashes break with a single pixel change. AXIOM uses Semantic Embeddings which survive GenAI modifications (like logo swaps and face replacements) and pHash for visual similarities.
2. **Real-time Automated Takedowns:** Unlike manual 48-hour takedowns, AXIOM's automated detection achieves 3–8 minute response times.
3. **Optimized AI Costs:** Tiered triage means only 2% of traffic reaches expensive Gemini models, drastically reducing inference costs (e.g., $30/day vs $1,500/day for 10,000 videos).
4. **Legally Admissible Evidence:** Utilizes C2PA cryptographic chain (ISO-certified) for undeniable provenance and origin verification.

## 5-Layer Defense Architecture
- **Layer 0:** Perimeter Security (WAF, iAP, mTLS)
- **Layer 1:** Provenance Shield (C2PA Signing, WORM Storage)
- **Layer 2 & 2.5:** Cost Optimiser (pHash + Audio Fingerprint + local PaliGemma VPC inference)
- **Layer 3:** Deep Semantic Interrogation (Vertex AI Multi-vector + Gemini 1.5 Pro deepfake analysis)
- **Layer 4:** Data Layer & DR (Cloud SQL, Vector DB, active/passive Dual-Region)
- **Layer 5:** Observability & Alerts (React/GraphQL Dashboard, Chronicle SIEM, Auto/Human Triage Queue)
