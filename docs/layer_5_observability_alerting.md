# Layer 5: Observability, Alerting & Human Review

## Overview
Layer 5 is the interaction surface for Security Operations Center (SOC) analysts to view threat intelligence, verify medium-confidence detections, and manage legal exports.

## Core Services
- **GraphQL APIs (Apollo Server / Node.js):** Aggregates data from Postgres, Redis, and Vector DB.
- **Frontend Dashboard (React):** Fed by WebSocket push notifications (via Pub/Sub) meaning analysts see incidents dynamically update without page refreshes.

## Dashboard Components
1. **Dynamic Threat Matrix:** Renders a list of all registered assets with live Integrity Scores (0-100), which decrement immediately in response to new scraped infringements.
2. **Human Review Queue:** Holds medium confidence incidents (Gemini 65-84%). Exposes side-by-side videos, context text (from Gemma OSINT layer), and highlighted suspected regions.
3. **Automated Blocking Queue:** Shows incidents processed and actioned automatically (Confidence > 85%).
4. **Legal Export Workflow:** Analysts can trigger the generation of a WORM-certified, legally formatted PDF incident report detailing C2PA validations, AI traces, and visual differences.

## Alerting & SIEM Integration
- **Alert Types:**
  - *CRITICAL:* Gemini >85% fraud detected (PagerDuty P1, Slack, Email).
  - *HIGH:* Direct copy pHash match (Slack, Email).
  - *SYSTEM/CRASH:* Queue depth spikes or Zero-Day malformed files triggering eBPF Sandbox exceptions (PagerDuty P0).
- **Google Chronicle SIEM:** Cloud Logging exports the entire immutable evidence chain directly to Chronicle. Chronicle’s ML applies UEBA (User and Entity Behavior Analytics) to detect wider organized piracy operations or probing efforts across multiple incidents.
