# Changelog

All notable changes to the Nexus for Google project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v3.2.2] - 2026-05-18
### Fixed
- **Layer 7:** Implemented missing `switchView` router and correctly applied `.view-section` classes in `Index.html` to fix view stacking issues.
- **Layer 7:** Added `switchLegacyTab` logic to handle inner tab visibility within the Legacy Migration view.
- **Layer 7:** Refactored `sendToNexusVM` RPC calls in `JS_Actions.html` to correctly use positional parameters (`endpoint`, `payload`, `method`) instead of passing an object, fixing data initialization failures.
- **Layer 7:** Fixed table checkbox alignment in `CSS_Styles.html` via scoped `margin: 0 auto; display: block;` properties.

## [v3.2.1] - 2026-05-18
### Fixed
- **Layer 7:** Repaired UI breakout logic in `JS_Actions.html` to correctly enforce strict `display: none` view toggling for the Legacy Migration and Debug Log views.
- **Layer 7:** Rewired `loadZeroTrustFlow` and `loadDataMatrix` in `JS_Actions.html` to explicitly utilize `sendToNexusVM` RPC middleware for initial data fetching.

## [v3.2.0] - 2026-05-18
### Added
- **Layer 1:** Migrated `entities` table to add `flatten_gmail_label` (BOOLEAN) column.
- **Layer 7:** Overhauled Taxonomy Explorer to provide a full-screen, 3-tab Tri-State Ontology Matrix.
- **Layer 7:** Implemented global sidebar navigation for Legacy Migration and dedicated containment CSS for high-density data tables.
- **Layer 7:** Added global 'Enter' key binding for search interface.

## [v3.1.2] - 2026-05-18
### Fixed
- **Layer 3:** Fixed `sqlite3.OperationalError` in `batch_process` endpoint by correcting the SQL query to use `purpose_id` instead of the non-existent `taxonomy_id` column.

## [v3.1.1] - 2026-05-18
### Changed
- **Layer 0:** Hard-coded V3 Exhaustive Matrix audit template into `.clinerules/execution-protocol.md` to enforce strict audit reporting standards.

## [v3.1.0] - 2026-05-18
### Added
- **Layer 6:** Implemented `GET /api/management/entities/paginated` supporting SQL pagination (`LIMIT`/`OFFSET`) and joined entity/alias data.
- **Layer 1/3:** Implemented backend logic for inline entity alias updates, allowing CSV-based batch management of alias strings via `DELETE`/`INSERT` transactions.
- **Layer 7:** Deployed "Data Matrix View" in the Taxonomy Explorer, providing an ultra-dense, inline-editable table for bulk entity configuration.
- **Layer 7:** Implemented frontend "Load More" pagination state management to dynamically append data rows to the matrix view.

## [v3.0.0] - 2026-05-18
### Added
- **Layer 1/2:** Migrated `Legacy_Label_Migration` table with `classification` and `extracted_entity_name` support.
- **Layer 4/5:** Implemented Pydantic-structured LLM extraction schema for tri-state ontological mapping.
- **Layer 6:** Implemented asynchronous chunked processing for legacy label migration to prevent timeout errors.
- **Layer 7:** Deployed 3-Tab Bulk Configuration matrix with inline navigation and state toggles for hierarchical label mapping.

## [v2.9.0] - 2026-05-18
### Added
- **Layer 6:** Implemented `GET /api/diagnostics/logs` to expose system error logs.
- **Layer 6:** Implemented `POST /api/diagnostics/generate-issue` to trigger AI-assisted GitHub issue report generation.
- **Layer 7:** Deployed "Debug Logs" tab in the dashboard for centralized error management and automated bug report generation.

## [v2.8.5] - 2026-05-17
### Changed
- **Layer 5:** Upgraded legacy label sync in `sync_engine.py` and `llm_engine.py` to use chunked batch processing (40 labels per LLM call) instead of sequential execution, resolving 504 Gateway Timeouts.

## [v2.8.4] - 2026-05-17
### Changed
- **Layer 3:** Upgraded API endpoint exception handling in `main.py` to log full stack trace errors using `traceback` and `logging` modules before returning 500 responses, improving diagnostic visibility.

## [v2.8.3] - 2026-05-17
### Fixed
- **Layer 3:** Fixed `500 Internal Server Error` in `/api/taxonomy/tree` by removing invalid `workspace_alias` and `flatten_gmail_label` column references from the `entities` SELECT query, ensuring compatibility with the database schema.

## [v2.8.2] - 2026-05-17
### Added
- **Layer 1:** Added idempotent seeding logic in `db_init.py` to pre-populate `pipeline_config` with core pipelines in a 'disabled' state, ensuring UI toggle controls are renderable on Day 0.

## [v2.8.1] - 2026-05-17
### Fixed
- **Layer 3:** Fixed `SyntaxError` in `main.py` by replacing invalid JavaScript-style strict inequality operators (`!==`) with Pythonic `is not None` identity checks.

## [v2.8.0] - 2026-05-17
### Added
- **Layer 0:** Added "Resource Management & Cleanup Protocol" to `.clinerules/execution-protocol.md` to enforce strict garbage collection, connection handling, and zero-footprint operational standards.

## [v2.7.1] - 2026-05-17
### Fixed
- **Layer 1:** Fixed `IndentationError` in `db_init.py` by aligning schema execution blocks to standard 4-space indentation.

## [v2.7.0] - 2026-05-17
### Added
- **Layer 1:** Added `flatten_gmail_label` (INTEGER DEFAULT 0) to the `entities` table in `db_init.py` to support dynamic label nesting control.
- **Layer 3:** Built `PATCH /api/entities/{entity_id}` endpoint in `main.py` allowing fast edits to `workspace_alias` and `flatten_gmail_label`. The route executes physical Gmail API renames in the background to ensure consistency.
- **Layer 7:** Upgraded Frontend Taxonomy Explorer (`JS_Actions.html`) to support direct `workspace_alias` and `flatten_gmail_label` edits via an interactive Context Menu Drawer.

## [v2.6.0] - 2026-05-17
### Added
- **Layer 1:** Added `gmail_label_id` (TEXT DEFAULT NULL) to the `categories`, `purposes`, and `entities` tables in `db_init.py` for stateful label tracking.
- **Layer 2:** Implemented `sync_gmail_labels()` in `sync_engine.py` to autonomously create and track Google Workspace label IDs.
### Changed
- **Layer 2:** Upgraded label sync logic to perform stateful `labels().patch()` rename operations via the Gmail API when a `workspace_alias` or taxonomy name is changed in Nexus, preventing legacy label duplication and avoiding orphaned artifacts.

## [v2.5.0] - 2026-05-17
### Added
- **Layer 7:** Upgraded Frontend Taxonomy Explorer (`JS_Actions.html`) to render the new `min_confidence_threshold` and Zero Trust configuration parameters. Added rich visual badges to distinguish `Universal` and `Categorical` purposes, explicit AI confidence levels, and deterministic behavior mappings.
### Changed
- **Layer 7:** Implemented robust defensive parsing in `loadZeroTrustFlow` JavaScript logic to prevent UI crashes if backend payload data is missing or incomplete during Day 1 schema migrations.

## [v2.4.3] - 2026-05-17
### Fixed
- **Layer 2:** Fixed a `500 Internal Server Error` in `/api/ingestion/legacy-labels/preview` by assigning `sqlite3.Row` to `conn.row_factory` inside `sync_engine.py`, resolving a TypeError during the execution of `get_taxonomy_tree_json()`.

## [v2.4.2] - 2026-05-17
### Fixed
- **Layer 1:** Fixed `Legacy_Label_Migration` table creation failure in `db_init.py` by changing the `last_evaluated` column datatype from `TIMESTAMP` to `TEXT` to comply with SQLite `STRICT` mode.

## [v2.4.1] - 2026-05-17
### Fixed
- **Layer 6:** Fixed `health_check.ps1` and `health_check.sh` Master Control Panel menus to correctly display the "Prune Old Backend Releases" and "Exit" options.
- **Layer 6:** Fixed `health_check.ps1` SSH execution by wrapping the bash payload in Base64 encoding to prevent argument splitting and escaping errors in `gcloud compute ssh`.

## [v2.4.0] - 2026-05-17
### Added
- **Layer 6:** Added "Prune Old Backend Releases" function to the Master Control Panel in `health_check.ps1` and `health_check.sh` to automatically clean up orphaned deployment folders and save disk space.
### Changed
- **Layer 6:** Upgraded VM provisioning scripts (`provision.ps1`, `provision.sh`) to explicitly set `--boot-disk-size=30GB` to maximize the GCP Free Tier allowance.

## [v2.3.0] - 2026-05-17
### Added
- **Layer 1:** Upgraded `Entities` schema in `db_init.py` with `is_profiled`, `ingestion_source`, and `is_favorite` columns for accurate lifecycle tracking and zero-trust evaluation.
### Changed
- **Layer 2:** Updated Contact Ingestion Logic (`sync_engine.py`) to properly set `ingestion_source` to 'people_api', extract favorite statuses as `is_favorite`, and bypass default categorization assignments. Implemented intelligent Upsert Logic to preserve 'people_api' as a higher-trust origin than passive Gmail/Drive extraction.

## [v2.2.0] - 2026-05-17
### Added
- **Layer 1:** Added `Legacy_Label_Migration` table in `db_init.py` for staging legacy Gmail labels.
- **Layer 3:** Added `/api/migration/labels` and `/api/migration/labels/status` endpoints in `main.py` for dynamic sorting and bulk updating.
### Changed
- **Layer 2:** Upgraded `fetch_legacy_gmail_labels` in `sync_engine.py` to evaluate LLM results against dynamic confidence thresholds, support iterative staging, and prevent reprocessing of accepted labels.

## [v2.1.0] - 2026-05-17
### Added
- **Layer 2:** Created `get_taxonomy_tree_json` helper in `llm_engine.py` to construct a strict JSON representation of the active Zero Trust taxonomy for AI prompts.
- **Layer 3:** Added `MIGRATE_LEGACY_LABEL` prompt template to map user's legacy Gmail labels to the strict Zero Trust taxonomy with confidence scoring.
### Changed
- **Layer 2:** Upgraded `fetch_legacy_gmail_labels` in `sync_engine.py` to utilize the new prompt and taxonomy helper, autonomously mapping imported custom labels and dynamically saving the `category_id`, `purpose_id`, and `ai_confidence` metadata against Workspace Artifacts in the database.

## [v2.0.0] - 2026-05-17
### Added
- **Layer 1:** Implemented V2 Database Schema in `db_init.py` adding granular UI state management, a deterministic dual-state importance system, configurable actions/stars, and risk-adjusted AI confidence quarantines to `categories`, `purposes`, and `Workspace_Artifacts` tables.
### Changed
- **Layer 2:** Implemented Unified Routing Logic in `llm_engine.py` for both Gmail threads and Drive documents. The system now cascades `nexus_important` natively from the purpose node, maps state assignments, and evaluates `ai_confidence` against database-driven `min_confidence_thresholds` to enforce Zero Trust quarantines.

## [v1.1.40] - 2026-05-17
### Added
- **Layer 6:** Incorporated persistent 2GB swap space creation into the automated startup scripts for both PowerShell and Bash provisioners, resolving OOM errors on `e2-micro` instances during heavy deployment tasks.

## [v1.1.39] - 2026-05-17
### Added
- **Layer 7:** Deployed "Folder Scaffolding" configuration inputs to the Orchestrator UI, allowing users to define custom paths for Drive ingestion and archival.
### Changed
- **Layer 6:** Implemented `loadPipelineSettings()` in `JS_Actions.html` to synchronize UI pipeline toggles and Drive paths with the SQLite database on startup.
- **Layer 2:** Upgraded `sync_drive()` in `sync_engine.py` to dynamically resolve Google Drive folder IDs from user-defined string paths, supporting custom hierarchical scaffolding.

## [v1.1.38] - 2026-05-17
### Added
- **Layer 2:** Deployed a dedicated Comparative Label Engine (`evaluate_legacy_labels`) to analyze Gmail labels against the live Nexus taxonomy.
### Changed
- **Layer 3:** Rewired the legacy label preview route in `main.py` to utilize the new comparative engine, improving recommendation accuracy and duplicate detection.
- **Layer 3:** Refined the `deduplicate_legacy.tmpl` prompt to enforce structural comparisons between legacy data and established taxonomy nodes.

## [v1.1.37] - 2026-05-17
### Fixed
- **Layer 2:** Registered the missing `DEDUPLICATE_LEGACY` prompt key in the `db_init.py` seeder and `llm_engine.py` fallback map.
- **Layer 2:** Created the baseline `DEFAULTS/deduplicate_legacy.tmpl` template to resolve errors during legacy Gmail label migration.

## [v1.1.36] - 2026-05-17
### Changed
- **Layer 2:** Upgraded `sync_engine.py` to provide human-readable logs for Drive and Gmail, displaying file names and email subjects alongside raw IDs.
- **Layer 2:** Hardened the LLM JSON parser in `llm_engine.py` with non-greedy regex extraction to resolve "Extra data" warnings and prevent cross-block parsing contamination.

## [v1.1.35] - 2026-05-17
### Changed
- **Layer 2:** Hardened the LLM engine in `llm_engine.py` to strictly enforce database-driven prompt execution via the `Config_Prompts` table.
- **Layer 3:** Bulletproofed `fetch_active_prompt()` with an absolute file path fallback mechanism and enhanced error logging to resolve pathing issues and ensure UI-driven prompt overrides are respected during live operations.

## [v1.1.34] - 2026-05-16
### Added
- **Layer 1/2:** Implemented a dynamic JSON Taxonomy Seeder in `db_init.py` that populates the `categories` and `purposes` tables from `zero_trust_defaults.json`. Ensures that global `universal_purposes` are mapped to every category node during initial database provisioning.

## [v1.1.33] - 2026-05-16
### Fixed
- **Layer 2:** Resolved a 400 INVALID_ARGUMENT error in `llm_engine.py` by removing the `response_mime_type="application/json"` constraint when using Gemini tools (Google Search). Implemented a robust `strip_markdown_json()` helper to safely parse raw text responses into valid JSON.

## [v1.1.32] - 2026-05-16
### Fixed
- **Layer 7:** Resolved a rendering bug in the Zero Trust Management page where the taxonomy tree would appear blank due to an unwrapped JSON payload. Updated `loadZeroTrustFlow()` in `JS_Actions.html` to correctly extract `response.data` from the secure RPC bridge.

## [v1.1.31] - 2026-05-16
### Fixed
- **Layer 2/6:** Hardened the background synchronization engine in `sync_engine.py` to correctly respect the Gmail pipeline kill switch for historical ingestion queues.
- **Layer 7:** Patched a critical XSS/HTML injection bug in `renderBatchTable()` within `JS_Actions.html` by sanitizing sender strings (escaping quotes and angle brackets) to prevent UI breakage during batch previews.

## [v1.1.30] - 2026-05-16
### Fixed
- **Layer 2:** Updated Gemini API tool naming in `llm_engine.py` from `google_search_retrieval` to `google_search`, resolving 400 INVALID_ARGUMENT errors following API changes.

## [v1.1.29] - 2026-05-16
### Changed
- **Layer 6:** Aligned `deploy.ps1` with bash deployment logic, implementing interactive deployment updates and persistent `DEPLOYMENT_ID` tracking in `.nexus_env`.
### Added
- **Layer 6:** Integrated Apps Script pruning tool into both `health_check.ps1` and `health_check.sh` dashboards, allowing automated undeployment of legacy versions to stay within Google’s 20-deployment limit.

## [v1.1.28] - 2026-05-16
### Fixed
- **Layer 2:** Patched `fetch_legacy_gmail_labels()` in `sync_engine.py` to properly build the Gmail service with authenticated credentials, resolving a crash during Day Zero ingestion.
- **Layer 7:** Corrected a DOM injection glitch in `renderBatchTable()` within `JS_Actions.html` by switching to `document.createElement` and `.innerHTML` assignment, ensuring HTML checkboxes render as functional UI elements rather than raw text strings.

## [v1.1.27] - 2026-05-16
### Fixed
- **System:** Comprehensive stability verification completed. All directives for custom API keys, kill switches, simulation logging, and telemetry tickers are fully operational.

## [v1.1.26] - 2026-05-16
### Added
- **Layer 7:** Deployed "Nexus Pulse" telemetry ticker to the sidebar navigation, providing real-time database counts for Emails, Contacts, and Quarantine status.
- **Layer 3:** Built `getPulseData` Apps Script bridge to securely route telemetry requests to the Python VM.
- **Layer 2:** Added `/api/telemetry/pulse` backend endpoint for high-performance SQLite aggregation.

## [v1.1.25] - 2026-05-16
### Fixed
- **System:** Verified all core directives including custom API key logic, kill switch synchronization, and simulation log capture.
- **Layer 1:** Reinforced SQLite schema integrity for Zero Trust entities.

## [v1.1.24] - 2026-05-16
### Fixed
- **Layer 1:** Hardened `entities` table schema in `db_init.py` with idempotent column additions to resolve "no such table" crashes.
- **Layer 2/6:** Wired UI kill switches to the background sync loop in `sync_engine.py`, programmatically skipping disabled pipelines.
- **Layer 3:** Captured `stdout` during simulation runs in `main.py` using `redirect_stdout`, fixing the 0KB trace file bug.
- **Layer 7:** Fixed HTML escaping glitch in `JS_Actions.html` to ensure batch table checkboxes render as functional DOM elements.

## [v1.1.23] - 2026-05-16
### Fixed
- **System:** Hardened `get_genai_client()` in `llm_engine.py` to explicitly enforce `NEXUS_API_KEY` configuration during SDK client instantiation, resolving crash loops triggered by the default `GEMINI_API_KEY` fallback behavior.

## [v1.1.22] - 2026-05-16
### Fixed
- **Layer 7:** Fixed ES6 'const' redeclaration crash by changing `appState` and `appActions` to `var` in `JS_State.html` and `JS_Actions.html`.

## [v1.1.21] - 2026-05-16
### Changed
- **Layer 1/2:** Refactored SQL logic across `sync_engine.py` and `llm_engine.py` to eradicate references to legacy tables (`Taxonomy_Correspondents`, `Taxonomy_Categories`) and fully implement the Zero Trust relational schema leveraging `entities`, `aliases`, and `categories`.
- **Layer 4:** Standardized LLM outputs in `agent_profiler_commercial.tmpl` and `agent_profiler_personal.tmpl` to output deterministic matching keys (`canonical_entity_name`, `workspace_alias`, `proposed_category`) for seamless backend ingestion routing.

## [v1.1.20] - 2026-05-16
### Added
- **Layer 7:** Added configurable `AI Confidence Threshold (%)` inputs to the Orchestrator UI for the Gmail and Drive pipelines, providing granular routing control.
- **Layer 6:** Serialized `ai_confidence_threshold` via the `google.script.run` middleware inside `JS_Actions.html`, passing dynamic configurations securely.
- **Layer 2:** Enforced the dynamic confidence thresholds in `sync_engine.py`, programmatically evaluating LLM classifier results and correctly routing sub-threshold artifacts directly into the `quarantine_queue` to satisfy Zero Trust requirements.

## [v1.1.19] - 2026-05-16
### Changed
- **Layer 2:** Implemented `run_single_pipeline` wrapper in `sync_engine.py` to natively encapsulate explicit dependency instantiation (`creds`, `conn`, `governor`), preventing background threading crashes and database locks.
- **Layer 2:** Patched `fetch_legacy_gmail_labels` in `sync_engine.py` to properly build `creds` prior to Google Workspace resource generation.
- **Layer 3:** Refactored `run_pipeline_now` in `main.py` to invoke the newly encapsulated `run_single_pipeline` framework, restoring isolated UI pipeline triggers.

## [v1.1.18] - 2026-05-16
### Added
- **Layer 2:** Added `preview_gmail_batch(query)` in `sync_engine.py` to hit the Gmail API dynamically and compile aggregated sender counts.
- **Layer 3:** Added `POST /api/batch/preview` route in `main.py` mapping to the dynamic batch engine.
### Changed
- **Layer 7:** Overhauled `previewBatch` in `JS_Actions.html` to eliminate hardcoded dummy data and correctly call the new `previewBatchQuery` via `google.script.run` middleware, rendering live workspace statistics.

## [v1.1.17] - 2026-05-16
### Changed
- **Layer 7:** Mechanized the Orchestrator UI by successfully executing `getPrompts()` via `google.script.run`, securely populating the commercial profiler and classifier `readonly` textareas.
- **Layer 7:** Eradicated the final rogue `fetch('/api/orchestrator/config')` routing it through proper `google.script.run.saveOrchestratorConfig()` middleware, completing the full iframe CORS isolation effort.

## [v1.1.16] - 2026-05-16
### Fixed
- **System:** Hardened authentication tunnels (`auth.py`, `auth_tunnel.ps1`, `auth_tunnel.sh`) to resolve OAuth headless flow hanging by explicitly routing `8080:127.0.0.1:8080` to avoid IPv4/IPv6 loopback mismatches, splitting SSH proxy flags for proper parsing, and suppressing verbose OAuthlib logger output.

## [v1.1.15] - 2026-05-16
### Changed
- **Layer 7:** Refactored `JS_Actions.html` network logic, migrating all frontend VM data calls (`renderVQB`, `renderSankey`, `executeBatch`, `simulatePipeline`, `runPipelineNow`, `snapshotLegacyLabels`, `executeLegacyLabels`, `loadZeroTrustFlow`, and `renderLegacyLabelTable`) from raw `fetch()` to `google.script.run` RPC endpoints, properly unboxing envelope payloads and enforcing Google Apps Script iframe CORS compliance while preserving UI state logic.

## [v1.1.14] - 2026-05-16
### Changed
- **Layer 7:** Updated `getHeatmapData` and `getSankeyData` in `frontend/Code.gs` to strictly match requested middleware bridge signatures, removing default parameters to ensure explicit downstream routing. Verified all other requested API bridges exist and correctly utilize the `sendToNexusVM` HMAC signature pipeline.

## [v1.1.13] - 2026-05-16
### Fixed
- **Layer 3:** Purged duplicate legacy label routes (`legacy_labels_preview` and `legacy_labels_execute`) from the bottom of `backend/main.py` that were causing namespace collisions, preserving the primary fully-implemented ones.

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