# Layer 1: Security Perimeter & Provenance Shield

## Overview
This layer handles the secure ingestion of master assets into the platform. It provides a cryptographic "birth certificate" for newly registered assets against which all future scraped variants will be checked.

## Perimeter Security (Layer 0)
Every byte entering the system goes through a strict security perimeter.
- **Google Cloud Armor (WAF):** Provides L3/L4 volumetric DDoS mitigation, geo-fencing, rate limiting (max 1000 requests/min per IP), and OWASP Top 10 L7 protection.
- **Identity-Aware Proxy (IAP):** Provides a Zero Trust gateway, requiring valid Google identities to reach API endpoints.
- **Mutual TLS (mTLS):** Secures internal service-to-service communication using Google Certificate Authority Service.

## The Provenance Shield (Layer 1)
When partners register new assets (via a gRPC API), they undergo validation and cryptographic certification.
1. **Validation:** Checks MIME type and container structure of uploaded raw media.
2. **C2PA Manifest Signing:** A C2PA manifest (ISO/IEC DIS 22389 standard) records details of creation, tools, timestamps, and SHA-256 hashes. It is signed with the organization's HSM-backed private key via Cloud KMS.
3. **Storage Setup:** 
   - Media file + Signed Manifest are saved in a **WORM** (Write Once, Read Many) Cloud Storage bucket with CMEK encryption, preventing alteration or deletion.
   - Metadata and SHA-256 reference are saved in PostgreSQL (Cloud SQL).
4. **Async Embedding Pipeline Kickoff:** Trigger a background task to compute a 1408-dimensional semantic embedding via Vertex AI for future nearest-neighbor searches.

## Economic & Security Impact
The lack or invalidation of a C2PA manifest on a suspected scraped asset immediately acts as an early warning signal of tampering, removing the need for AI-based evaluation if the adversary didn't strip it correctly.
