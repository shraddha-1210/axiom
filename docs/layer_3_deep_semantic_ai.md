# Layer 3: Deep Semantic Interrogation (Vertex AI & Gemini)

## Overview
As the platform's definitive, legally defensible classification layer, Layer 3 is invoked for the ~2% of traffic that survives early heuristics without being definitively blocked or cleared.

## Layer 3a: Vertex AI Multimodal Embeddings (Semantic Fingerprinting)
When simple visual hashing fails (e.g. replacing a logo using GenAI alters bytes and local pixels heavily but the global semantic scene remains identical), semantic embeddings act as the ultimate identifier.
- **Processing:** Video frames, audio tracks, and textual metadata are passed to Vertex AI's `multimodalembedding@001`.
- **Output:** A 1408-dimensional float vector capturing spatial, contextual, and temporal meaning (e.g. "IPL match, batsman hits six, crowd is cheering").
- **Verification:** An Approximate Nearest Neighbor (ANN) search via Vertex Vector Search determines the Cosine Similarity against all registered assets.
  - Similarity > 0.85: Same semantic content confirmed. Escalate to Layer 3b.
  - Similarity 0.70-0.85: Moderate similarity (flag for review).
  - Similarity < 0.70: Different content (discard).

## Layer 3b: Gemini 1.5 Pro Vision (Deepfake Interrogation)
Invoked only on highly suspicious content (Similarity > 0.85 and modified/missing C2PA). This layer does heavyweight interrogation.
- **Deepfake Analysis:** Looks for temporal flickering on face boundaries, blinking frequency anomalies, mismatched skin textures.
- **Logo/Object Inpainting Detection:** Examines edge gradient irregularities, DCT frequency anomalies, and color space inconsistencies.
- **SynthID AI Generation Detection:** Captures Google's LSB statistical watermark for generative diffusion models.
- **Audio-Visual Coherence:** Gemini transcribes audio using Google Speech-to-Text v2 (Chirp) and validates if spoken content correlates contextually to the visual events.
- **Result Output:** A structured JSON object categorizing the fraud (e.g., `DEEPFAKE`, `FRAUD_AI_MORPHED`, `AI_SYNTHESISED`) and suggesting immediate response actions (Takedown, Legal Escalation) with >85% confidence rules driving automatic handling.
