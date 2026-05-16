# Feature Tracking

## Post-Clean-Room Baseline (May 15, 2026)

| Feature | Audit Summary | Status |
| :--- | :--- | :--- |
| **Pipeline Orchestrator Redesign** | Refactored Index.html for split-screen workspace, horizontal tabs, Omnibox, Simulate button, and Master Safety Toggles. Wired dynamic Mermaid rendering and backend simulate hook. | [DEPLOYED/PRODUCTION READY] |
| **Live VQB Analytics Telemetry** | Added unified control bar with Date Picker, Source Dropdown, Status Toggle. Dynamically fetching `/api/analytics/heatmap` and `/api/analytics/sankey` for live visualization. | [DEPLOYED/PRODUCTION READY] |
| **Batch Ingestion Dashboard** | Added "Batch Ingestion" tab with Quota Dashboard, Control Bar, and Staging Table. Wired frontend to generate bulk payloads and POST to `/api/batch/process`. | [DEPLOYED/PRODUCTION READY] |
| **Array Batching & Simulation Routes** | Implemented `run_bulk_profiler`, `run_bulk_classifier`. Added `/api/batch/process` and `/api/orchestrator/simulate` backend endpoints. | Deployed (May 15, 2026) |
| **Schema Expansion & Pipeline Safety** | Expanded `entities` with `workspace_alias` and `parent_entity_id`. Added `aliases` table. Implemented safe-mode pipeline toggles. | Deployed (May 15, 2026) |
| **Zero Trust Ingestion Pipelines** | Implemented contacts, gmail, and drive pipelines routing directly to the `quarantine_queue`. | Deployed (May 13, 2026) |
| **Legacy SQL Refactor** | Refactored main.py and sync_engine.py queries to match Zero Trust schema (`categories`, `entities`, `purposes`). Purged legacy table logic. | Deployed (May 14, 2026) |

## Future Epic Backlog

### Automated DX Debug Panel & GitHub Issue Generator
**Concept:** A dedicated UI tab for administrators to view system, API, and LLM errors. Users can select specific error logs and trigger an AI-assisted action to generate a sanitized, GitHub-ready bug report.
**Status:** Drafting / Backlog (Target: Epic 5)

### The Edge Node SMS/RCS Forwarder
**Core Objective:** Bypass the lack of a public Google Messages REST API by utilizing the user's Android device as a secure, automated edge node. Treats mobile text messages with the same ingestion and classification rigor as emails or Drive documents.
**Status:** Drafting / Backlog

### Universal IMAP Ingestion (Provider-Agnostic Sync)
**Core Objective:** Break the hard dependency on the Google Workspace API by implementing a standard IMAP client within the Python backend, allowing Nexus to ingest unstructured communications from any standard email provider.
**Status:** Drafting / Backlog

## Bugs & Hotfixes

| Bug Description | Resolution |
| :--- | :--- |
| *Bug Tracking:* All bugs must be documented here utilizing this standard two-column format. | |
