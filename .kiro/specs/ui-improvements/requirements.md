# Requirements Document

## Introduction

This feature improves the AXIOM Enterprise SOC Portal UI while preserving the existing design system (Obsidian/Rose dark theme, Royal Blue light theme, Inter font, flat enterprise aesthetic). The improvements target three areas: navigation usability, visual consistency across all panels and components, and surfacing the currently empty or sparse tabs (Deep Interrogation, Pipeline Settings) with meaningful functionality.

The portal serves SOC analysts who need fast, low-friction access to deepfake detection telemetry, forensic asset review, cryptographic provenance records, and scraper fleet management.

---

## Glossary

- **Portal**: The AXIOM Enterprise SOC frontend application (Next.js/React).
- **Sidebar**: The left-hand navigation panel containing module links and user identity.
- **Topbar**: The horizontal bar at the top of the main content area containing breadcrumbs and controls.
- **Active Tab**: The currently selected navigation module rendered in the main content area.
- **KPI Card**: A metric display card showing a single numeric value with a label.
- **Panel**: A bordered surface container (`background: var(--surface-base)`) used to group related content.
- **Status Badge**: A small inline label indicating operational state (e.g., VERIFIED, FRAUD HIT, PROCESSING).
- **Design Token**: A CSS custom property defined in `globals.css` (e.g., `--accent`, `--surface-base`, `--border-muted`).
- **Deep Interrogation Tab**: The forensic analysis workspace for reviewing a specific flagged asset.
- **Pipeline Settings Tab**: The scraper fleet management view for YouTube, Reddit, and Telegram workers.
- **Command Center Tab**: The primary overview dashboard with KPIs and the live ingestion feed.
- **Provenance Ledger Tab**: The cryptographic audit trail table showing C2PA manifest records.
- **Analyst**: An authenticated SOC operator using the Portal.
- **Asset**: A media file (video/image) ingested and processed by the AXIOM backend pipeline.
- **Takedown**: An automated or manual action to remove a flagged asset from a platform.
- **C2PA Manifest**: A cryptographic provenance record attached to an Asset per the C2PA standard.
- **WAF**: Web Application Firewall — Layer 0 of the AXIOM defense architecture.

---

## Requirements

### Requirement 1: Sidebar Navigation Usability

**User Story:** As an Analyst, I want a clear and responsive sidebar navigation, so that I can switch between modules quickly without losing context.

#### Acceptance Criteria

1. THE Portal SHALL render the Sidebar with exactly four navigation items: Overview, Triage Sandbox, Audit Ledger, and Pipeline Hooks.
2. WHEN an Analyst clicks a navigation item, THE Sidebar SHALL apply the `.active` style (left accent border + `--surface-hover` background) to that item and remove it from all other items.
3. WHEN an Analyst clicks a navigation item, THE Topbar breadcrumb SHALL update to reflect the name of the newly Active Tab within 100ms.
4. THE Sidebar SHALL display a keyboard shortcut hint (e.g., `⌘1`) alongside each navigation item label.
5. WHEN an Analyst presses the keyboard shortcut assigned to a navigation item, THE Portal SHALL navigate to that module as if the item were clicked.
6. THE Sidebar SHALL display the authenticated Analyst's identifier and an online status indicator at the bottom of the navigation group.
7. WHEN the Analyst clicks the logout control in the Sidebar, THE Portal SHALL return to the Login Screen and clear the authenticated session state.

---

### Requirement 2: Topbar and Breadcrumb Consistency

**User Story:** As an Analyst, I want the topbar to always reflect my current location and provide quick access to global controls, so that I maintain orientation within the Portal at all times.

#### Acceptance Criteria

1. THE Topbar SHALL display a breadcrumb trail in the format `AXIOM › [Module Name]` for every Active Tab.
2. WHEN the Active Tab changes, THE Topbar breadcrumb SHALL update to the new module name without a full page reload.
3. THE Topbar SHALL display the theme toggle control (light/dark) at all times regardless of the Active Tab.
4. WHEN the Analyst activates the theme toggle, THE Portal SHALL switch between light and dark themes and persist the selection for the duration of the session.
5. THE Topbar SHALL maintain a fixed height of 60px and remain visible when the content area is scrolled.

---

### Requirement 3: Visual Consistency and Design Token Compliance

**User Story:** As an Analyst, I want a visually consistent interface across all tabs, so that the Portal feels like a unified product rather than a collection of disconnected screens.

#### Acceptance Criteria

1. THE Portal SHALL use only Design Tokens defined in `globals.css` for all color, border, radius, and shadow values — no hardcoded hex values outside of `globals.css`.
2. THE Portal SHALL apply the `.panel` class to every bordered surface container across all tabs.
3. THE Portal SHALL apply the `.panel-header` class to every panel title row across all tabs.
4. THE Portal SHALL apply the `.status-badge` class with the appropriate modifier (`.status-green`, `.status-red`) to every inline status indicator across all tabs.
5. THE Portal SHALL apply consistent vertical spacing of `2rem` between major content sections within each tab's content area.
6. THE Portal SHALL render all Asset identifiers and hash values in a monospace font (`font-family: monospace`).
7. THE Portal SHALL apply the `.kpi-card` class to every metric display card across all tabs.
8. WHEN the theme is switched, THE Portal SHALL apply the new theme's Design Tokens to all visible components within 300ms via CSS transition.

---

### Requirement 4: Deep Interrogation Tab — Forensic Workspace

**User Story:** As an Analyst, I want the Deep Interrogation tab to display forensic analysis data for a selected Asset, so that I can review detection evidence and take action without leaving the Portal.

#### Acceptance Criteria

1. WHEN an Analyst clicks a row in the Command Center Pipeline Event Feed, THE Portal SHALL navigate to the Deep Interrogation tab and load the selected Asset's identifier into the forensic workspace.
2. THE Deep Interrogation Tab SHALL display the selected Asset's identifier, origin context, and current pipeline status in a summary header Panel.
3. THE Deep Interrogation Tab SHALL display a Triage Log Panel showing the heuristic analysis results (pHash/aHash match score, audio fingerprint result, and routing decision).
4. THE Deep Interrogation Tab SHALL display a Gemini Reasoning Panel showing the confidence score and reasoning text returned by the Gemini analysis layer, rendered as structured key-value pairs.
5. WHEN no Asset is selected, THE Deep Interrogation Tab SHALL display an empty state with instructional text directing the Analyst to select an asset from the Overview table.
6. THE Deep Interrogation Tab SHALL display an Action Bar with three controls: "Issue Takedown", "Archive as False Positive", and "Escalate to Tier 2".
7. WHEN the Analyst clicks "Issue Takedown", THE Portal SHALL display a confirmation dialog before submitting the takedown request to the backend API.
8. WHEN the Analyst clicks "Archive as False Positive", THE Portal SHALL update the Asset's Status Badge to `ARCHIVED` and disable the Action Bar controls for that Asset.
9. IF the backend API returns an error response to a takedown or escalation request, THEN THE Portal SHALL display an inline error message within the Action Bar describing the failure.

---

### Requirement 5: Pipeline Settings Tab — Scraper Fleet Management

**User Story:** As an Analyst, I want the Pipeline Settings tab to show the operational status of all scraper workers and allow manual dispatch, so that I can monitor and control the automated ingestion pipeline.

#### Acceptance Criteria

1. THE Pipeline Settings Tab SHALL display a status card for each configured scraper worker: YouTube Sync, Reddit Crawler, and Telegram Monitor.
2. EACH scraper status card SHALL display the worker name, current operational status (ACTIVE / IDLE / ERROR), and the timestamp of the last successful scrape run.
3. THE Pipeline Settings Tab SHALL display an "Invoke Scrape" button on each scraper status card.
4. WHEN the Analyst clicks "Invoke Scrape" on a worker card, THE Portal SHALL send a dispatch request to the backend API and display a loading indicator on that card.
5. WHEN the backend API confirms the dispatch, THE Portal SHALL update the worker card's status to ACTIVE and display a success notification.
6. IF the backend API returns an error to a dispatch request, THEN THE Portal SHALL display the error message within the affected worker card and set the card's status badge to ERROR.
7. THE Pipeline Settings Tab SHALL display a global "Invoke All Scrapers" control that dispatches all configured workers simultaneously.

---

### Requirement 6: Command Center Tab — Enhanced KPI and Feed

**User Story:** As an Analyst, I want the Command Center to surface richer telemetry and make the ingestion feed interactive, so that I can triage threats faster from the primary dashboard.

#### Acceptance Criteria

1. THE Command Center Tab SHALL display at least four KPI Cards: Volume Indexed (24h), Cache Intercepts, Critical Incidents, and System Latency.
2. THE Pipeline Event Feed SHALL display columns for: Resource ID, Origin Context, Timestamp, Status, and Routing.
3. WHEN an Analyst clicks a row in the Pipeline Event Feed, THE Portal SHALL navigate to the Deep Interrogation tab with that Asset loaded (satisfying Requirement 4, Criterion 1).
4. THE Pipeline Event Feed rows SHALL be visually differentiated by status: rows with `FRAUD HIT` status SHALL apply a subtle threat-high tint to the row background.
5. THE Command Center Tab SHALL display a "Refresh Feed" control that re-fetches the latest pipeline events from the backend API.
6. WHEN the upload panel receives a file and the backend returns a successful response, THE Portal SHALL display the generated C2PA Manifest issuer and claim generator in a structured result Panel below the upload zone.

---

### Requirement 7: Provenance Ledger Tab — Expanded Record View

**User Story:** As an Analyst, I want to inspect the full C2PA manifest for any provenance record, so that I can verify cryptographic chain of custody for an Asset.

#### Acceptance Criteria

1. THE Provenance Ledger Tab SHALL display a paginated data table with columns: Object Hash (SHA-256), C2PA Standard, Issuer, Timestamp, and Signature Integrity.
2. WHEN an Analyst clicks a row in the Provenance Ledger table, THE Portal SHALL expand an inline detail panel below that row displaying the full C2PA Manifest fields.
3. THE expanded C2PA Manifest detail panel SHALL display at minimum: claim generator, signature issuer, signing timestamp, and asset hash.
4. THE Provenance Ledger Tab SHALL display a total record count above the table.
5. WHEN the Provenance Ledger table has more than 20 records, THE Portal SHALL render pagination controls allowing the Analyst to navigate between pages of 20 records each.
