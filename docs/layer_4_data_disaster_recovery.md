# Layer 4: Data Layer & Disaster Recovery (Active/Passive HA)

## Overview
All analysis results, embeddings, metadata, cache, and audit logs are stored in a highly resilient geo-redundant architecture with RTO < 2 minutes and RPO < 15 minutes.

## Storage Components
1. **Metadata DB (Cloud SQL PostgreSQL - HA):** Stores asset registration, SHA-256 hashes, ownership, and C2PA manifest references. Async syncs to Region B replica every 30 seconds.
2. **Vector DB (pgvector / Vertex Vector Search):** Stores 1408-dim embeddings. Features stream replication to a cold standby in Region B.
3. **Object Store (Cloud Storage - WORM & CMEK):** Stores original registered files, manifests, quarantined files. Dual-region auto replication ensures durability.
4. **Hash Cache (Redis / Cloud Memorystore):** Maintains pHash and audio fingerprints for rapid O(1) in-memory lookups. Replicated to Region B standby.
5. **Audit Logs (Cloud Logging):** Immutable WORM buckets capturing all AI traces and decisions, exported to Chronicle SIEM in real-time.
6. **Message Queue (Cloud Pub/Sub):** Manages async scraper results and stage isolation with 3-zone durability and Dead Letter Queues (DLQ).

## Disaster Recovery Routing
- **Region A (Active):** Hosts primary load balancing, active processing services (Cloud Run/GKE), primary databases, and active caching.
- **Region B (Standby):** Pre-provisioned warm Cloud Run services, read-only Replicas, cold Vector DB standby, and standby Redis instance.
- **Automated Failover:** Cloud Monitoring checks endpoint health continuously. Three consecutive failures invoke the **DR Orchestrator**, which points Cloud DNS (30s TTL) to Region B ensuring system-wide RTO ~60-90 seconds.
