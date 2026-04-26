# AXIOM

**Digital Asset Integrity Platform**

AXIOM is a multi-layered enterprise middleware system designed for Security Operations Center (SOC) teams. It automates the ingestion, heuristic filtering, multimodal AI verification, and cryptographic provenance signing of digital media assets. The platform is purpose-built to detect AI-generated deepfakes, synthetic media, and intellectual property violations at scale.

---

## Architecture

The platform is organized across five distinct processing layers, each routing assets based on confidence thresholds to minimize inference cost and maximize throughput.

| Layer | Component | Technology |
|---|---|---|
| Layer 1 | Provenance & Signing | C2PA Manifest, RSA-2048 (local), NeonDB |
| Layer 2 | Heuristic Triage | FFmpeg, dHash/aHash, Upstash Redis |
| Layer 2.5 | Vision Enclave | PaliGemma (Colab/T4), Ngrok Tunnel |
| Layer 3 | Semantic Interrogation | Gemini 1.5 Pro, Pinecone Vector Search |
| Layer 4 | Data Persistence | NeonDB Serverless PostgreSQL, pgvector |
| Layer 5 | Operator Interface | Next.js, Framer Motion, Vanilla CSS |

The triage engine uses perceptual hash Hamming-distance thresholds to route assets:

- `0-8` - Direct block. Cache hit in Redis. No further processing.
- `9-20` - Escalate to PaliGemma vision inference.
- `21-35` - Escalate to Gemini 1.5 Pro multimodal chain.
- `35+`  - Archive as novel content.

---

## Repository Structure

```
AXIOM/
  backend/           FastAPI microservice and all AI pipeline modules
    main.py          Primary API routing (upload, triage, interrogate, scrapers)
    triage.py        FFmpeg keyframe extraction and pHash computation
    provenance.py    C2PA manifest generation and RSA signing
    database.py      SQLAlchemy ORM for NeonDB asset and incident records
    vector_store.py  Pinecone upsert and cosine similarity query interface
    gemini_interrogator.py  Gemini 1.5 Pro prompt chain and fraud report
    scrapers.py      YouTube and Reddit async OSINT scraper workers
    requirements.txt  Full Python dependency manifest
    Dockerfile       Backend container definition

  frontend/          Next.js 16 SOC operator dashboard
    src/app/
      page.tsx       Application router, login screen, and dashboard layout
      globals.css    Enterprise vanilla CSS design system (light + dark themes)
      layout.tsx     Root HTML shell and Inter font injection

  docs/              Technical architecture documentation
    objective.md
    layer_1_security_provenance.md
    layer_2_heuristic_local_ai.md
    layer_3_deep_semantic_ai.md
    layer_4_data_disaster_recovery.md
    layer_5_observability_alerting.md
    external_sources_ingestion.md
    ui_ux_plan.md

  docker-compose.yml  Orchestrates the backend container with volume mounts
  .gitignore          Excludes credentials, build artifacts, and node_modules
  .env                Local environment variable store (never committed)
```

---

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 20.x
- Python 3.11

### 1. Configure Environment

Copy the environment template and populate the values. Credentials for the external services listed below (NeonDB, Pinecone, Upstash, Google AI Studio) are required.

```sh
cp .env.example .env
```

Required environment variables:

```
DATABASE_URL=                 # NeonDB PostgreSQL connection string
PINECONE_API_KEY=             # Pinecone serverless API key
PINECONE_INDEX=               # Target Pinecone index name
REDIS_URL=                    # Upstash Redis TLS connection string
GEMINI_API_KEY=               # Google AI Studio API key
PALIGEMMA_URL=                # Active Ngrok/Cloudflare tunnel to Colab instance
GOOGLE_APPLICATION_CREDENTIALS=  # Path to GCP service account (optional for local)
```

### 2. Start the Backend

```sh
docker compose up --build
```

The FastAPI service will be accessible at `http://localhost:8000`. Interactive API docs are available at `http://localhost:8000/docs`.

### 3. Start the Frontend

```sh
cd frontend
npm install
npm run dev
```

The SOC dashboard will be accessible at `http://localhost:3000`.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/upload-source` | Ingest asset, generate C2PA manifest, store in NeonDB, upsert Pinecone embedding |
| `POST` | `/api/triage` | Run FFmpeg keyframe extraction, compute pHash, check Upstash Redis cache |
| `POST` | `/api/paligemma` | Proxy frame payload to PaliGemma vision inference endpoint |
| `POST` | `/api/interrogate` | Gemini 1.5 Pro interrogation chain, log IncidentRecord to NeonDB |
| `GET`  | `/api/scrapers/trigger` | Dispatch YouTube and Reddit async scraper workers |
| `GET`  | `/health` | API health check |

---

## Infrastructure

This platform operates under a zero-cost MVP architecture designed to replicate enterprise cloud capabilities using free-tier serverless providers.

| Enterprise Service | Free Replacement |
|---|---|
| Cloud SQL PostgreSQL | NeonDB Serverless |
| Vertex AI Vector Search | Pinecone Serverless |
| Cloud Memorystore (Redis) | Upstash Serverless Redis |
| GKE + L4 GPU (PaliGemma) | Google Colab T4 + Ngrok |
| Cloud KMS | Local RSA-2048 via Python `cryptography` |

---

## Security

Sensitive credentials are stored exclusively in `.env` and `credentials.md`, both of which are listed in `.gitignore` and excluded from all version control operations. The `youtube_client_secret.json` OAuth payload is also excluded.

The git history was initialized as a clean orphan commit to prevent any accidental secret exposure in prior commits. GitHub Secret Scanning is enabled on the remote repository.

---

## License

Proprietary. All rights reserved.
