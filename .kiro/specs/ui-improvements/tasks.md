# Implementation Plan: UI Improvements — AXIOM Enterprise SOC Portal

## Overview

All changes are confined to `frontend/src/app/page.tsx` and `frontend/src/app/globals.css`. No new packages. Tasks are ordered so each step compiles and renders correctly before the next begins.

## Tasks

- [x] 1. Add `--threat-high-rgb` design token to globals.css
  - In the `[data-theme="light"]` block add `--threat-high-rgb: 225, 29, 72;`
  - In the `[data-theme="dark"]` block add `--threat-high-rgb: 239, 68, 68;`
  - This token is consumed by FRAUD HIT row tinting as `rgba(var(--threat-high-rgb), 0.08)`
  - _Requirements: 3.1, 6.4_

- [x] 2. Sidebar — keyboard shortcuts, analyst identity, and `useEffect` keydown listener
  - [x] 2.1 Add shortcut hints to nav items
    - Define a `NAV_ITEMS` config array with `{ key, label, icon, shortcut }` entries for all four tabs
    - Render each nav item from the array; display the shortcut string (e.g. `⌘1`) right-aligned in muted text
    - _Requirements: 1.1, 1.4_
  - [ ]* 2.2 Write property test for shortcut hints present on all nav items
    - **Property 4: Shortcut hints are present on all nav items**
    - **Validates: Requirements 1.4**
  - [x] 2.3 Add `useEffect` keydown listener in `EnterpriseDashboard`
    - Register a `keydown` listener on `document` that maps `Meta+1`–`Meta+4` and `Ctrl+1`–`Ctrl+4` to the corresponding tab keys
    - Clean up the listener on unmount
    - _Requirements: 1.5_
  - [ ]* 2.4 Write property test for keyboard shortcut navigation
    - **Property 3: Keyboard shortcut navigates to correct tab**
    - **Validates: Requirements 1.5**
  - [x] 2.5 Analyst identity row
    - Thread the authenticated email down from `AppRouter` → `EnterpriseDashboard` → `Sidebar` as a prop
    - Render the email (or a fallback `analyst@axiom.internal`) and a green status dot at the bottom of the sidebar
    - _Requirements: 1.6_

- [x] 3. Topbar — AXIOM › breadcrumb using `MODULE_NAMES` map
  - Define `MODULE_NAMES` constant mapping each tab key to its human-readable name
  - Replace the existing `Root › …` breadcrumb with `AXIOM › {MODULE_NAMES[activeTab]}`
  - Pass `activeTab` as a prop to the topbar section (or keep inline — single-file is fine)
  - _Requirements: 2.1, 2.2_
  - [ ]* 3.1 Write property test for breadcrumb reflects active tab
    - **Property 2: Breadcrumb reflects active tab**
    - **Validates: Requirements 1.3, 2.1, 2.2**

- [x] 4. Command Center — 4th KPI card, Timestamp column, clickable rows, FRAUD HIT tinting, Refresh Feed
  - [x] 4.1 Add System Latency KPI card and update grid to 4 columns
    - Change `.kpi-grid` to `grid-template-columns: repeat(4, 1fr)` inline or via a modifier class
    - Add a 4th `.kpi-card` for System Latency; measure backend response time via `GET /health` in a `useEffect`; fall back to `"N/A"` when unreachable
    - _Requirements: 6.1_
  - [x] 4.2 Add Timestamp column to Pipeline Event Feed and promote feed data to state
    - Define a `FeedRow` interface and a `MOCK_FEED` constant with at least 5 rows including `timestamp`, `triageData`, and `geminiData` fields
    - Lift feed rows into `feedRows` state in `EnterpriseDashboard`
    - Add `<th>Timestamp</th>` and the corresponding `<td>` to the feed table
    - _Requirements: 6.2_
  - [ ]* 4.3 Write property test for FRAUD HIT row tinting
    - **Property 16: FRAUD HIT rows receive threat tint**
    - **Validates: Requirements 6.4**
  - [x] 4.4 Make feed rows clickable — navigate to Deep Interrogation
    - Add `onClick` to each `<tr>` that calls `setSelectedAsset(row)` and `setActiveTab('interrogation')`
    - Apply `cursor: pointer` to feed rows
    - Apply `background: rgba(var(--threat-high-rgb), 0.08)` inline style to rows where `status === 'FRAUD HIT'`
    - _Requirements: 4.1, 6.3, 6.4_
  - [ ]* 4.5 Write property test for feed row click navigates to Deep Interrogation
    - **Property 9: Feed row click loads asset in Deep Interrogation**
    - **Validates: Requirements 4.1, 6.3**
  - [x] 4.6 Add Refresh Feed button
    - Render a `btn-secondary` "Refresh Feed" button in the `.panel-header` row of the Pipeline Event Feed panel
    - Clicking it calls a `refreshFeed()` function that resets `feedRows` to the mock data (or re-fetches from backend)
    - _Requirements: 6.5_

- [x] 5. Deep Interrogation tab — full forensic workspace
  - [x] 5.1 Define data interfaces and thread `selectedAsset` state
    - Add `TriageData`, `GeminiData`, and `Asset` (= `FeedRow`) TypeScript interfaces at the top of `page.tsx`
    - Add `selectedAsset: Asset | null` state to `EnterpriseDashboard`; pass it and a setter to the interrogation tab
    - _Requirements: 4.1, 4.2_
  - [x] 5.2 Empty state panel
    - When `selectedAsset` is `null`, render a `.panel` with centered `Search` icon and instructional text
    - _Requirements: 4.5_
  - [x] 5.3 Asset Summary header panel
    - When `selectedAsset` is set, render a `.panel` with `.panel-header` "Asset Summary"
    - Display Asset ID in `font-family: monospace`, Origin Context, and a `.status-badge` for Pipeline Status
    - _Requirements: 4.2, 3.6_
  - [ ]* 5.4 Write property test for Deep Interrogation summary panel fields
    - **Property 10: Deep Interrogation summary panel contains required fields**
    - **Validates: Requirements 4.2**
  - [x] 5.5 Triage Log panel
    - Render a `.panel` with `.panel-header` "Triage Log"
    - Display key-value rows: pHash Match Score, aHash Match Score, Audio Fingerprint, Routing Decision from `selectedAsset.triageData`
    - _Requirements: 4.3_
  - [x] 5.6 Gemini Reasoning panel
    - Render a `.panel` with `.panel-header` "Gemini Analysis"
    - Display key-value rows: Confidence Score, Classification, Recommended Action, Forensic Signals from `selectedAsset.geminiData`
    - _Requirements: 4.4_
  - [x] 5.7 Action Bar — Issue Takedown, Archive, Escalate
    - Render three buttons: `btn-primary` "Issue Takedown", `btn-secondary` "Archive as False Positive", `btn-secondary` "Escalate to Tier 2"
    - "Issue Takedown" calls `window.confirm` then `POST /api/interrogate`; on API error render inline error message below the bar
    - "Archive as False Positive" sets local status to `ARCHIVED` and disables all three buttons
    - "Escalate to Tier 2" calls `POST /api/interrogate` with escalation payload; on error render inline error
    - _Requirements: 4.6, 4.7, 4.8, 4.9_
  - [ ] 5.8 Write property test for Archive action disables controls
    - **Property 11: Archive action updates status badge and disables controls**
    - **Validates: Requirements 4.8**
  - [ ] 5.9 Write property test for API error surfaces inline in Action Bar
    - **Property 12: API error surfaces inline in Action Bar**
    - **Validates: Requirements 4.9**

- [ ] 6. Checkpoint — ensure Command Center and Deep Interrogation render without errors
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Pipeline Settings tab — 3 worker cards and Invoke All Scrapers
  - [x] 7.1 Define `WorkerStatus` interface and `WORKERS` config array
    - Add `WorkerStatus` interface with `id`, `name`, `status`, `lastRun`, `loading`, `error` fields
    - Define `WORKERS` constant for YouTube Sync, Reddit Crawler, Telegram Monitor
    - Add `workerStatuses` state to `EnterpriseDashboard` initialised from `WORKERS`
    - _Requirements: 5.1, 5.2_
  - [x] 7.2 Render worker cards
    - Replace the existing placeholder cards with cards rendered from `workerStatuses`
    - Each card is a `.panel` with `.panel-header` (worker name), `.status-badge`, monospace last-run timestamp, and "Invoke Scrape" `btn-secondary` button
    - _Requirements: 5.1, 5.2, 5.3_
  - [ ]* 7.3 Write property test for worker card displays name, status, and timestamp
    - **Property 13: Worker card displays name, status, and timestamp**
    - **Validates: Requirements 5.2**
  - [x] 7.4 Invoke Scrape per-card action
    - Clicking "Invoke Scrape" sets `loading: true` on that card, calls `GET /api/scrapers/trigger?platform={id}`
    - On success set `status: 'ACTIVE'`; on error set `status: 'ERROR'` and `error: message`
    - _Requirements: 5.4, 5.5, 5.6_
  - [ ]* 7.5 Write property test for successful dispatch updates worker status to ACTIVE
    - **Property 14: Successful dispatch updates worker status to ACTIVE**
    - **Validates: Requirements 5.5**
  - [ ]* 7.6 Write property test for failed dispatch shows error in worker card
    - **Property 15: Failed dispatch shows error in worker card**
    - **Validates: Requirements 5.6**
  - [x] 7.7 Invoke All Scrapers global button
    - Render a `btn-primary` "Invoke All Scrapers" button above the worker cards
    - Clicking it fans out `invokeWorker()` for all three workers simultaneously
    - _Requirements: 5.7_

- [x] 8. Provenance Ledger tab — expandable rows, record count, pagination
  - [x] 8.1 Define `ProvenanceRecord` interface and mock dataset
    - Add `ProvenanceRecord` interface with all fields including expanded detail fields
    - Create `MOCK_PROVENANCE` array with 25+ records to exercise pagination
    - Add `provenanceRecords`, `provenancePage`, and `expandedRowId` state to `EnterpriseDashboard`
    - _Requirements: 7.1, 7.4, 7.5_
  - [x] 8.2 Add Timestamp column and record count label
    - Add `<th>Timestamp</th>` to the ledger table header
    - Render `{provenanceRecords.length} records` above the table in muted text
    - _Requirements: 7.1, 7.4_
  - [x] 8.3 Expandable row detail panel
    - Each `<tr>` gets an `onClick` that toggles `expandedRowId`
    - When a row is expanded, insert a `<tr>` immediately below it containing a `.panel` with a 2-column key-value grid: Claim Generator, Signature Issuer, Signing Timestamp, Asset Hash
    - _Requirements: 7.2, 7.3_
  - [ ]* 8.4 Write property test for provenance row expansion shows all C2PA fields
    - **Property 17: Provenance row expansion shows all C2PA fields**
    - **Validates: Requirements 7.2, 7.3**
  - [ ]* 8.5 Write property test for record count matches dataset length
    - **Property 18: Record count matches dataset length**
    - **Validates: Requirements 7.4**
  - [x] 8.6 Pagination controls
    - Slice `provenanceRecords` to 20 per page using `provenancePage`
    - Render Previous / Next buttons and "Page X of Y" label only when `provenanceRecords.length > 20`
    - Clamp `provenancePage` to `[1, totalPages]`
    - _Requirements: 7.5_
  - [ ]* 8.7 Write property test for pagination renders iff record count exceeds 20
    - **Property 19: Pagination renders iff record count exceeds 20**
    - **Validates: Requirements 7.5**

- [x] 9. Visual consistency pass — enforce design tokens and shared CSS classes
  - Audit every inline style in `page.tsx` and replace any hardcoded hex/rgba colour values with CSS custom property references
  - Ensure every bordered surface container uses `.panel` and `.panel-header`
  - Ensure every status indicator uses `.status-badge` with `.status-green` or `.status-red`
  - Ensure every KPI card uses `.kpi-card` and `.kpi-label`
  - Ensure all asset IDs and hash values have `font-family: monospace`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7_
  - [ ]* 9.1 Write property test for status badges use correct CSS class
    - **Property 7: Status badges use the correct CSS class**
    - **Validates: Requirements 3.4**
  - [ ]* 9.2 Write property test for asset identifiers are monospace
    - **Property 8: Asset identifiers and hashes are monospace**
    - **Validates: Requirements 3.6**

- [ ] 10. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `fast-check` (already available as a dev dependency)
- Tag format for property tests: `// Feature: ui-improvements, Property {N}: {property_text}`
