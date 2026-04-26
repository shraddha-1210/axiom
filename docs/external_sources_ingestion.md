# External Sources & Ingestion Pipeline

## Overview
AXIOM utilizes a decoupled Orchestrator > Scraper > Queue > Processing model to discover and ingest potential threats asynchronously without relying on manual reporting.

## Scheduling Engine
- **Infrastructure:** Google Cloud Scheduler manages chron tasks, dispatching events to a Pub/Sub topic (`scraper-triggers`).
- **Functionality:** Dispatches trigger JSON detailing target platforms, keywords, region filters, and priority. Priority automatically scales during live-events, raising polling frequency by 3x.
- **Workers:** Ephemeral Cloud Run jobs consume targeted platform events and instantiate stateless processes.

## Platform Scrapers
Scraping strictly avoids browser automation to prevent ban risks, instead operating directly on platform APIs.
1. **YouTube Data API v3:** Performs Search API queries & Channel Monitoring against known threat lists.
2. **Reddit API (OAuth2):** Actively polls (`/new`) across designated subreddits looking for video extensions and known piracy hosting domains.
3. **Telegram Bot App:** Tracks channels, fetching message updates pulling out explicit videos AND surrounding contextual text.
4. **X (Twitter) Filtered Streams:** Holds persistent TLS connections, parsing new tweets for predefined rules, extracting `media_keys` and linked domains.

## Preprocessing & Quarantining
Prior to hashing or intensive AI tasks, downloaded content passes through a rigid vetting pipeline.
- Performs partial downloads (512kb) to parse header metadata instead of complete media files if false.
- Validates **True MIME type** via magic bytes checking, ignoring given file extensions.
- **Zero-Day Sandbox Mechanism:** Anomalous containers execute in an offline, eBPF-monitored Linux environment. Any file attempting unauthorized IO syscalls (network/disk open without clearance) triggers immediate permanent quarantine.
- Extract sparse spatial components (I-Frames specifically via FFmpeg, rather than the entire 60FPS feed) to optimize memory indexing and hashing.
- **Queueing Engine:** Filtered, preprocessed components are queued to Cloud Pub/Sub `analysis-queue` for progression through the 5 defense layers.
