# Backend Files: Used vs Unnecessary

## ✅ CORE FILES (Required - DO NOT DELETE)

### Application Core
- **main.py** ✅ REQUIRED
  - FastAPI application
  - All API endpoints
  - Server entry point

- **database.py** ✅ REQUIRED
  - PostgreSQL/SQLite configuration
  - Database models (AssetRecord, IncidentRecord)
  - Used by: main.py

- **vector_store.py** ✅ REQUIRED
  - Pinecone integration
  - Embedding storage
  - Used by: main.py

### Layer 2 Implementation
- **triage.py** ✅ REQUIRED
  - Layer 2 pHash triage
  - FFmpeg I-frame extraction
  - Hamming distance routing
  - Used by: main.py

- **paligemma_triage.py** ✅ REQUIRED
  - Layer 2.5 PaliGemma analysis
  - OSINT context analysis
  - Used by: main.py

- **gemini_interrogator.py** ✅ REQUIRED
  - Layer 3 Gemini analysis
  - Deepfake detection
  - Used by: main.py

### Layer 1 & Security
- **provenance.py** ✅ REQUIRED
  - C2PA manifest creation
  - Digital signatures
  - Used by: main.py

- **waf.py** ✅ REQUIRED
  - Web Application Firewall
  - Rate limiting
  - IP blocking
  - Used by: main.py

### Event System
- **event_queue.py** ✅ REQUIRED
  - Event-driven architecture
  - Pub/Sub integration
  - Used by: main.py

### Configuration
- **requirements.txt** ✅ REQUIRED
  - Python dependencies
  - Used by: pip install

- **axiom.db** ✅ REQUIRED (Generated)
  - SQLite database file
  - Auto-created by database.py

---

## ⚠️ OPTIONAL FILES (Can Keep or Delete)

### Scrapers
- **scrapers.py** ⚠️ OPTIONAL
  - Reddit, Telegram, YouTube scrapers
  - Used by: main.py (endpoint `/api/scrapers/trigger`)
  - **Keep if**: You want automatic content ingestion
  - **Delete if**: You only upload content manually

### Cloud Deployment
- **cloud_function_handler.py** ⚠️ OPTIONAL
  - Cloud Functions event handlers
  - Used by: Cloud Functions deployment only
  - **Keep if**: Deploying to GCP Cloud Functions
  - **Delete if**: Running locally or on Cloud Run only

- **deploy_cloud_functions.sh** ⚠️ OPTIONAL
  - Deployment script for Cloud Functions
  - **Keep if**: Planning to deploy to Cloud Functions
  - **Delete if**: Not using Cloud Functions

- **deploy_cloud_run.sh** ⚠️ OPTIONAL
  - Deployment script for Cloud Run
  - **Keep if**: Planning to deploy to Cloud Run
  - **Delete if**: Running locally only

- **Dockerfile** ⚠️ OPTIONAL
  - Docker container for Cloud Functions
  - **Keep if**: Using Cloud Functions
  - **Delete if**: Not using Docker/Cloud Functions

- **Dockerfile.cloudrun** ⚠️ OPTIONAL
  - Docker container for Cloud Run
  - **Keep if**: Using Cloud Run
  - **Delete if**: Not using Docker/Cloud Run

### GCP Services
- **gcp_services.py** ⚠️ OPTIONAL
  - GCP Cloud Storage and KMS integration
  - Used by: test_gcp.py only
  - **Keep if**: Using GCP services for storage/encryption
  - **Delete if**: Not using GCP services

- **gcp-key.json** ⚠️ OPTIONAL (SENSITIVE!)
  - GCP service account credentials
  - **Keep if**: Using GCP services
  - **Delete if**: Not using GCP (and remove from git!)
  - **⚠️ SECURITY**: Should be in .gitignore

### Helper Scripts
- **start_server.ps1** ⚠️ OPTIONAL
  - PowerShell script to start server
  - Convenience script
  - **Keep if**: You like using it
  - **Delete if**: You prefer manual commands

---

## 🧪 TEST FILES (Safe to Delete)

### Test Scripts
- **test_layer2_pipeline.py** 🧪 TEST
  - Comprehensive Layer 2 & 2.5 tests
  - **Keep if**: You want to run tests
  - **Delete if**: Not testing

- **test_pipeline.py** 🧪 TEST
  - Basic pipeline integration tests
  - **Keep if**: You want to run tests
  - **Delete if**: Not testing

- **test_waf.py** 🧪 TEST
  - WAF and rate limiting tests
  - **Keep if**: Testing security features
  - **Delete if**: Not testing

- **test_gcp.py** 🧪 TEST
  - GCP services verification
  - **Keep if**: Using GCP services
  - **Delete if**: Not using GCP

- **test_import.py** 🧪 TEST
  - Debug script for import issues
  - **Keep if**: Debugging imports
  - **Delete if**: Everything works

---

## 📁 DIRECTORIES

- **__pycache__/** 🗑️ AUTO-GENERATED
  - Python bytecode cache
  - Safe to delete (will regenerate)
  - Add to .gitignore

---

## 🗑️ RECOMMENDED CLEANUP

### Minimal Setup (Local Development Only)

**DELETE these files**:
```
axiom/backend/cloud_function_handler.py
axiom/backend/deploy_cloud_functions.sh
axiom/backend/deploy_cloud_run.sh
axiom/backend/Dockerfile
axiom/backend/Dockerfile.cloudrun
axiom/backend/gcp_services.py
axiom/backend/gcp-key.json
axiom/backend/test_gcp.py
axiom/backend/test_import.py
axiom/backend/test_pipeline.py
axiom/backend/test_waf.py
```

**KEEP these files**:
```
axiom/backend/main.py
axiom/backend/database.py
axiom/backend/vector_store.py
axiom/backend/triage.py
axiom/backend/paligemma_triage.py
axiom/backend/gemini_interrogator.py
axiom/backend/provenance.py
axiom/backend/waf.py
axiom/backend/event_queue.py
axiom/backend/scrapers.py (if using scrapers)
axiom/backend/requirements.txt
axiom/backend/axiom.db
axiom/backend/start_server.ps1 (convenience)
axiom/backend/test_layer2_pipeline.py (for testing)
```

### Production Setup (Cloud Deployment)

**KEEP everything except**:
```
axiom/backend/test_import.py (debug script)
axiom/backend/gcp-key.json (use environment variables instead)
```

---

## 📊 File Usage Summary

| File | Used By | Purpose | Can Delete? |
|------|---------|---------|-------------|
| main.py | Server | API endpoints | ❌ NO |
| database.py | main.py | Database | ❌ NO |
| vector_store.py | main.py | Embeddings | ❌ NO |
| triage.py | main.py | Layer 2 | ❌ NO |
| paligemma_triage.py | main.py | Layer 2.5 | ❌ NO |
| gemini_interrogator.py | main.py | Layer 3 | ❌ NO |
| provenance.py | main.py | C2PA | ❌ NO |
| waf.py | main.py | Security | ❌ NO |
| event_queue.py | main.py | Events | ❌ NO |
| scrapers.py | main.py | Scrapers | ⚠️ Optional |
| cloud_function_handler.py | Cloud Functions | Deployment | ⚠️ Optional |
| gcp_services.py | test_gcp.py | GCP | ⚠️ Optional |
| deploy_*.sh | Manual | Deployment | ⚠️ Optional |
| Dockerfile* | Docker | Containers | ⚠️ Optional |
| test_*.py | Manual | Testing | ✅ Yes |
| gcp-key.json | GCP | Credentials | ⚠️ Sensitive |

---

## 🎯 Quick Cleanup Commands

### Delete all test files:
```powershell
cd axiom/backend
Remove-Item test_gcp.py, test_import.py, test_pipeline.py, test_waf.py
```

### Delete cloud deployment files (if not using):
```powershell
cd axiom/backend
Remove-Item cloud_function_handler.py, deploy_cloud_functions.sh, deploy_cloud_run.sh, Dockerfile, Dockerfile.cloudrun, gcp_services.py
```

### Delete GCP credentials (if not using):
```powershell
cd axiom/backend
Remove-Item gcp-key.json
```

### Clean Python cache:
```powershell
cd axiom/backend
Remove-Item -Recurse -Force __pycache__
```

---

## ⚠️ IMPORTANT NOTES

1. **gcp-key.json** contains sensitive credentials - should NOT be in git
2. **axiom.db** is auto-generated - safe to delete (will recreate)
3. **__pycache__** is auto-generated - safe to delete (will recreate)
4. Keep **test_layer2_pipeline.py** - it's the main test suite
5. Keep **scrapers.py** if you want automatic content monitoring

---

## 🔍 How to Check if a File is Used

```powershell
# Search for imports
cd axiom/backend
Select-String -Pattern "from filename|import filename" -Path *.py
```

Replace `filename` with the file you want to check (without .py extension).
