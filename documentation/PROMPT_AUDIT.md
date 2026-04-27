# Nexus Hub for Google - Prompt Audit Log

## Phase 1: Infrastructure & CI/CD Scripts
**Date:** April 25, 2026

**Summary:** 
Initiated Phase 1 of the Nexus Hub for Google project based on Section 3 of the ARCHITECTURE.md. Established the foundational infrastructure automation and deployment lifecycle scripts for the Google Cloud VM.

**Decisions Made:**
- Created an idempotent `setup.sh` script to handle the installation of required VM dependencies: Docker, Docker Compose, Node.js, Python3, and `@google/clasp`. Added clear manual intervention instructions for handling the highly sensitive `.clasprc.json` OAuth token to maintain security and avoid version control leaks.
- Created `update.sh` to serve as the master CI/CD executor. The script adheres to trunk-based deployment principles by halting containers, pulling from the `main` branch, applying sequentially numbered Python migrations (if present), force-pushing to Apps Script via `clasp`, and cleanly restarting the background services.
- Designed scripts to be resilient using bash strict mode (`set -e`) and rich in UI feedback (`echo` statements).

**Files Altered/Created:**
- `setup.sh` (Created)
- `update.sh` (Created)
- `documentation/PROMPT_AUDIT.md` (Created)
- `documentation/INSTRUCTIONS.md` (Created)
- `README.md` (Updated)

## Phase 2: Database Initialization
**Date:** April 25, 2026

**Summary:** 
Executed Phase 2 to create the centralized SQLite index (`nexus.db`) following Section 5.2 of the ARCHITECTURE.md. Developed the initial `db_init.py` Python script to generate the required database schema with robust constraints.

**Decisions Made:**
- Exclusively utilized the built-in `sqlite3` library to maintain zero dependencies for this core layer.
- Enforced `PRAGMA journal_mode=WAL;` to allow concurrent reading/writing between background processes and the web frontend.
- Enforced `PRAGMA foreign_keys = ON;` and `ON DELETE CASCADE` to ensure strong relational integrity, preventing orphaned history records.
- Appended the `STRICT` keyword to every table definition to prevent dynamic typing mismatches.
- Implemented `CHECK(json_valid(column_name))` constraints on `custom_data`, `previous_state`, and `new_state` fields in `Workspace_Artifacts` and `Artifact_History` to guarantee structurally sound JSON.
- Used Google-style Docstrings to maintain strict codebase documentation standards.

**Files Altered/Created:**
- `db_init.py` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 3: Webhook Receiver & Cryptographic Protection
**Date:** April 25, 2026

**Summary:**
Implemented the FastAPI backend application (`main.py`) to receive updates from the Google Apps Script frontend securely. The implementation fulfills Section 6.2 and 9.2 of ARCHITECTURE.md.

**Decisions Made:**
- Used `FastAPI` and `uvicorn` as requested, creating a modular foundation for API routes.
- Created an HTTP middleware (`@app.middleware("http")`) to intercept all incoming API POST requests and validate the `X-Nexus-Signature` header.
- The middleware successfully computes the HMAC-SHA256 signature using `NEXUS_HMAC_SECRET` from the `.env` file via `python-dotenv`.
- Implemented robust Replay Protection by extracting a `timestamp` from the request JSON payload, ensuring it is within a 5-minute (300-second) window.
- Gracefully handles missing secrets, signatures, malformed payloads, and expired timestamps by responding with a clear HTTP 401 Unauthorized or 500 without crashing the server.

**Files Altered/Created:**
- `main.py` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 4: Apps Script Router & Cryptographic Client
**Date:** April 25, 2026

**Summary:**
Implemented `Code.gs` for the Google Apps Script frontend, establishing the client-side half of the cryptographic webhook bridge based on Sections 6.3 and 9.5 of ARCHITECTURE.md.

**Decisions Made:**
- Created the core `doGet(e)` function to serve the `Index.html` UI shell.
- Implemented the `configureHMAC(secretString)` setup function, ensuring the sensitive secret is stored strictly in `PropertiesService.getScriptProperties()` rather than hardcoded in the script. Emphasized the critical instruction for the user to delete the string post-execution.
- Developed `sendToNexusVM(endpoint, payload)` to act as the primary communication bridge. It pulls the HMAC secret, automatically injects the current UNIX timestamp into the JSON payload for replay protection, computes the HMAC-SHA256 signature natively using `Utilities.computeHmacSha256Signature()`, and dispatches the payload via `UrlFetchApp`.
- Added JSDoc comments enforcing the architectural constraint that `sendToNexusVM` must exclusively be invoked asynchronously from the client UI via `google.script.run`.

**Files Altered/Created:**
- `Code.gs` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 5: Google Workspace API Authentication Bridge
**Date:** April 25, 2026

**Summary:**
Developed `auth.py` to handle the Google Workspace API authentication for the backend Python VM, granting access to Gmail Modify and Drive scopes.

**Decisions Made:**
- Used `google_auth_oauthlib.flow.InstalledAppFlow` and `google.oauth2.credentials.Credentials` to manage the OAuth 2.0 flow natively.
- Implemented a check for `credentials.json` with a clear terminal warning if it's missing. Also added automatic token caching (`token.json`) and refreshing to prevent repeated login requests.
- Since the VM is headless, explicitly configured `flow.run_local_server(port=8080, open_browser=False)`. This requires the user to set up a local SSH tunnel to the VM in order to complete the web-based Google OAuth login securely from their local machine.
- Set the exact scopes required: `'https://www.googleapis.com/auth/gmail.modify'` and `'https://www.googleapis.com/auth/drive'`.

**Files Altered/Created:**
- `auth.py` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 6: Automated Health Checks & Diagnostics
**Date:** April 25, 2026

**Summary:**
Implemented the diagnostic suite based on Section 8.3 of ARCHITECTURE.md to proactively isolate points of failure across the hybrid architecture.

**Decisions Made:**
- Developed `diagnostics.py` to independently verify the SQLite database connection/lock state and Google Workspace OAuth token validity.
- Created `upload_diagnostic_log()` to automatically compile test results into a JSON file and upload it to a specific 'Nexus Diagnostics' folder in Google Drive. This enforces the architectural constraint of strictly avoiding logging these errors into the SQLite database itself.
- Updated `main.py` by turning the `/api/health` POST endpoint into a secure router that triggers `diagnostics.py`. It inherits the existing `verify_nexus_signature` HMAC middleware.
- Updated `Code.gs` with `runSystemDiagnostics()`, a client-callable function that constructs an action payload, hashes it, and transmits it securely to the VM's health endpoint.

**Files Altered/Created:**
- `diagnostics.py` (Created)
- `main.py` (Updated)
- `Code.gs` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 7: Delta Synchronization Engine
**Date:** April 25, 2026

**Summary:**
Implemented `sync_engine.py` based on Sections 4.1 and 4.3 of ARCHITECTURE.md (requested as Phase 5 execution in prompt). This module handles delta synchronization for Google Drive and Gmail to strictly avoid full polling.

**Decisions Made:**
- Utilized `google-api-python-client` for interacting with Drive and Gmail APIs.
- Specifically used `drive_service.changes().list(pageToken=...)` and `gmail_service.users().history().list(historyId=...)` to retrieve delta changes.
- Employed the `tenacity` library with `@retry` decorators using exponential backoff to robustly handle API 429 Too Many Requests errors.
- Read and update sync tokens from the SQLite `Sync_State` table using the initial `app_name` keys `drive` and `gmail`.
- Used strict Python type hinting.

**Files Altered/Created:**
- `sync_engine.py` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 8: LLM Extraction Engine
**Date:** April 25, 2026

**Summary:**
Implemented the `llm_engine.py` module based on Section 4.2 and Section 9.3 of ARCHITECTURE.md. This handles the core AI analysis pipeline, identifying correspondents, categorizing intent, and extracting custom fields.

**Decisions Made:**
- Utilized the official `google-genai` SDK to communicate with Gemini models.
- Configured the API calls with `response_mime_type="application/json"` to strictly enforce structured output.
- Wrapped the JSON decoding (`json.loads`) in a robust `try/except` block to capture and gracefully handle any hallucinated output, preventing systemic crashes.
- Implemented the "Single-Pass" pipeline for Gmail thread extraction.
- Implemented the "Two-Stage Triage" pipeline for Google Drive documents (Stage 1: Identify Correspondent, Stage 2: Enforce & Extract).
- Integrated `tenacity` for exponential backoff on all LLM API calls.
- Enforced strict database integrity: upon successful extraction, it updates `Workspace_Artifacts` and writes an immutable audit record to `Artifact_History`.

**Files Altered/Created:**
- `llm_engine.py` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 9: Material Design UI & Frontend State
**Date:** April 25, 2026

**Summary:**
Implemented the Google Apps Script Web App frontend based on Section 7 and Section 9.1 of ARCHITECTURE.md. This provides the user with a responsive dashboard to view, review, and trigger diagnostic actions.

**Decisions Made:**
- Adhered to the zero-dependency constraint, using only vanilla HTML, CSS variables, and JavaScript.
- Implemented a Split-Pane layout for the main Workspace view to allow simultaneous grid browsing and detailed metadata review.
- Created `CSS_Styles.html` for comprehensive, modern Material Design styling.
- Created `JS_State.html` to manage client-side memory, allowing instantaneous switching between artifacts and tabs without network delay.
- Created `JS_Actions.html` to handle DOM manipulation, grid rendering, timeline rendering, and interacting with `google.script.run`.
- Generated `Index.html` to serve as the master shell, utilizing `<?!= include('filename'); ?>` templating syntax.
- Modified `Code.gs` to expose the `include(filename)` function and updated `doGet(e)` to `evaluate()` the `Index` template dynamically.

**Files Altered/Created:**
- `Index.html` (Created)
- `CSS_Styles.html` (Created)
- `JS_State.html` (Created)
- `JS_Actions.html` (Created)
- `Code.gs` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `README.md` (Updated)

## Phase 11: Database Connection Factory Fix
**Date:** April 25, 2026

**Summary:**
Addressed a discrepancy noted in the architecture audit by enforcing `sqlite3.Row` for all database connections to ensure robust dictionary-style row access rather than fragile tuple indexing.

**Decisions Made:**
- Updated `db_init.py`, `sync_engine.py`, `llm_engine.py`, and `diagnostics.py` to assign `conn.row_factory = sqlite3.Row` immediately after establishing the SQLite connection.
- Refactored `SELECT` queries across `sync_engine.py`, `llm_engine.py`, and `diagnostics.py` to reference fields by string keys (e.g., `row['sync_token']`, `row['custom_data']`) instead of numeric indices (e.g., `row[0]`).
- Appended Phase 11 update to `PROMPT_AUDIT.md`.

**Files Altered/Created:**
- `db_init.py` (Updated)
- `sync_engine.py` (Updated)
- `llm_engine.py` (Updated)
- `diagnostics.py` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 12: Programmatic Color Management
**Date:** April 25, 2026

**Summary:**
Implemented the `branding_engine.py` module to handle automated cross-workspace color coding, fulfilling the requirements of Section 2.2 of ARCHITECTURE.md.

**Decisions Made:**
- Included a hardcoded list of 35 Gmail-approved `backgroundColor` and `textColor` hex pairs.
- Implemented an algorithm that converts requested hex strings into RGB format and calculates the closest allowable Gmail color pair using Euclidean distance.
- Created `sync_workspace_colors()` which successfully connects to the Gmail API (to patch the nested label `color` property) and the Google Drive API (to patch the nested folder `folderColorRgb` property) ensuring visual continuity across the workspace.
- Added localized `try/except` blocks around external API calls so that a missing folder or label doesn't crash the program execution.
- Appended Phase 12 documentation to `README.md` and `PROMPT_AUDIT.md`.

**Files Altered/Created:**
- `branding_engine.py` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)
- `README.md` (Updated)

## Phase 14: Internal 'How It Works' Documentation & Tooltips
**Date:** April 25, 2026

**Summary:**
Generated internal documentation (`HOW_IT_WORKS.md`) and UI contextual tooltips (`tooltips.json`) based on Section 7.4 of ARCHITECTURE.md to power the frontend Help Section and enhance user understanding of the complex background workflows.

**Decisions Made:**
- Authored a highly detailed `HOW_IT_WORKS.md` explaining the exact lifecycles of documents and emails.
- Detailed the Google Drive ingestion to SQLite insertion process, emphasizing the `sync_engine.py` delta fetching and `llm_engine.py` Two-Stage Triage logic.
- Detailed the Gmail to SQLite process, emphasizing the Pub/Sub / History API delta sync and the Single-Pass extraction logic.
- Embedded explicit `[MERMAID_DIAGRAM_PLACEHOLDER: Name of specific system flow]` tags to serve as placeholders for future visual diagrams.
- Generated `tooltips.json` containing user-friendly explanations for core `Config_System` parameters, UI Settings, and environment variables (e.g., HMAC secrets, API keys, sync intervals).
- Appended Phase 14 documentation to `PROMPT_AUDIT.md`.

**Files Altered/Created:**
- `documentation/HOW_IT_WORKS.md` (Created)
- `tooltips.json` (Created)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 15: Documentation Expansion
**Date:** April 25, 2026

**Summary:**
Expanded the internal 'How It Works' documentation and generated the comprehensive `tooltips.json` file as dictated by Section 7.4 of ARCHITECTURE.md.

**Decisions Made:**
- Created `tooltips.json` covering every configurable parameter from the `Config_System` table and UI Settings (e.g., `NEXUS_HMAC_SECRET`, `triage_enabled`, `auto_color_sync`) with precise technical explanations.
- Appended Section 3 (The Exception Queue & Manual UI Overrides) to `HOW_IT_WORKS.md`, detailing the cryptographic handshake flow and `Artifact_History` logging.
- Appended Section 4 (The Tuning Loop) to `HOW_IT_WORKS.md`, explaining how user overrides feed back into `Config_Prompts` for AI self-correction.
- Appended Section 5 (Programmatic Color Management) to `HOW_IT_WORKS.md`, detailing the Euclidean distance algorithm and cross-workspace synchronization.
- Included the explicit `[MERMAID_DIAGRAM_PLACEHOLDER: The UI Cryptographic Handshake]` placeholder in Section 3 as requested.

**Files Altered/Created:**
- `tooltips.json` (Updated)
- `documentation/HOW_IT_WORKS.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 16: Telemetry and Hardening
**Date:** April 25, 2026

**Summary:**
Implemented architectural hardening and telemetry updates to improve system resiliency, logging, and data integrity.

**Decisions Made:**
- Created `docker-compose.yml` to orchestrate the Python sync engine, mounting the local `/data` directory as a persistent volume to preserve `nexus.db`.
- Configured the Docker logging driver (`json-file`) with `max-size: 10m` and `max-file: 3` to prevent disk overflow from long-running background processes.
- Updated `db_init.py` by adding the `Error_Logs` STRICT table for centralized stack trace/error persistence, and appended a `locked_by_system` boolean to `Workspace_Artifacts` to mitigate race conditions during sync.
- Updated `llm_engine.py` by injecting `normalize_taxonomy()`. This function intercepts the Gemini JSON output, applies basic pluralization matching against the database whitelist, and aggressively routes the document to the 'Purpose/Review' queue if normalization fails, thereby preventing hallucinated tags from breaking the UI.
- Updated `README.md` and `PROMPT_AUDIT.md` to document the new telemetry architecture.

**Files Altered/Created:**
- `docker-compose.yml` (Created)
- `db_init.py` (Updated)
- `llm_engine.py` (Updated)
- `README.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 17: The Master Documentation Rewrite
**Date:** April 25, 2026

**Summary:**
Completely rewrote `HOW_IT_WORKS.md` from scratch to provide extreme technical depth, procedural step-by-step lifecycles, and inclusion of the UI data retrieval flow.

**Decisions Made:**
- Scrapped the previous high-level draft of `HOW_IT_WORKS.md`.
- Acted as a Senior Technical Writer to articulate the *why* and *how* for every architectural choice.
- **System Overview:** Provided a brief summary of the hybrid architecture spanning Google Apps Script, Python VM, and SQLite.
- **The Google Drive Pipeline:** Broken down into 4 procedural phases (Ingestion & OCR Strip-down, Triage & Routing Queue, Threshold Batching & Extraction, Archival & Exception Handling) with the `[MERMAID_DIAGRAM: Advanced Drive Pipeline]` placeholder.
- **The Gmail Pipeline:** Detailed the single-pass extraction, Pub/Sub vs. Polling triggers, and labeling sequence with the `[MERMAID_DIAGRAM: Gmail Pub/Sub Flow]` placeholder.
- **UI Data Retrieval & Presentation:** Authored a new section outlining the `google.script.run` trigger, the HMAC-secured GET request, SQLite dictionary row fetching, and client-side rendering via `JS_State.html`, including the `[MERMAID_DIAGRAM: UI Data Flow]` placeholder.
- **Error Routing & Dead-Letter Queue:** Fully detailed how Phase 16's `Error_Logs` table and `locked_by_system` booleans manage race conditions and API failures.
- Documented Phase 17 execution in `PROMPT_AUDIT.md`.

**Files Altered/Created:**
- `documentation/HOW_IT_WORKS.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 18: Docker Containerization Fix
**Date:** April 25, 2026

**Summary:**
Addressed a critical architectural violation by fully containerizing the Python VM environment, eliminating manual `pip install` commands from the deployment workflow.

**Decisions Made:**
- Created `requirements.txt` to strictly define all Python dependencies with their respective versions (`fastapi`, `uvicorn`, `google-api-python-client`, `google-auth-oauthlib`, `tenacity`, `python-dotenv`, `google-genai`).
- Developed a `Dockerfile` based on `python:3.11-slim`. It handles the dependency installation during the image build process and sets the default command to execute the `uvicorn` FastAPI server for `main.py`.
- Updated `docker-compose.yml` to define both the `nexus-api` service (running the default web server) and the `nexus-sync-engine` service (overriding the command to run the background sync process). Both leverage `build: .` to ensure the environment is consistent.
- Refactored `INSTRUCTIONS.md` to remove all manual pip commands, replacing them with accurate Docker Compose build and run instructions to ensure the deployment workflow strictly adheres to Section 3.4.

**Files Altered/Created:**
- `requirements.txt` (Created)
- `Dockerfile` (Created)
- `docker-compose.yml` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 19: Dynamic Prompt Architecture
**Date:** April 26, 2026

**Summary:**
Addressed the architectural flaw of hardcoded AI prompts by fully migrating them to a dynamic, database-driven architecture, enabling on-the-fly tuning via the UI.

**Decisions Made:**
- Updated `db_init.py` by introducing the `seed_default_prompts(conn)` function. It safely executes `INSERT OR IGNORE` commands to populate the `Config_Prompts` table with the master Gmail and Drive prompts on the first boot.
- Refactored `llm_engine.py` to remove all hardcoded prompt variables. Implemented the `fetch_active_prompt(prompt_key)` helper function, which queries the database for the active text string.
- Adjusted `process_gmail_thread` and `process_drive_document` to invoke `fetch_active_prompt()` immediately prior to the Gemini API call, ensuring real-time prompt injection.
- Added `GET /api/prompts` and `POST /api/prompts` endpoints to `main.py` allowing the frontend to read and update master prompts. Since the HMAC middleware automatically intercepts any `POST` request to `/api/*`, the update route is fully secured without needing to modify the core middleware.
- Authored a new 'Dynamic Prompt Architecture' sub-section in `HOW_IT_WORKS.md` detailing the transition from static files to live SQLite injection.

**Files Altered/Created:**
- `db_init.py` (Updated)
- `llm_engine.py` (Updated)
- `main.py` (Updated)
- `documentation/HOW_IT_WORKS.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 20: AI Self-Correction Engine
**Date:** April 26, 2026

**Summary:**
Implemented the AI Self-Correction engine based on Section 9.3.4 (The Tuning Loop) to dynamically generate and append new routing rules directly from user corrections.

**Decisions Made:**
- Developed the `generate_tuning_rule(artifact_id, original_json, corrected_json)` asynchronous function in `llm_engine.py`. This function retrieves the original text from SQLite, structures a diagnostic prompt, and calls the Gemini API to analyze the failure.
- Configured the new tuning rule to dynamically append to the specific Correspondent's prompt string in the `Config_Prompts` table, effectively learning from its mistakes. If a correspondent-specific prompt doesn't exist, it intelligently creates one using the base `DRIVE_STAGE_2` instructions.
- Wired the `/api/update` endpoint in `main.py` using FastAPI `BackgroundTasks`. This ensures the manual override instantly returns a 200 OK success state to the Google Apps Script frontend to maintain UI responsiveness, while the expensive LLM analysis and database tuning process occurs asynchronously in a background thread.
- Updated Section 4 of `HOW_IT_WORKS.md` with explicit details regarding the technical implementation of the `BackgroundTasks` queue.

**Files Altered/Created:**
- `llm_engine.py` (Updated)
- `main.py` (Updated)
- `documentation/HOW_IT_WORKS.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 21: Final Codebase Verification
**Date:** April 26, 2026

**Summary:**
Executed a final audit of the Python codebase to ensure late-stage architectural pivots were implemented safely and correctly.

**Decisions Made:**
- **Dynamic Prompts Verified:** Scanned `llm_engine.py` and confirmed `fetch_active_prompt()` is successfully used for both `process_gmail_thread` and `process_drive_document`. No hardcoded master prompt strings remain in the file.
- **Async Tuning Verified:** Scanned `main.py` and confirmed `BackgroundTasks` from `fastapi` is imported and leveraged effectively within the `/api/update` webhook endpoint.
- **Containerization Verified:** Scanned `update.sh` and confirmed database migration files are safely executed inside the Docker container via `docker compose run --rm nexus-api python3 "$migration"` rather than directly on the host VM.

**Files Altered/Created:**
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 22: UI Expansion & Sandbox
**Date:** April 26, 2026

**Summary:**
Expanded the UI and API capabilities based on Sections 7.5 and 7.6 of the architecture documentation, introducing bulk edit functionality and a prompt sandbox.

**Decisions Made:**
- Developed `POST /api/sandbox` in `main.py` and `run_sandbox_prompt` in `llm_engine.py` to fetch raw text and query Gemini using a temporary prompt without affecting database state.
- Developed `POST /api/bulk-update` in `main.py` to accept an array of artifact IDs and apply metadata payload updates simultaneously.
- Modified `Code.gs` to expose `runSandboxPrompt` and `bulkUpdateArtifacts` endpoints to the client.
- Redesigned `Index.html` to add 'Correspondent Review' and 'Purpose Review' tabs, an advanced cross-ecosystem filter bar, a 'Bulk Edit' action bar, and the 'Prompt Sandbox' tab.
- Updated `JS_State.html` to support multiselect `Set` states.
- Rewrote `JS_Actions.html` to add logic for filtering the grid, bulk selecting checkboxes, executing bulk edits, and running temporary AI prompts inside the Sandbox UI.

**Files Altered/Created:**
- `llm_engine.py` (Updated)
- `main.py` (Updated)
- `Code.gs` (Updated)
- `JS_State.html` (Updated)
- `Index.html` (Updated)
- `JS_Actions.html` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)

## Phase 23: Discovery & RAG
**Date:** April 26, 2026

**Summary:**
Implemented Discovery Mode to identify unknown correspondents or purposes, saving suggestions under pending_discovery custom data. Also added RAG querying capabilities allowing natural language searches over workspace artifacts.

**Decisions Made:**
- Updated master prompts in db_init.py for dynamic suggestion extraction (discovered_purpose, discovered_correspondent).
- Upgraded llm_engine.py processing pipelines to interpret discovery values and accurately route artifacts to Correspondent/Review or Purpose/Review queues.
- Created sk_rag() function in llm_engine.py to handle the LLM transformation of natural language into safe SQLite queries, fetching relevant rows, and summarizing them dynamically.
- Created POST /api/ask endpoint in main.py to serve the new query engine securely.
- Updated the Apps Script frontend (Code.gs, Index.html, JS_Actions.html) to include a fully featured AI Assistant chat tab leveraging the webhook.

**Files Altered/Created:**
- db_init.py (Updated)
- llm_engine.py (Updated)
- main.py (Updated)
- Code.gs (Updated)
- Index.html (Updated)
- JS_Actions.html (Updated)
- documentation/PROMPT_AUDIT.md (Updated)


## Phase 24: Database Schema Refactor
**Date:** April 26, 2026

**Summary:**
Implemented the Multi-Dimensional Entity Schema and Three-Tier Hierarchy to organize categories, correspondents/divisions, and purposes in the taxonomy system, with an added focus on Entity Profiles and zero-trust defaults.

**Decisions Made:**
- Refactored db_init.py to break Taxonomy_Entities into Taxonomy_Categories, Taxonomy_Correspondents, and Taxonomy_Purposes tables.
- Updated Workspace_Artifacts to point to purpose_id with cascading deletes.
- Added Entity Profile fields: sending_subdomains, physical_addresses, and rand_colors to Correspondents, as well as requency_weight and confidence_weight to Purposes.
- Implemented zero-trust is_gmail_enabled and is_drive_enabled booleans on all hierarchy tables, defaulting to 0 (FALSE).
- Updated HOW_IT_WORKS.md to document the Entity Profile columns and the default zero-trust state.

**Files Altered/Created:**
- db_init.py (Updated)
- documentation/HOW_IT_WORKS.md (Updated)
- documentation/PROMPT_AUDIT.md (Updated)

## Phase 25: Quota Governor & Ingestion
**Date:** April 26, 2026

**Summary:**
Implemented the 72-Hour Priority Lane Quota Governor and the passive JSON taxonomy seeder to safely ingest configurations while protecting API limits.

**Decisions Made:**
- Added `operation_cost` columns to `Taxonomy_Correspondents` and `Taxonomy_Purposes` in `db_init.py`.
- Refactored `sync_engine.py` to include a `QuotaGovernor` class that tracks daily Google API calls and throttles historical batch processing if it exceeds the 70% limit.
- Created an `ingest_taxonomy_seed` function in `sync_engine.py` that checks Drive for `taxonomy_seed.json`, parses it, and populates the multi-dimensional schema, enforcing zero-trust defaults (`is_gmail_enabled = 0`, `is_drive_enabled = 0`).
- Attached a background `asyncio` task to the FastAPI `main.py` `@app.on_event("startup")` hook, creating a cron-like schedule that runs the sync engine loop hourly.
- Updated `HOW_IT_WORKS.md` to document the Quota Governor tracking system and the passive Zero-Trust Seed Ingestion flow.

**Files Altered/Created:**
- `db_init.py` (Updated)
- `sync_engine.py` (Updated)
- `main.py` (Updated)
- `documentation/HOW_IT_WORKS.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)


## Phase 26: UI Hierarchy & Zero-Trust
**Date:** April 26, 2026

**Summary:**
Updated the Google Apps Script frontend to match the new database schema, introducing cascading taxonomy selectors and a Zero-Trust Review Queue.

**Decisions Made:**
- Upgraded Index.html to replace flat text inputs with cascading dropdowns (ilter-category, ilter-correspondent, ilter-purpose) in the data grid filter bar.
- Repurposed the Review tabs in Index.html into a new Zero-Trust Review Queue that displays items where is_gmail_enabled and is_drive_enabled are both false.
- Updated JS_State.html to hold 	axonomyTree and zeroTrustQueue data structures.
- Updated JS_Actions.html to populate dropdowns conditionally (onCategoryChange, onCorrespondentChange), render the Zero-Trust table with ecosystem toggles, and dynamically calculate and display a bulk edit API quota cost estimate (updateBulkEstimate).
- Updated README.md version history to reflect v1.2.0 features.

**Files Altered/Created:**
- Index.html (Updated)
- JS_State.html (Updated)
- JS_Actions.html (Updated)
- README.md (Updated)
- documentation/PROMPT_AUDIT.md (Updated)

## Phase 28: Telemetry & Alerting Matrix
**Date:** April 26, 2026

**Summary:**
Implemented the Telemetry and Alerting Matrix based on Section 8.6 of ARCHITECTURE.md to provide critical system monitoring and daily summaries.

**Decisions Made:**
- Created `notifier.py` with `NexusNotifier` class to handle both urgent webhooks via HTTP POST and daily digest emails via the Gmail API.
- Updated `sync_engine.py` exception handling to catch fatal OAuth errors and `sqlite3.OperationalError` (database locks) and broadcast them via `send_urgent_webhook()`.
- Added a `daily_digest` background task in `main.py` that queries `Error_Logs` (DLQ) and `Workspace_Artifacts` linked to zero-trust purposes, compiling an HTML report and sending it via `send_daily_digest()`.
- Updated `README.md` to highlight the Telemetry & Push Alerts feature.
- Updated `INSTRUCTIONS.md` to guide users on configuring `NEXUS_WEBHOOK_URL` via Pushover.

**Files Altered/Created:**
- `notifier.py` (Created)
- `sync_engine.py` (Updated)
- `main.py` (Updated)
- `README.md` (Updated)
- `documentation/INSTRUCTIONS.md` (Updated)
- `documentation/PROMPT_AUDIT.md` (Updated)


## Phase 27: Final V1.1 Master Audit
**Date:** April 26, 2026

**Summary:**
Conducted the V1.1 Master Project Audit acting as the Lead QA Engineer, verifying all recent architectural pivots against the master constraints and syncing documentation.

**Decisions Made:**
- Verified Three-Tier Hierarchy, 72-Hour Priority Lane, and Zero-Trust defaults are present in the codebase.
- Added Apps Script timeout protection (continuation tokens) logic to ulkUpdateArtifacts in Code.gs to handle heavy frontend routing functions.
- Updated HOW_IT_WORKS.md System Overview to explicitly reflect the 'Google Inbox' zero-inbox design philosophy.
- Confirmed INSTRUCTIONS.md details the DRIVE_SEED_FOLDER_ID configuration for 	axonomy_seed.json.
- Appended the V1.1 Phase 22-26 Pass/Fail checklist to ARCHITECTURE_AUDIT.md.

**Files Altered/Created:**
- Code.gs (Updated)
- documentation/HOW_IT_WORKS.md (Updated)
- documentation/ARCHITECTURE_AUDIT.md (Updated)
- documentation/PROMPT_AUDIT.md (Updated)


## Phase 24b: Database Documentation Polish
**Date:** April 26, 2026

**Summary:**
Added rich, functional inline SQL comments (--) directly above each table creation block in db_init.py to clarify the schema's purpose.

**Decisions Made:**
- Clarified that Workspace_Artifacts only uses purpose_id to strictly enforce the cascading Three-Tier Hierarchy (Purpose -> Correspondent -> Category).
- Documented that JSON tracking columns (sending_subdomains, physical_addresses, rand_colors) are used to enrich the deterministic knowledge graph for LLM matching and UI branding.
- Documented the operation_cost columns on Correspondents and Purposes, noting their function in tracking historical LLM execution weight for the Quota Governor's throttling logic.
- Ensured all updates were strictly cosmetic comments, leaving actual SQL table definitions and Python logic unchanged.

**Files Altered/Created:**
- db_init.py (Updated)
- documentation/PROMPT_AUDIT.md (Updated)
