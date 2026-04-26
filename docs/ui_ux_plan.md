# AXIOM Enterprise UI/UX Strategy

## 1. Aesthetic & Design System (Antigravity Style)
The design will pivot away from "AI generated neon blue" towards a sophisticated, premium enterprise tool.
- **Color Palette:** Pure Monochromatic darks (`#0a0a0a` to `#1f1f1f`). Sharp contrasting whites for typography. Accents will be extremely subtle, utilizing muted silver or very desaturated indigo (`#4f46e5` dialed down to 30% opacity). 
- **Typography:** Refined variable font (`Inter` or `Geist`) utilizing stark contrast in weights (ExtraBold for KPI numbers, regular for microcopy).
- **Layout:** Heavy use of CSS Grid to create distinct, bordered panels with 1px solid off-white borders (`rgba(255,255,255,0.08)`) instead of heavy glassmorphism. Flat, minimalist, and data-dense.

## 2. Application Flow & Tab Structure

### Tab 1: Command Center (Overview Dashboard)
*The primary landing page for the SOC Analyst providing top-down visibility.*
- **Top Bar:** Breadcrumbs, Global Search, Active User Profile.
- **KPI Row:** Total Scanned Assets, Critical Deepfakes Blocked, Global System Latency.
- **Live Ingestion Feed:** A streaming table showing the latest files entering the system (via Scrapers or Manual) with status indicators (e.g., `[Triage..]`, `[Interrogating..]`, `[Matched]`).
- **Urgent Dropzone:** A sleek, minimal drag-and-drop bounding box labeled "Ingest Manual Evidence".

### Tab 2: Threat Analysis (Deep Interrogation View)
*The dedicated workspace for reviewing a specific flagged video.*
- **Split Pane Layout:**
    - **Left Screen:** The Video Player with timeline markers highlighting suspicious frames.
    - **Right Screen - Triage Log:** Shows FFmpeg `dHash`/`aHash` outputs and matching vectors pulled from Pinecone.
    - **Right Screen - Gemini Reasoning:** Renders the JSON output from the Gemini 1.5 Pro multimodal analysis engine, giving a confidence score and reasoning text.
- **Action Dashboard:** Sticky bottom bar allowing the analyst to "Issue Takedown", "Archive as False Positive", or "Escalate".

### Tab 3: Provenance Ledger (Neon DB Logs)
*The cryptographic audit trail.*
- **Data Table:** A dense, paginated table representing the `AssetRecord` table from NeonDB.
- **Features:** Columns for `Asset ID`, `Uploader`, `Timestamp`, and `SHA-256 Hash`. Clicking a row reveals the attached C2PA Manifest signature.

### Tab 4: Scraper Operations (Fleet Management)
*Managing the automated intake vectors.*
- **Workers:** Status cards for YouTube, Reddit, and Telegram mock instances.
- **Controls:** A simple "Invoke Scrape Command" button to manually dispatch the asynchronous queue.

---
## Implemented Antigravity V2 Aesthetic
Here is the actual executed interface captured by our visual testing agent showing the Antigravity minimalist implementation:

![Command Center Navigation Demo](file:///home/shivaji/.gemini/antigravity/brain/c278d785-dc3c-48dd-a56e-2d2f9939eba1/antigravity_ui_rewrite_1777178020262.webp)

![Deep Interrogation Sandbox](file:///home/shivaji/.gemini/antigravity/brain/c278d785-dc3c-48dd-a56e-2d2f9939eba1/forensic_sandbox_view_1777178064709.png)
