# Changelog

All notable changes to the Nexus for Google project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.12] - 2026-05-16
### Changed
- **Layer 7:** Wired the Legacy Label Migration engine in the Global Settings UI to the backend `/api/ingestion/legacy-labels/preview` and `/api/ingestion/legacy-labels/execute` endpoints.
- **Layer 7:** Updated the Legacy Label staging table in `Index.html` to display category mapping dropdowns and canonical entity badges.

## [v1.1.11] - 2026-05-16
### Changed
- **Layer 2:** Rewrote `/api/analytics/heatmap` and `/api/analytics/sankey` endpoints in `main.py` to use dynamic SQL telemetry targeting `Workspace_Artifacts`, effectively replacing the initial dummy data generators and adhering to VQB formatting specs.

## [v1.1.10] - 2026-05-16
### Added
- **System:** Added `write_migration_trace` in `diagnostics.py` to heavily instrument the Legacy Label Migration Engine with physical logging.
- **Layer 2:** Implemented `fetch_legacy_gmail_labels` in `sync_engine.py` to extract non-system Gmail labels and trace the output.
- **Layer 4/5:** Implemented `deduplicate_legacy_labels` and `profile_and_map_entities` in `llm_engine.py` to perform search-grounded mapping and tracing.
- **Layer 3:** Built orchestration endpoints `POST /api/ingestion/legacy-labels/preview` and `execute` in `main.py` applying strict Layer 1 transaction blocks.

## [v1.1.9] - 2026-05-16
### Changed
- **Layer 7:** Updated the Orchestrator UI (`Index.html`) to replace generic bypass placeholders with explicit Google Workspace `CATEGORY_*` bypass checkboxes and domain whitelist textareas for the Gmail pipeline.
- **Layer 7:** Deployed dynamic, labeled `readonly` textareas within the 'Master Prompt' sections of the Gmail and Drive panels to securely expose live Layer 4 and Layer 5 AI parameters.

## [v1.1.8] - 2026-05-16
### Changed
- **Layer 7:** Updated `loadZeroTrustFlow` in `JS_Actions.html` to dynamically fetch the taxonomy tree from the live database. Implemented graceful empty state placeholders for initial 'Day 0' entity sets without crashing the UI.
### Added
- **Layer 2:** Added `GET /api/taxonomy/tree` endpoint in `main.py` that queries `categories` and `purposes`, explicitly attaching empty `entities: []` arrays to satisfy UI bindings while preserving strictly read-only Layer 1 database compliance.

## [v1.1.7] - 2026-05-16
### Changed
- **Layer 7:** Implemented `loadPipelineSettings` dual-fetch logic in `JS_Actions.html` to dynamically fetch UI settings and `Config_Prompts` master templates from the backend, populating the new Orchestrator textareas.

## [v1.1.6] - 2026-05-16
### Added
- **Layer 2:** Restored `GET /api/prompts` route in `main.py` to serve master templates from `Config_Prompts` to the Orchestrator UI.
- **Layer 2:** Explicitly verified `GET /api/analytics/heatmap` and `GET /api/analytics/sankey` endpoints return the exact strict JSON schema required by VQB.

## [v1.1.5] - 2026-05-16
### Changed
- **Layer 7:** Updated Mermaid.js flows in Orchestrator UI (`JS_Actions.html`) to accurately reflect the 7-Layer Array Batching architecture.

## [v1.1.4] - 2026-05-16
### Changed
- **Layer 7:** Fixed ES6 'const' redeclaration crash by changing `appState` and `appActions` to `var` in `JS_State.html` and `JS_Actions.html`.
- **Layer 7:** Removed duplicate inclusions of script files from the bottom of `Index.html`.
### Added
- **Layer 2:** Implemented `GET /api/analytics/heatmap` telemetry route querying `Artifact_History` to return temporal data.
- **Layer 2:** Implemented `GET /api/analytics/sankey` telemetry route mapping the flow from category to purpose across `Workspace_Artifacts`.

## [v1.1.3] - 2026-05-16
### Added
- **Layer 2:** Added `POST /api/orchestrator/run-now/{pipeline_name}` endpoint in `main.py` utilizing `fastapi.BackgroundTasks` to manually trigger synchronous sync engine workers.
- **Layer 7:** Added "Run Pipeline Now" button to Orchestrator UI settings panels and implemented corresponding `appActions.runPipelineNow` fetch logic in `JS_Actions.html`.

## [v1.1.2] - 2026-05-16
### Changed
- **Layer 7:** Updated Orchestrator UI (`Index.html`) to replace generic settings with specific Zero Trust Bypass Rules for Gmail and Drive.
- **Layer 7:** Implemented `savePipelineConfig` serialization logic in `JS_Actions.html`.
- **Layer 7:** Updated Mermaid flow diagrams to reflect accurate pipeline architecture (Extract -> Bypass -> Array Batching -> Layer 4 -> Layer 5 -> Materialize/Quarantine).

## [v1.1.1] - 2026-05-16
### Changed
- **Layer 4:** Refactored `agent_profiler_commercial.tmpl` to focus exclusively on entity identification and output a precise JSON schema with `workspace_alias`.
- **Layer 5:** Refactored `agent_classifier.tmpl` to focus exclusively on intent and taxonomy categorization, outputting a precise JSON array schema.

## [v1.1.0] - 2026-05-16
### Added
- **Layer 2:** Implemented `fetch_legacy_gmail_labels` to extract user custom labels via the Gmail API, filtering system labels.
- **Layer 3:** Added `/api/ingestion/legacy-labels/preview` and `/api/ingestion/legacy-labels/execute` orchestration routes for the Legacy Label Migration Engine.
- **Layer 4/5:** Created `deduplicate_legacy_labels` and `profile_and_map_entities` for AI-powered deduplication and mapping.
- **Layer 1:** Added transactional execution block to ensure strict schema integrity during legacy label ingestion.

## [v1.0.0] - 2026-05-15
### Added
- **Layer 1:** Established Clean-Room SQLite schema with WAL journaling, strict foreign keys, and hierarchical entity structures.
- **Layer 2:** Implemented O(1) Array Batching architecture for optimized Gemini API token economy.
- **Layer 7:** Deployed split-screen Orchestrator UI, contextual Omnibox Simulation engine, and live telemetry Data Binding.

### Changed
- **System:** Executed V3 Exhaustive Matrix Purge, eliminating all orphaned API routes, dead UI triggers, and unlinked Apps Script webhooks.
- **Governance:** Instantiated dual-linked AI Governance profiles (Cline/GCA) enforcing the 7-Layer Description Model.