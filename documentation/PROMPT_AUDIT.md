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