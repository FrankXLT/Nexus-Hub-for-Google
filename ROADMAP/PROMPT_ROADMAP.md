
# Nexus Hub: Prompt Roadmap By Epic

**Instructions for the Human Developer:** Do not paste this entire file into Gemini Code Assist at once. Treat this as a sequential playbook. 
1. Ensure the living documentation (`README.md` and `INSTRUCTIONS.md`) is open or referenced in your IDE chat context. *(Note: The legacy `ARCHITECTURE.md` and `HOW_IT_WORKS.md` files are officially deprecated. All architecture and logic are now centralized in the README).*
2. Paste the prompt to anchor the agent. 
3. Proceed prompt-by-prompt within the current Epic, only moving to the next when the current code is perfect.

## Table of Contents
* [EPIC 0: The Baseline Foundation (v0.x.x)](#epic-0-the-baseline-foundation-v0xx)
* [EPIC 1: Autonomous Profiling & Lifecycle Management (v1.x.x)](#epic-1-autonomous-profiling--lifecycle-management-v1xx)
* [EPIC 2: The Core API & Graph Migration (v2.x.x)](#epic-2-the-core-api--graph-migration-v2xx)
* [EPIC 3: The Nexus Paradigm Frontend (v3.x.x)](#epic-3-the-nexus-paradigm-frontend-v3xx)
* [EPIC 4: Infrastructure as Code (v4.x.x)](#epic-4-infrastructure-as-code-v4xx)

---

## EPIC 0: The Baseline Foundation (v0.x.x)
*Notice to AI: This Epic covers the foundational ingestion, database, and webhook architecture.*

---

<a id="epic-0-prompt-0"></a>
### Epic 0 - Prompt 0: The Context Anchor
**Goal:** Prevent the agent from generating unsolicited code while forcing it to digest the master architecture and the continuous documentation rules.

**Copy/Paste this to Gemini Code Assist:**
> "I am the Lead Architect, and you are my Junior Developer. We are building the 'Nexus Hub for Google'. Please read the `README.md` and `INSTRUCTIONS.md` file in this repository to understand the master specification. 
>
> **Continuous Documentation Rules:** Throughout this project, you are responsible for maintaining three living documents alongside the code:
> 1. `PROMPT_AUDIT.md`: After every completed stage, you will log a summary of what was built, decisions made, and files altered. This acts as our recovery memory.
> 2. `README.md`: You will continuously update this with feature summaries, version history, and high-level architecture overviews as they are built.
> 3. `INSTRUCTIONS.md`: You will iteratively write the step-by-step user manual here, including exact GCP setup instructions, API enabling, Service Account creation, and deployment steps.
> 
> **CRITICAL INSTRUCTION:** Do NOT write any code yet. Your only task right now is to reply with exactly: 'Architecture digested and documentation rules acknowledged. I understand the hybrid Apps Script/GCP structure and my responsibility to maintain the Audit, Readme, and Instructions files. Awaiting Phase 1 instructions.'"

---

<a id="epic-0-prompt-1"></a>
### Epic 0 - Prompt 1: Infrastructure & CI/CD
**Internal Simulation & Correction:** *Left to its own devices, the agent will write generic bash scripts, forget to install `clasp`, and write a destructive `update.sh` that wipes the SQLite database. The prompt below explicitly forces idempotency and safe Git pulling.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 1 based on Section 3 of README.md and INSTRUCTIONS.md. Generate two bash scripts:
> 
> 1. `setup.sh`: This must be an idempotent provisioning script for an Ubuntu VM. It must install Docker, Docker Compose, Node.js, and `@google/clasp`. Include comments explaining where the user must manually paste their `.clasprc.json` token.
> 2. `update.sh`: This is our CI/CD executor. It must gracefully stop the docker containers, run `git pull origin main`, execute any Python files found in a `/migrations` directory, run `clasp push --force`, and restart the containers.
> 
> Use bash best practices (`set -e`, echo statements for UI feedback). Do not generate any Python code yet."
> 
> **Post-Execution Documentation:**
> After you have generated the code for this stage, you MUST:
> - Append a summary of the generated files and logic to `PROMPT_AUDIT.md`.
> - Update `README.md` to reflect these new features.
> - Update `INSTRUCTIONS.md` with any required setup steps for this specific phase (e.g., if we just wrote the webhook, add the Nginx setup instructions; if we wrote the Delta Sync, add the instructions for enabling the Drive/Gmail APIs in GCP).
---

<a id="epic-0-prompt-2"></a>
### Epic 0 - Prompt 2: Centralized SQLite Index 
**Internal Simulation & Correction:** *The agent will default to using SQLAlchemy (bloat) and standard SQLite tables. It will also likely format the `custom_data` columns as TEXT instead of JSON. The prompt below forces lightweight standard libraries and strict SQLite 3.37+ constraints.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 2 based on Section 5.2 of README.md and INSTRUCTIONS.md. Write the Python initialization script (`db_init.py`) to create the `nexus.db` database.
> 
> **Strict Constraints:**
> 1. Do NOT use SQLAlchemy or external ORMs. Use the built-in Python `sqlite3` library.
> 2. Implement `PRAGMA journal_mode=WAL;` and `PRAGMA foreign_keys = ON;`.
> 3. Every single table MUST append the `STRICT` keyword (SQLite 3.37+).
> 4. For `Workspace_Artifacts` and `Artifact_History`, explicitly ensure the `custom_data`, `previous_state`, and `new_state` columns are designed to hold JSON strings.
> 5. Use Google-style Docstrings for all functions. 
> Generate the complete Python script."
> 
> **Post-Execution Documentation:**
> After you have generated the code for this stage, you MUST:
> - Append a summary of the generated files and logic to `PROMPT_AUDIT.md`.
> - Update `README.md` to reflect these new features.
> - Update `INSTRUCTIONS.md` with any required setup steps for this specific phase (e.g., if we just wrote the webhook, add the Nginx setup instructions; if we wrote the Delta Sync, add the instructions for enabling the Drive/Gmail APIs in GCP).

---

<a id="epic-0-prompt-3"></a>
### Epic 0 - Prompt 3: Python Webhook & HMAC Security Bridge
**Internal Simulation & Correction:** *The agent will frequently forget replay-attack protection, or it might hardcode secrets. It must be forced to use `python-dotenv` and explicit timestamp math.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 3 based on Section 6.2 and 9.2 of README.md and INSTRUCTIONS.md. Write the FastAPI backend application (`main.py`) that will receive requests from Apps Script.
> 
> **Strict Constraints:**
> 1. Use `FastAPI` and `uvicorn`.
> 2. Build a dependency/middleware that intercepts all incoming requests and verifies the `X-Nexus-Signature` header.
> 3. The HMAC signature must be validated using a `NEXUS_HMAC_SECRET` loaded via `python-dotenv`.
> 4. **Replay Protection:** The payload will contain a UNIX timestamp. The middleware MUST reject any request where the timestamp is older than 5 minutes from the server's current time.
> 5. Return a clean HTTP 401 Unauthorized if the signature or timestamp fails, without crashing the server.
> Write the FastAPI script."
> 
> **Post-Execution Documentation:**
> After you have generated the code for this stage, you MUST:
> - Append a summary of the generated files and logic to `PROMPT_AUDIT.md`.
> - Update `README.md` to reflect these new features.
> - Update `INSTRUCTIONS.md` with any required setup steps for this specific phase (e.g., if we just wrote the webhook, add the Nginx setup instructions; if we wrote the Delta Sync, add the instructions for enabling the Drive/Gmail APIs in GCP).

---

<a id="epic-0-prompt-4"></a>
### Epic 0 - Prompt 4: Google Apps Script Backend (The Secure Router)
**Internal Simulation & Correction:** *The agent might hardcode the HMAC secret. This prompt forces the creation of a secure setup utility.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 4 based on Section 6.3 and 9.5 of README.md and INSTRUCTIONS.md. Generate the `Code.gs` file.
> 
> **Strict Constraints:**
> 1. Write the `doGet(e)` function to serve `Index.html`.
> 2. Write a one-time setup function `configureHMAC(secretString)`. This function saves the string to `PropertiesService.getScriptProperties()`. Add a prominent comment telling the user to run this once and then delete the string from the editor.
> 3. Write `sendToNexusVM(endpoint, payload)`. It MUST pull the HMAC secret from `PropertiesService`, generate the HMAC-SHA256 signature natively, append a timestamp, and transmit via `UrlFetchApp.fetch()`.
> 4. Add a JSDoc comment explicitly warning that this function must only be called via `google.script.run` from the client-side.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md, README.md, and draft the Apps Script deployment steps in INSTRUCTIONS.md."

---

<a id="epic-0-prompt-5"></a>
### Epic 0 - Prompt 5: Python Headless OAuth Bootstrapper
**Internal Simulation & Correction:** *The agent will assume it can open a local web browser to authenticate. It must be forced to write a headless-compatible OAuth flow.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 5. We need to build the authentication bridge for the Python VM to talk to Workspace APIs. Write an `auth.py` script.
> 
> **Strict Constraints:**
> 1. Use `google_auth_oauthlib.flow.InstalledAppFlow` and `google.oauth2.credentials.Credentials`.
> 2. The script must load `credentials.json` (warn the user to place this file via `.env` or root directory).
> 3. It must check for a valid `token.json`. If missing or expired, it must initiate the auth flow.
> 4. **CRITICAL:** Because this runs on a headless VM, you must configure the flow to allow terminal/console-based URL copy-pasting, or bind to a specific port the user can tunnel to. Do not rely on automatic browser opening.
> 5. Request scopes for Gmail Modify and Drive (metadata and file access).
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md. Critically, write the exact step-by-step guide in INSTRUCTIONS.md for how the user downloads `credentials.json` from GCP and generates the `token.json` via SSH."

---

<a id="epic-0-prompt-6"></a>
### Epic 0 - Prompt 6: Isolated Health Checks & Diagnostic Logging
**Internal Simulation & Correction:** *The agent might try to log diagnostics into the main SQLite database, which defeats the purpose if the database is down. It must be forced to use Google Drive for isolated logging.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 6 based on Section 8.3 of README.md and INSTRUCTIONS.md. We need to build the diagnostic suite to isolate points of failure.
> 
> **Strict Constraints:**
> 1. In `main.py`, create a new FastAPI endpoint: `/api/health`. It must utilize the exact same HMAC signature validation middleware as the rest of the application.
> 2. Create a `diagnostics.py` module. It must contain functions to perform three distinct tests:
>    - A simple read/write verification on `nexus.db` (does it connect? is it locked?).
>    - A lightweight token check using the Google Python Client (e.g., fetch the user's Gmail profile or Drive quota) to ensure OAuth is valid.
> 3. **Isolated Logging:** Write a function that compiles the results of these tests into a formatted string (JSON or text) and uploads it directly to Google Drive as a new file in a specific "Nexus Diagnostics" folder. Do NOT log these health checks into the SQLite database.
> 4. In `Code.gs`, write a frontend test runner function `runSystemDiagnostics()` that sends the HMAC-secured ping to `/api/health` and returns the success/fail UI alert to the user.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md, README.md, and detail how to trigger this test runner in INSTRUCTIONS.md."

---

<a id="epic-0-prompt-7"></a>
### Epic 0 - Prompt 7: Delta Sync & Tenacity Backoff
**Internal Simulation & Correction:** *The agent will likely try to write a script that does a full folder scan `drive.files().list()`. It must be forced to use the `Changes.list` endpoint and the `tenacity` library for error handling.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 5 based on Section 4.1 and 4.3 of README.md and INSTRUCTIONS.md. Write a Python module (`sync_engine.py`) that fetches changes from Google Drive and Gmail.
> 
> **Strict Constraints:**
> 1. Use the `google-api-python-client`.
> 2. **NO FULL POLLING.** For Drive, use `drive_service.changes().list(pageToken=...)`. For Gmail, use `gmail_service.users().history().list(historyId=...)`.
> 3. You must import the `tenacity` library. Decorate your API call functions with `@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))` to handle 429 Too Many Requests errors.
> 4. The script must read the last known token from the `Sync_State` table, fetch the delta, and update the table with the new token. 
> 5. Use strict Python Type Hinting."
> 
> **Post-Execution Documentation:**
> After you have generated the code for this stage, you MUST:
> - Append a summary of the generated files and logic to `PROMPT_AUDIT.md`.
> - Update `README.md` to reflect these new features.
> - Update `INSTRUCTIONS.md` with any required setup steps for this specific phase (e.g., if we just wrote the webhook, add the Nginx setup instructions; if we wrote the Delta Sync, add the instructions for enabling the Drive/Gmail APIs in GCP).

<a id="epic-0-prompt-8"></a>
### Epic 0 - Prompt 8: The LLM Processing Engine
**Internal Simulation & Correction:** *The agent might try to use outdated Gemini SDKs or fail to parse the JSON outputs safely. It must be forced to use the latest `google-genai` SDK and implement structured output parsing.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 8 based on Section 4.2 and Section 9.3 of README.md and INSTRUCTIONS.md. Write the `llm_engine.py` module to handle the batch processing and Gemini API interactions.
> 
> **Strict Constraints:**
> 1. Use the official Google GenAI SDK to interact with the Gemini models.
> 2. Implement the Two-Stage Triage logic for Google Drive and the Single-Pass logic for Gmail as defined in the architecture.
> 3. Inject the exact prompts from Section 9.3. 
> 4. **CRITICAL:** You must force the LLM to return `application/json` using the `response_mime_type` configuration, and you must wrap the JSON parsing (`json.loads`) in a `try/except` block to prevent crashes if the LLM hallucinates formatting.
> 5. If Epic 0 - Prompt 2 extraction succeeds, write the database `UPDATE` to `Workspace_Artifacts` and the `INSERT` to `Artifact_History`.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md and README.md. Detail any required Gemini API key configurations in INSTRUCTIONS.md."

---

<a id="epic-0-prompt-9"></a>
### Epic 0 - Prompt 9: Frontend UI (Material Design & State)
**Internal Simulation & Correction:** *The agent might try to write a monolithic HTML file or use heavy external frameworks. It must be forced to use the separated Apps Script architecture and lightweight vanilla JS/CSS.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 9 based on Section 7 and Section 9.1 of README.md and INSTRUCTIONS.md. We are returning to the Google Apps Script environment to build the frontend.
> 
> **Strict Constraints:**
> 1. Generate `Index.html` (the Material Design shell and Split-Pane layout), `CSS_Styles.html` (styling and grid layouts), `JS_State.html` (client-side data memory), and `JS_Actions.html` (DOM manipulation and `google.script.run` calls).
> 2. Ensure `Index.html` properly includes the CSS and JS files using the `<?!= include('filename'); ?>` templating syntax required by Apps Script.
> 3. Build the dynamic data grid to render the `custom_data` JSON fields.
> 4. Build the Audit Timeline tab to render the history logs.
> 5. Keep dependencies zero. Use vanilla JavaScript and CSS variables for the theming.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md and README.md. Write the final Apps Script deployment instructions (how to publish as a Web App) in INSTRUCTIONS.md."

---

<a id="epic-0-prompt-10"></a>
### Epic 0 - Prompt 10: Final Codebase & Architecture Audit
**Internal Simulation & Correction:** *Agents often suffer from 'context drift' by Epic 0 - Prompt 9 and may have silently dropped a constraint from Epic 0 - Prompt 2. This forces a complete retrospective sweep of the local directory against the master spec.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 10: The Final QA Audit. You have completed the primary build. You must now act as the Lead QA Engineer. 
> 
> **Tasks:**
> 1. Read the `PROMPT_AUDIT.md` to see what you previously claimed to build.
> 2. Scan the actual codebase you just generated (`.py`, `.gs`, `.html`, `.sh` files).
> 3. Cross-reference the actual codebase against the strict constraints outlined in `README.md` and `INSTRUCTIONS.md`.
> 
> **Output:**
> Generate a new file named `ARCHITECTURE_AUDIT.md`. This file MUST contain the following sections:
> 
> - **1. File Manifest:** A list of every file generated and its current state.
> - **2. Security Compliance:** Verify explicitly if the HMAC-SHA256 signature is validating timestamps in `main.py`, and if `auth.py` is properly configured for a headless VM (no browser auto-open). Check if any secrets are hardcoded.
> - **3. Database Integrity Check:** Confirm that `db_init.py` includes the `STRICT` keyword on ALL tables, uses `PRAGMA journal_mode=WAL`, and enforces Foreign Keys.
> - **4. Resiliency Check:** Confirm that the Google API and Gemini API calls use the `tenacity` exponential backoff, and that JSON responses from Gemini are wrapped in safe `try/except` blocks.
> - **5. Discrepancies & Deviations:** Self-report any constraints from `README.md` and `INSTRUCTIONS.md` that were missed, skipped, or implemented differently than requested.
> 
> Do not write any new application code during this stage. Only generate the `ARCHITECTURE_AUDIT.md` file."

<a id="epic-0-prompt-11"></a>
### Epic 0 - Prompt 11: Database Utility Refactor (Audit Fix)
**Internal Simulation & Correction:** *The audit revealed the DB is returning tuples instead of dictionary-like objects. This prompt forces the implementation of `sqlite3.Row` across the connection layer.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 11. In your Architecture Audit, you noted a discrepancy regarding database connection factories. We need to fix this.
> 
> **Tasks:**
> 1. Update `db_init.py` (and any other files that establish a database connection, like `main.py`, `sync_engine.py`, or `llm_engine.py`).
> 2. Immediately after establishing `sqlite3.connect()`, you MUST set `conn.row_factory = sqlite3.Row`.
> 3. Refactor any existing `SELECT` queries in the codebase that rely on tuple indexing (e.g., `row[0]`) to use dictionary key indexing (e.g., `row['artifact_id']`).
> 
> **Post-Execution Documentation:** Append this fix to `PROMPT_AUDIT.md`."

<a id="epic-0-prompt-12"></a>
### Epic 0 - Prompt 12: Visual Branding & Color Sync Engine
**Internal Simulation & Correction:** *The agent missed Section 2.2. It must be forced to write the algorithm that limits colors to the strict Gmail API hex palette and syncs them to Google Drive.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 12 based on Section 2.2 of README.md and INSTRUCTIONS.md. We need to build the Programmatic Color Management system. Write a new Python module: `branding_engine.py`.
> 
> **Strict Constraints:**
> 1. The script must contain a hardcoded list/dictionary of the 35 specific background/text hex color pairs allowed by the Gmail API.
> 2. Write an algorithm that takes a requested brand color (e.g., from the `Taxonomy_Entities` table) and finds the closest matching allowed Gmail color pair using simple Euclidean distance in RGB color space.
> 3. Write a function `sync_workspace_colors()`. It must use the `google-api-python-client` to apply the matched color pair to the corresponding nested Label in Gmail.
> 4. It must then take that exact same hex color and apply it to the `folderColorRgb` property of the matching Google Drive nested folder.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md and README.md."

<a id="epic-0-prompt-13"></a>
### Epic 0 - Prompt 13: Feature Audit & Regression Check
**Internal Simulation & Correction:** *When refactoring database logic (Epic 0 - Prompt 11), agents frequently miss isolated tuple indexes (e.g., `row[0]`) buried inside try/except blocks. For Epic 0 - Prompt 12, they often format the Drive API `folderColorRgb` payload incorrectly. This forces a surgical scan of those specific implementations.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 13: The Feature & Regression Audit. You must act as the Lead QA Engineer to verify the fixes implemented in Stages 11 and 12.
> 
> **Tasks:**
> 1. **Scan Database Logic:** Search the entire codebase (`db_init.py`, `main.py`, `sync_engine.py`, `llm_engine.py`, `diagnostics.py`) for any remaining instances of tuple-based indexing (e.g., `row[0]`, `row[1]`). Confirm `conn.row_factory = sqlite3.Row` is applied to ALL connections.
> 2. **Scan Branding Logic:** Review `branding_engine.py`. Confirm the 35 Gmail hex pairs are explicitly defined. Confirm the Drive API payload correctly targets the `folderColorRgb` metadata field, and the Gmail API targets the `color` object for labels.
> 
> **Output:**
> Append a new section titled '## 6. V1.1 Feature Audit' to the bottom of the existing `ARCHITECTURE_AUDIT.md` file. 
> 
> In this section, report:
> - **Row Factory Compliance:** Pass/Fail (List any files that were missed).
> - **Tuple Purge:** Pass/Fail (List any lines of code that still incorrectly use integer indexing for database rows).
> - **Branding API Payload Check:** Pass/Fail (Confirm the exact JSON/Dict payload structure used for the Drive and Gmail API updates).
> 
> If you discover any remaining tuple bugs during this scan, automatically fix them in the source code before generating the audit report."

<a id="epic-0-prompt-14"></a>
### Epic 0 - Prompt 14: Internal Documentation & Tooltip Generation
**Internal Simulation & Correction:** *The agent will likely write a generic, surface-level readme. It must be forced to act as a Technical Writer, creating a granular, module-by-module breakdown, extracting a structured JSON for the UI tooltips, and leaving explicit placeholders for the Lead Architect to insert visual diagrams.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 14 based on Section 7.4 of README.md and INSTRUCTIONS.md. We need to generate the internal 'How It Works' documentation that will power the UI's Help Section and contextual tooltips. You must act as the Lead Technical Writer.
> 
> **Tasks:**
> 1. Read the finalized codebase (`sync_engine.py`, `llm_engine.py`, `main.py`, `Code.gs`, etc.).
> 2. Create a highly detailed `README.md` and `INSTRUCTIONS.md` file explaining the exact lifecycle of a document from Google Drive ingestion to SQLite insertion, and the lifecycle of an email via Pub/Sub. 
> 3. **CRITICAL:** Wherever a complex flow occurs, you must leave an explicit placeholder for the Lead Architect to add a graphic. Format it exactly like this: `[MERMAID_DIAGRAM_PLACEHOLDER: Name of specific system flow]`.
> 4. Create a new file named `tooltips.json`. Extract every configurable parameter from the `Config_System` table and the UI Settings module. Write a concise, 1-2 sentence user-friendly explanation for each parameter to be used as a UI tooltip.
> 
> **Post-Execution Documentation:** Append this phase to `PROMPT_AUDIT.md`. Do not write any Mermaid code; leave the placeholders intact."

<a id="epic-0-prompt-15"></a>
### Epic 0 - Prompt 15: Documentation Expansion & Correction
**Internal Simulation & Correction:** *The agent provided a highly summarized README.md and INSTRUCTIONS.md and entirely skipped the tooltips.json requirement. This prompt acts as a Lead Architect reprimand, forcing deep technical expansion and completion of missing tasks.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 15. I have reviewed your `README.md` and `INSTRUCTIONS.md` and you missed several critical architectural requirements from Section 7.4. 
> 
> **Tasks & Corrections:**
> 1. **You forgot `tooltips.json`.** You must extract every configurable parameter from the UI Settings and `Config_System` table and write a 1-2 sentence technical explanation for each in a new `tooltips.json` file.
> 2. **Expand `README.md` and `INSTRUCTIONS.md`.** Your current draft is too high-level. You must append three entirely new sections to the document:
>    - **Section 3: The Exception Queue & Manual UI Overrides:** Explain exactly what happens when a document is flagged as 'Purpose/Review', how the Apps Script UI fetches it, how the HMAC cryptographic handshake secures the user's manual correction, and how that correction is appended to the `Artifact_History` timeline.
>    - **Section 4: The Tuning Loop (AI Self-Correction):** Explain how a user's manual override triggers the Bulk AI Correction loop to generate a new routing rule.
>    - **Section 5: Programmatic Color Management:** Explain how the dual-snapping Euclidean algorithm ensures WCAG contrast compliance and syncs hex codes between Gmail labels and Drive folders.
> 3. Leave `[MERMAID_DIAGRAM_PLACEHOLDER: The UI Cryptographic Handshake]` under Section 3.
> 
> **Post-Execution Documentation:** Ensure these expansions reflect the depth of our actual python/GS implementation."

<a id="epic-0-prompt-16"></a>
### Epic 0 - Prompt 16: Telemetry, Normalization & Compose Hardening
**Internal Simulation & Correction:** *The agent needs to augment existing files (`db_init.py`, `llm_engine.py`) and create a new one (`docker-compose.yml`). We must ensure it doesn't accidentally wipe out the existing logic in those Python files, but strictly augments them.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 16 based on our architectural review for Telemetry and Hardening. You will be augmenting our existing codebase.
> 
> **Tasks:**
> 1. **Docker Compose:** Create a `docker-compose.yml` file. It must define the Python sync engine service, map a persistent volume for the `/data` directory (where `nexus.db` lives), load variables from `.env`, and implement a logging driver with `max-size: 10m` and `max-file: 3`.
> 2. **Database Updates:** Modify `db_init.py`. 
>    - Add a new `STRICT` table: `Error_Logs` with columns: `log_id` (PK), `timestamp`, `module_name`, `artifact_id` (FK, nullable), `error_message`, and `stack_trace` (JSON).
>    - Add a boolean column `locked_by_system` (default 0) to the `Workspace_Artifacts` table to prevent race conditions during sync.
> 3. **Taxonomy Normalization:** Update `llm_engine.py`. Before the LLM output is evaluated against the database whitelist, inject a pre-processing function to normalize common plural/misspelled tags (e.g., converting 'Receipts' -> 'Receipt'). If normalization fails and the tag still does not match the whitelist, aggressively enforce the 'Purpose/Review' exception fallback.
> 
> **Post-Execution Documentation:** Append these hardening updates to `PROMPT_AUDIT.md` and summarize the new telemetry architecture in `README.md`."

<a id="epic-0-prompt-17"></a>
### Epic 0 - Prompt 17: The Master Documentation Rewrite
**Internal Simulation & Correction:** *The agent previously generated a superficial README.md and INSTRUCTIONS.md. This prompt forces a complete rewrite, demanding extreme technical depth, procedural step-by-step lifecycles, and the inclusion of the UI data retrieval flow.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 17. Your previous draft of `README.md` and `INSTRUCTIONS.md` was too high-level and took shortcuts. You must act as a Senior Technical Writer and completely rewrite `README.md` and `INSTRUCTIONS.md` from scratch. 
> 
> **Strict Content Requirements:**
> 1. **System Overview:** Begin with a brief summary of the hybrid architecture.
> 2. **The Google Drive Pipeline (Deep Dive):** Break this down into 4 explicit procedural phases: (1) Ingestion & OCR Strip-down, (2) Triage & Routing Queue, (3) Threshold Batching & Extraction, (4) Archival & Exception Handling. Leave placeholder: `[MERMAID_DIAGRAM: Advanced Drive Pipeline]`.
> 3. **The Gmail Pipeline (Deep Dive):** Detail the single-pass extraction, Pub/Sub trigger vs. Polling fallback, and labeling sequence. Leave placeholder: `[MERMAID_DIAGRAM: Gmail Pub/Sub Flow]`.
> 4. **UI Data Retrieval & Presentation:** Create a new section detailing how the Material UI actually gets its data. Explain the `google.script.run` trigger, the HMAC secured GET request to the VM, the SQLite dictionary row fetching, and how the frontend `JS_State.html` handles the JSON payload to render the Split-Pane view without page reloads. Leave placeholder: `[MERMAID_DIAGRAM: UI Data Flow]`.
> 5. **Error Routing & Dead-Letter Queue:** Detail how Epic 0 - Prompt 16's `Error_Logs` table and `locked_by_system` booleans manage race conditions and API failures.
> 
> **Formatting:** Use bolding, numbered lists, and sub-headers. Do not summarize. Explain the *why* and *how* for every step. Do not write Mermaid code, only leave the exact placeholders requested."

<a id="epic-0-prompt-18"></a>
### Epic 0 - Prompt 18: Container Dependency & Dockerfile Fix
**Internal Simulation & Correction:** *The agent documented a manual `pip install` on the host VM, violating the containerization architecture. It must generate a Dockerfile and requirements.txt to isolate the Python environment.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 18. I reviewed your INSTRUCTIONS.md and discovered a critical architectural violation. In Phase 8, you instruct the user to manually run `pip install google-genai` on the VM. This violates our strict Docker containerization constraint (Section 3.4).
> 
> **Tasks & Corrections:**
> 1. **Create `requirements.txt`:** Generate this file including all required Python libraries with strict versions (e.g., `fastapi`, `uvicorn`, `google-api-python-client`, `google-auth-oauthlib`, `tenacity`, `python-dotenv`, `google-genai`).
> 2. **Create `Dockerfile`:** Write a Dockerfile using `python:3.11-slim`. It must copy the repository files, install the `requirements.txt` via pip, and set the entrypoint to run the FastAPI `uvicorn` server from `main.py`.
> 3. **Update `docker-compose.yml`:** Ensure the compose file is configured to `build: .` from the new Dockerfile rather than using a raw python image.
> 4. **Fix `INSTRUCTIONS.md`:** Delete the manual `pip install` instructions. Update the manual to explain that Docker Compose will automatically build the image and install the Python dependencies.
> 
> **Post-Execution Documentation:** Append this containerization fix to `PROMPT_AUDIT.md`."

<a id="epic-0-prompt-19"></a>
### Epic 0 - Prompt 19: Dynamic Prompt Extraction & Seeding
**Internal Simulation & Correction:** *The AI likely hardcoded the master prompts directly into `llm_engine.py` during Phase 8. This violates the goal of allowing users to update prompts via the UI. We must refactor the engine to fetch prompts dynamically from the `Config_Prompts` table and ensure this architectural shift is documented.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 19. We have an architectural flaw regarding how AI prompts are stored. Currently, the prompts from Section 9.3 are likely hardcoded in `llm_engine.py`. They must be fully database-driven so the user can update them later.
> 
> **Tasks:**
> 1. **Update `db_init.py` (Seeding):** Write a new function `seed_default_prompts(conn)`. This function must safely `INSERT OR IGNORE` the master prompts (from Section 9.3: Gmail Single-Pass, Drive Epic 0 - Prompt 1, Drive Epic 0 - Prompt 2) into the `Config_Prompts` table so the database is pre-loaded on the first boot.
> 2. **Refactor `llm_engine.py`:** Delete the hardcoded prompt strings. Write a helper function `fetch_active_prompt(prompt_key)` that queries the `Config_Prompts` table. 
> 3. **Dynamic Injection:** Ensure the routing and extraction functions in `llm_engine.py` call `fetch_active_prompt()` to retrieve their instructions *immediately before* making the call to the Gemini API.
> 4. **Update `main.py`:** Ensure the FastAPI server has a `GET /api/prompts` and `POST /api/prompts` endpoint (secured with the HMAC signature) so the Apps Script frontend can read and update these prompts in the database later.
> 5. **Update `README.md` and `INSTRUCTIONS.md`:** Add a new sub-section under the LLM Engine explaining this dynamic prompt architecture. Explain how prompts are fetched from the database in real-time, allowing users to modify AI behavior without requiring a Docker container restart.
> 
> **Post-Execution Documentation:** Append this refactor to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-20"></a>
### Epic 0 - Prompt 20: The AI Self-Tuning Engine (Feedback Loop)
**Internal Simulation & Correction:** *The system currently accepts manual UI corrections but does not use them to tune the LLM. We must build an asynchronous tuning loop that analyzes the error and updates the `Config_Prompts` table without blocking the UI's HTTP response, and document this technical mechanism.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 20 based on Section 9.3.4 (The Tuning Loop) of README.md and INSTRUCTIONS.md. We need to implement the AI Self-Correction engine.
> 
> **Tasks:**
> 1. **Create the Tuning Logic:** In `llm_engine.py`, write a new asynchronous function `generate_tuning_rule(artifact_id, original_json, corrected_json)`. 
>    - This function must fetch the `raw_text` for the artifact from the database.
>    - It must send the raw text, the AI's original mistake, and the user's correction to the Gemini model using the precise prompt structure defined in Section 9.3.4.
>    - It must extract the generated `new_routing_rule` from Gemini's JSON response and append it to the existing prompt string in the `Config_Prompts` table for that specific Correspondent.
> 2. **Wire the Webhook:** Modify the `POST /api/update` endpoint in `main.py`. When a user submits a manual override, the API must return the `200 OK` response to the frontend immediately, but use FastAPI's `BackgroundTasks` to execute `generate_tuning_rule()` asynchronously in the background.
> 3. **Update `README.md` and `INSTRUCTIONS.md`:** Review Section 4 (The Tuning Loop). Add a paragraph explicitly detailing the technical implementation: explain how FastAPI `BackgroundTasks` are used to process the Gemini AI tuning request asynchronously, ensuring the manual override webhook returns a 200 OK immediately to keep the UI snappy.
> 
> **Post-Execution Documentation:** Append this self-learning engine implementation to `PROMPT_AUDIT.md`."

<a id="epic-0-prompt-21"></a>
### Epic 0 - Prompt 21: The Master Project Audit & Documentation Alignment
**Internal Simulation & Correction:** *By this stage, the agent has generated thousands of lines of code and documentation. It may have orphaned features or out-of-sync documents. This prompt forces a holistic reconciliation, demanding that it verify the implementation of the hardest features (dynamic prompts, tuning loop, containerization) and ensure the user manuals reflect the absolute final state.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 21: The Master Project Audit. You must now act as the Lead QA Engineer and Lead Technical Writer. We are preparing for the V1.x production release.
> 
> **Tasks:**
> 1. **Cross-Reference Roadmap vs. Audit:** Read `PROMPT_AUDIT.md`. Verify that Stages 1 through 20 have been executed. Specifically, confirm that the features from our late-stage pivots (Epic 0 - Prompt 18 Containerization, Epic 0 - Prompt 19 Dynamic Prompts, Epic 0 - Prompt 20 Async Tuning Loop) are actually present in the `.py` files, not just in your memory.
> 2. **Codebase vs. Architecture Check:** Scan the codebase to ensure no strict constraints were violated:
>    - Are there any hardcoded Gemini prompts left in `llm_engine.py`? (They should be fetched from the DB).
>    - Does `update.sh` correctly execute database migrations and restart Docker?
>    - Are `fastapi` and `BackgroundTasks` properly handling the async tuning loop in `main.py`?
> 3. **Documentation Alignment:** Review `README.md`, `INSTRUCTIONS.md`, and `README.md` and `INSTRUCTIONS.md`. 
>    - Ensure `INSTRUCTIONS.md` clearly explains how Docker Compose handles the Python dependencies (no manual `pip install`).
>    - Ensure the `README.md` features list includes the Dead-Letter Queue, Dynamic Prompts, and the Self-Tuning Engine.
> 
> **Output:**
> 1. If you find any broken code or missing documentation constraints during this scan, silently fix them in the respective files.
> 2. Generate a final section at the bottom of `ARCHITECTURE_AUDIT.md` titled '## 7. V1.0 Master Release Audit'.
> 3. In this section, provide a Pass/Fail checklist for the 20 Stages, confirm the documentation is fully synced, and declare the codebase Ready for Production."

<a id="epic-0-prompt-21"></a>
### Epic 0 - Prompt 21: The Final Codebase Verification
**Internal Simulation & Correction:** *By this stage, the AI has generated extensive code, but the Lead Architect has manually taken over the documentation. This prompt restricts the agent strictly to a codebase audit to ensure the late-stage features (dynamic prompts, async webhook, and containerized migrations) actually exist in the `.py` and `.sh` files without risking further documentation corruption.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute a revised Epic 0 - Prompt 21: The Final Codebase Verification. The Lead Architect has already manually polished the documentation suite. Your only job is to audit the Python codebase to ensure our latest features were implemented safely and correctly.
> 
> **Tasks:**
> 1. **Verify Dynamic Prompts:** Scan `llm_engine.py`. Confirm that `fetch_active_prompt()` is being actively used to query the `Config_Prompts` table. If there are any massive, hardcoded prompt strings still lingering in the file, delete them and replace them with the dynamic fetch call.
> 2. **Verify Async Tuning:** Scan `main.py`. Confirm that `BackgroundTasks` from `fastapi` is imported and utilized in the `/api/update` webhook endpoint to trigger the `generate_tuning_rule` function asynchronously. 
> 3. **Verify Containerization:** Scan `update.sh`. Ensure that any database migrations are executed *inside* the docker container (e.g., `docker compose run --rm nexus-api python3 db_init.py`) rather than directly on the host VM.
> 
> **Output:**
> 1. If you find any missing logic, silently patch the respective `.py` or `.sh` files now.
> 2. Append 'Epic 0 - Prompt 21: Final Codebase Verification' to `PROMPT_AUDIT.md`, logging that you verified the dynamic prompts, async webhook, and dockerized execution. Do not alter any other markdown files."

<a id="epic-0-prompt-22"></a>
### Epic 0 - Prompt 22: UI Expansion, Bulk Edits, and Prompt Sandbox
**Internal Simulation & Correction:** *The current UI lacks bulk editing, distinct exception queues, and a safe testing environment. We must expand the Apps Script frontend and FastAPI backend to support these missing enterprise features.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 22 based on the newly added Sections 7.5 and 7.6 of README.md and INSTRUCTIONS.md. We are expanding the UI and API.
> 
> **Tasks:**
> 1. **Sandbox API (`main.py` & `llm_engine.py`):** Create a new endpoint `POST /api/sandbox`. It accepts an `artifact_id` and a temporary `prompt_string`. It must fetch the raw text, run it through Gemini using the temporary prompt, and return the result WITHOUT updating the `Workspace_Artifacts` or `Artifact_History` tables.
> 2. **Bulk Edit API (`main.py`):** Create `POST /api/bulk-update` accepting a list of `artifact_ids` and a metadata payload to update multiple records simultaneously.
> 3. **UI Expansion (`Index.html`, `JS_Actions.html`):**
>    - Implement distinct tabs for 'Correspondent Review' and 'Purpose Review'.
>    - Add checkbox selection to the data grid and a 'Bulk Edit' action bar.
>    - Build the 'Prompt Sandbox' tab allowing the user to select an artifact, edit the prompt, and see the dry-run JSON output.
>    - Implement an advanced filter bar allowing cross-ecosystem search (filtering by App, Category, and Custom Field JSON keys).
> 
> **Output:** Silently update the `.py`, `.html`, and `.gs` files. Append 'Epic 0 - Prompt 22: UI Expansion & Sandbox' to `PROMPT_AUDIT.md`."

<a id="epic-0-prompt-23"></a>
### Epic 0 - Prompt 23: Discovery Mode & RAG Knowledge Retrieval
**Internal Simulation & Correction:** *The current AI strictly uses whitelists. We must add a 'Discovery' fallback to suggest new correspondents, and implement a natural language chat interface to query the extracted SQLite metadata.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 23 based on the user requirement for RAG querying and Taxonomy Discovery.
> 
> **Tasks:**
> 1. **Discovery Mode (`llm_engine.py`):** Update the Epic 0 - Prompt 1 and Epic 0 - Prompt 2 extraction prompts. If the LLM cannot match a whitelist, instruct it to suggest a `discovered_correspondent` or `discovered_purpose`. 
> 2. **Pending DB State (`db_init.py` & `llm_engine.py`):** Ensure these suggestions are saved to the `Workspace_Artifacts` custom data under a `pending_discovery` key, and route the status to `Correspondent/Review` or `Purpose/Review` so the user can approve them in the UI.
> 3. **RAG Backend (`main.py` & `llm_engine.py`):** Create `POST /api/ask`. It accepts a natural language string. The backend must:
>    - Use Gemini to convert the user's question into a safe SQLite query targeting the `Workspace_Artifacts` metadata (or perform a direct semantic search if integrated).
>    - Fetch the relevant rows.
>    - Pass the rows and the user's question back to Gemini to generate a human-readable summary.
> 4. **RAG Frontend (`Index.html`):** Add an 'AI Assistant' chat window that connects to the `runAskAI` function in `Code.gs`.
> 
> **Output:** Silently update the codebase. Append 'Epic 0 - Prompt 23: Discovery & RAG' to `PROMPT_AUDIT.md`."

<a id="epic-0-prompt-24"></a>
### Epic 0 - Prompt 24: Database Refactor & Three-Tier Taxonomy
**Internal Simulation & Correction:** *We are transitioning to a multi-dimensional, three-tier entity schema with frequency tracking and zero-trust ecosystem toggles. The database must be completely refactored to support this.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 24 based on the new constraints in `README.md` and `INSTRUCTIONS.md`. We are implementing the Multi-Dimensional Entity Schema and Three-Tier Hierarchy.
> 
> **Tasks:**
> 1. **Refactor `db_init.py`:** Restructure the taxonomy tables to enforce a `Category -> Correspondent/Division -> Purpose` hierarchy. 
> 2. **Implement Entity Profiles:** Add columns to store sending subdomains, physical addresses, brand color arrays, and frequency/confidence weights.
> 3. **Implement Toggles:** Add `is_gmail_enabled` and `is_drive_enabled` booleans. Ensure the default state for any new insertion is `FALSE` (Zero-Trust).
> 
> **Output:** > 1. Silently update `db_init.py`. 
> 2. Update `README.md` and `INSTRUCTIONS.md` to explain the new three-tier schema and zero-trust defaults. 
> 3. Append 'Epic 0 - Prompt 24: Database Schema Refactor' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-25"></a>
### Epic 0 - Prompt 25: Quota Governor & Drive Seed Ingestion
**Internal Simulation & Correction:** *The backend requires protection from API quota exhaustion and the ability to passively ingest the `taxonomy_seed.json` file from Drive.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 25. We need to implement the Quota Governor and the passive JSON seeder.
> 
> **Tasks:**
> 1. **The Governor (`sync_engine.py`):** Implement the 72-Hour Priority Lane. Track daily Google API calls. Throttle historical batch processing if it exceeds 70% of the daily estimated quota. Ensure the database tracks the operation cost per entity.
> 2. **Seed Ingestion (`main.py` & `sync_engine.py`):** Write a background cron function that checks Google Drive for `taxonomy_seed.json`. If found, parse it, update the SQLite entity profiles/frequency weights, and ensure all imported nodes default to `is_gmail_enabled = FALSE` and `is_drive_enabled = FALSE`.
> 
> **Output:** > 1. Silently update the Python files. 
> 2. Update `README.md` and `INSTRUCTIONS.md` to detail the Quota Governor logic. 
> 3. Append 'Epic 0 - Prompt 25: Quota Governor & Ingestion' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-26"></a>
### Epic 0 - Prompt 26: UI Hierarchy & Blacklist Toggles
**Internal Simulation & Correction:** *The frontend must be upgraded to support cascading dropdowns for the three-tier hierarchy and ecosystem toggles for the Zero-Trust blacklist.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 26. We are updating the Google Apps Script frontend to match the new database schema.
> 
> **Tasks:**
> 1. **Cascading Hierarchy (`JS_Actions.html` & `Index.html`):** Replace flat correspondent dropdowns with cascading selectors (Category -> Correspondent -> Purpose). 
> 2. **Review Queues & Toggles:** Build the UI logic to display items where both ecosystem booleans are `FALSE` (The Zero-Trust Review Queue). Add checkboxes allowing the user to enable/disable specific labels for Gmail or Drive.
> 3. **Bulk Estimates:** When a user selects items for a bulk edit, display a warning estimating the API quota cost based on the database's tracked operation metrics.
> 
> **Output:**
> 1. Silently update the HTML/JS files.
> 2. Update the `README.md` features list to include the Three-Tier Hierarchy and Zero-Trust UI.
> 3. Append 'Epic 0 - Prompt 26: UI Hierarchy & Zero-Trust' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-27"></a>
### Epic 0 - Prompt 27: Telemetry & Alerting Matrix
**Internal Simulation & Correction:** *The background synchronization engine needs a way to alert the user of critical failures or items requiring human review without forcing them to constantly check the UI. We must build a tiered notification engine.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 27 based on Section 8.6 of README.md and INSTRUCTIONS.md. We are building the Telemetry & Alerting Matrix.
> 
> **Tasks:**
> 1. **The Notifier Module (`notifier.py`):** Create a new file with a class `NexusNotifier`. It must support two methods: `send_urgent_webhook(payload)` (which POSTs to a URL found in `os.environ.get('NEXUS_WEBHOOK_URL')`) and `send_daily_digest(email_body)` (which uses the existing Google API service to send an email to the authenticated user).
> 2. **Wire the DLQ (`sync_engine.py`):** Update the exception handling. If a fatal OAuth error or database lock occurs, trigger `send_urgent_webhook()`. 
> 3. **The Daily Digest Cron (`main.py`):** Create a background scheduler job that runs once a day. It must query the database for all items currently in the 'Error_Logs' (DLQ) and all items in the 'Workspace_Artifacts' where `is_gmail_enabled` and `is_drive_enabled` are both FALSE (the Zero-Trust Quarantine). It formats these into an HTML email and sends it via `send_daily_digest()`.
> 
> **Output:**
> 1. Silently update the codebase and create `notifier.py`.
> 2. Update `README.md` to include the Alerting Matrix feature.
> 3. Update `INSTRUCTIONS.md` to explain how to add the `NEXUS_WEBHOOK_URL` to the `.env` file.
> 4. Append 'Epic 0 - Prompt 28: Telemetry & Alerting Matrix' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-28"></a>
### Epic 0 - Prompt 28: The V1.1 Master Project Audit & Doc Alignment
**Internal Simulation & Correction:** *This is the final QA sweep. The agent must verify its own codebase against the architectural constraints and guarantee all user-facing documentation is perfectly aligned.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 28: The V1.1 Master Project Audit. You are acting as the Lead QA Engineer. 
> 
> **Tasks:**
> 1. **Codebase Verification:** Scan the `.py`, `.sh`, and `.gs` files. Ensure the Three-Tier Hierarchy, 72-Hour Priority Lane, and Zero-Trust defaults are physically present in the code. Ensure the Apps Script timeout protection (continuation tokens) is implemented in any heavy frontend routing functions.
> 2. **Documentation Sweep:** Review `README.md`, `INSTRUCTIONS.md`, and `README.md` and `INSTRUCTIONS.md`. 
>    - Ensure `INSTRUCTIONS.md` clearly explains how to configure the Google Drive Folder ID for the `taxonomy_seed.json` file.
>    - Ensure `README.md` and `INSTRUCTIONS.md` accurately reflects the 'Google Inbox' design philosophy and Quota Management.
> 
> **Output:**
> 1. Silently fix any code or documentation inconsistencies you find.
> 2. Generate a Pass/Fail checklist at the bottom of `ARCHITECTURE_AUDIT.md` for Stages 22 through 26.
> 3. Append 'Epic 0 - Prompt 27: Final V1.1 Master Audit' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-24b"></a>
### Epic 0 - Prompt 24b: Database Schema Documentation Polish
**Internal Simulation & Correction:** *The `db_init.py` file has excellent relational structure but lacks inline documentation explaining the 'why' behind the schema design for future maintainers.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 24b. The structure of `db_init.py` is perfect, but the documentation is lacking. 
> 
> **Tasks:**
> 1. Add rich, functional inline SQL comments (`--`) directly above each table creation block in `db_init.py`. 
> 2. Explain *why* `Workspace_Artifacts` only uses `purpose_id` as a foreign key (cascading hierarchy).
> 3. Explain the function of the JSON tracking columns (`sending_subdomains`, `physical_addresses`, `brand_colors`) and the `operation_cost` columns for the Quota Governor.
> 4. Do not alter any of the actual SQL table definitions or Python logic. Only inject comments.
> 
> **Output:** Silently update `db_init.py`. Append 'Epic 0 - Prompt 24b: Database Documentation Polish' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-24c"></a>
### Epic 0 - Prompt 24c: LLM Multi-Dimensional Context Injection
**Internal Simulation & Correction:** *We successfully built the database architecture to store multi-dimensional profiles (subdomains, addresses, weights), but the AI prompts were never updated to ingest this data. We need to modify the master prompts and the Python string-injection logic so the LLM can use these profiles for deterministic routing.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 24c. We have a critical gap in our extraction pipeline. In Phase 24, we added `sending_subdomains`, `physical_addresses`, and `frequency_weights` to the `Taxonomy_Correspondents` table, but we never updated our AI prompts to actually use this data.
> 
> **Tasks:**
> 1. **Update Prompts (`db_init.py`):** Modify `PROMPT_GMAIL` and `PROMPT_DRIVE_STAGE_1`. Instead of just providing a flat `[WHITELIST]` of names, change the placeholder to `[ENTITY_PROFILES]`. Instruct the AI to cross-reference the document's sender email, sending domain, or physical address against the provided entity profiles to increase routing accuracy.
> 2. **Update Injection Logic (`llm_engine.py`):** Modify the `process_gmail_thread` and `process_drive_document` functions. When querying the database for the taxonomy whitelist, also pull the `sending_subdomains` and `physical_addresses` JSON columns. Format these into a dictionary (e.g., `{'Google Cloud': {'subdomains': ['cloud-noreply@google.com']}}`) and inject this into the `[ENTITY_PROFILES]` placeholder before calling the Gemini API.
> 
> **Output:** > 1. Silently update `db_init.py` and `llm_engine.py`.
> 2. Append 'Epic 0 - Prompt 24c: LLM Multi-Dimensional Context Injection' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-29"></a>
### Epic 0 - Prompt 29: Google Contacts API Integration (Entity Bootstrapping)
**Internal Simulation & Correction:** *The user realized that Google Contacts contains a wealth of pre-verified entity data (names, emails, physical addresses). We need to leverage the Google People API to automatically ingest these contacts into our multi-dimensional `Taxonomy_Correspondents` table to bootstrap the system.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 29. We had a breakthrough idea: we should use the user's existing Google Contacts to automatically populate our entity profiles. 
> 
> **Tasks:**
> 1. **Add the Google People API:** Update `auth.py` to include the scope `https://www.googleapis.com/auth/contacts.readonly`. (Note: The user will manually enable the People API in GCP and re-auth).
> 2. **Build Contact Ingestion:** In `sync_engine.py`, create a new function called `sync_contacts(creds, conn, governor)`. 
>    - Use the `people().connections().list` endpoint to fetch the user's contacts.
>    - Map the contact's Name to a Correspondent.
>    - Map the contact's email addresses into the `sending_subdomains` JSON array.
>    - Map the contact's physical addresses into the `physical_addresses` JSON array.
>    - Assign them to a Default Category called 'Personal Network' (create this category if it doesn't exist).
> 3. **Zero-Trust Enforcement:** Insert these contacts into `Taxonomy_Correspondents` with `is_gmail_enabled=0` and `is_drive_enabled=0` so they don't flood the active taxonomy until the user approves them in the UI.
> 4. **Update Main Loop:** Call `sync_contacts()` inside the main `run_sync()` loop in `sync_engine.py` (run it just before `sync_drive`).
> 
> **Output:** > 1. Silently update `auth.py` and `sync_engine.py`. 
> 2. Append 'Epic 0 - Prompt 29: Google Contacts Integration' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-30"></a>
### Epic 0 - Prompt 30: Codebase Inline Documentation Polish
**Internal Simulation & Correction:** *The backend Python engines (`sync_engine.py` and `llm_engine.py`) execute flawless logic, but they are missing the comprehensive Google-style docstrings and inline architectural comments mandated by Section 9.4 of the architecture. If a future developer modifies the Quota Governor or Two-Stage Triage without understanding the 'why', they could break the system. We need to enforce strict code-level documentation without altering any functional logic.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 30. Your code logic is excellent, but it currently fails the documentation standards outlined in Section 9.4 of `README.md` and `INSTRUCTIONS.md`. We need to polish the inline documentation for `sync_engine.py` and `llm_engine.py`.
> 
> **Tasks:**
> 1. **Google-Style Docstrings:** Add comprehensive Google-style docstrings to every class and method. (e.g., The `QuotaGovernor` class and its methods currently have zero documentation. `process_gmail_thread` is too sparse).
> 2. **Architectural Inline Comments:** Add inline comments (`#`) that explain the *intent* and *why* behind complex logic blocks. 
>    - In `sync_engine.py`, explain *why* we force `is_gmail_enabled = 0` during seed and contact ingestion (Zero-Trust Quarantine).
>    - In `sync_engine.py`, explain the math/logic behind the 72-Hour Priority Lane in the Governor.
>    - In `llm_engine.py`, explain *why* we use a Two-Stage Triage for Drive vs. a Single-Pass for Gmail.
> 3. **Strict Constraint:** You are strictly forbidden from altering any functional code, logic, or SQL queries. Your ONLY task is to inject docstrings and comments.
> 
> **Output:** > 1. Silently update `sync_engine.py` and `llm_engine.py`. 
> 2. Append 'Epic 0 - Prompt 30: Codebase Inline Documentation Polish' to `PROMPT_AUDIT.md`."

---

<a id="epic-0-prompt-31"></a>
### Epic 0 - Prompt 31: Docker Hardening (Multi-Stage & Healthchecks)
**Internal Simulation & Correction:** *The current Docker setup lacks health monitoring and leaves potentially dangerous build dependencies inside the final image. We need to implement a Multi-Stage build to reduce the attack surface (per Architecture Section 10.4) and inject Docker Compose healthchecks to catch silent database locks or hung web servers.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 31. We need to harden our Docker infrastructure to enterprise standards.
> 
> **Tasks:**
> 1. **Rewrite `Dockerfile` (Multi-Stage):** >    - Create a `builder` stage that installs `build-essential` and compiles our `requirements.txt` into wheels (`pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt`).
>    - Create the final `runner` stage using `python:3.11-slim`. Copy the compiled wheels from the builder and install them. Do NOT include any build tools in this final stage.
> 2. **Update `docker-compose.yml` (Healthchecks):**
>    - Add a `healthcheck` block to `nexus-api`. It should use `curl -f http://localhost:8000/api/health` (ensure curl is installed in the runner Dockerfile).
>    - Add a `healthcheck` block to `nexus-sync-engine`. It should run a lightweight Python command to verify database access: `python3 -c "import sqlite3; sqlite3.connect('nexus.db').cursor().execute('SELECT 1')"`
> 3. **Update `main.py`:** Add a simple `GET /api/health` endpoint that returns `{"status": "healthy"}` so the API healthcheck has a target to ping.
> 
> **Output:** > 1. Silently update `Dockerfile`, `docker-compose.yml`, and `main.py`.
> 2. Append 'Epic 0 - Prompt 31: Docker Hardening & Healthchecks' to `PROMPT_AUDIT.md`."

<a id="epic-0-prompt-32"></a>
### Epic 0 - Prompt 32: The Diagnostic Watchdog & Health Notifications
**Internal Simulation & Correction:** *Docker healthchecks lack native push notifications. We need to bridge our infrastructure layer to our telemetry layer by wiring `diagnostics.py` into `notifier.py` and automating its execution via a VM cron job.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Epic 0 - Prompt 32. We need to bridge our Docker healthchecks into our common logging and notification infrastructure.
> 
> **Tasks:**
> 1. **Update `diagnostics.py` (The Bridge):**
>    - Import `NexusNotifier` from `notifier.py`.
>    - Add a new function: `check_api_health()`. Have it make a simple HTTP GET request to `http://nexus-api:8000/api/health`. 
>    - Modify `run_all_diagnostics()`: If `check_database()`, `check_oauth_token()`, or `check_api_health()` return an error status, immediately trigger `notifier.send_urgent_webhook()` with the failure details.
> 2. **Update `setup.sh` (The Automation):**
>    - Add a block to the bash script that automatically installs a crontab entry on the host Ubuntu VM.
>    - The cron job should execute every 15 minutes: `*/15 * * * * cd /path/to/repo && docker compose run --rm nexus-sync-engine python3 diagnostics.py` (ensure you dynamically grab the current directory variable in the bash script).
> 
> **Output:** > 1. Silently update `diagnostics.py` and `setup.sh`.
> 2. Append 'Epic 0 - Prompt 32: Diagnostic Watchdog & Health Notifications' to `PROMPT_AUDIT.md`."

<a id="epic-0-prompt-33"></a>
### Epic 0 - Prompt 33: AI-Assisted Development CONOPS & Governance

<a id="epic-0-prompt-34"></a>
### Epic 0 - Prompt 34: Pre-AI Gmail Filtering
**Internal Simulation & Correction:** *The sync engine currently pulls all emails, which wastes expensive LLM quota on spam, drafts, and promotions. We need to implement hard-coded pre-AI filtering using native Gmail `labelIds` to drop this junk before it ever reaches the Two-Stage Triage.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`sync_engine.py`)**
> We need to prevent the Gmail sync engine from wasting LLM quota on useless emails. 
> * At the top of `sync_engine.py`, add a new hard-coded set: `IGNORED_GMAIL_LABELS = {'SPAM', 'TRASH', 'DRAFT', 'CATEGORY_PROMOTIONS', 'CATEGORY_SOCIAL', 'CATEGORY_FORUMS'}`
> * Inside the `sync_gmail()` function, locate the loop where individual message details are fetched (`service.users().messages().get(...)`). 
> * Extract the `labelIds` from the message payload. Add an intersection check: If the message's labels intersect with `IGNORED_GMAIL_LABELS`, explicitly skip the message (using `continue`). Do NOT pass it to `process_gmail_thread`.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 5. The Synchronization Engine (under the 'The Gmail Pipeline' subsection).
> * **Action:** Append a new paragraph explaining 'Pre-AI Filtering & Label Exclusion'.
> * **Content:** Explain that before any email is passed to the AI pipeline, `[sync_engine.py](./sync_engine.py)` natively inspects the Gmail `labelIds`. Messages flagged as Spam, Trash, Drafts, Promotions, Social, or Forums are hard-dropped to protect the Quota Governor.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.1.0:** [Epic 0 - Prompt 34](./PROMPT_ROADMAP.md#epic-0-prompt-34) - Implemented hard-coded Pre-AI filtering in the Gmail Sync Engine to drop junk mail before LLM processing.`
> 
> **Output Actions:**
> 1. Silently update `sync_engine.py`.
> 2. Silently update `README.md` exactly as instructed above."

<a id="epic-0-prompt-35"></a>
### Epic 0 - Prompt 35: Drive Topology & Folder Nomenclature
**Internal Simulation & Correction:** *We never officially documented how Nexus Hub tracks Drive files (via SQLite, not complex folders). We need to codify this "Anti-Folder" philosophy and establish the official names for the two operational folders: 'Nexus Dropbox' and 'Nexus Diagnostic Logs'.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Define Folder Nomenclature (Documentation Only)**
> We are officially defining the Google Drive operational topology in the documentation.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Insert a new subsection directly under '4. Database Schema' named `### 4.1 The Anti-Folder Philosophy & Drive Topology`. 
> * **Action:** Insert the following explanations.
> * **Content:** >   - **The Anti-Folder Philosophy:** Explain that Nexus Hub avoids complex, nested folders to prevent 'directory sprawl.' SQLite tracks immutable File IDs, meaning files can live anywhere in the user's Drive.
>   - **Operational Topology:** Note that the system only uses two folders: `Nexus Dropbox` (for ingestion/seed files) and `Nexus Diagnostic Logs` (where `[diagnostics.py](./diagnostics.py)` uploads health reports).
> * **Constraint - Tables:** Update the **Table of Contents** at the top of the file to include `4.1 The Anti-Folder Philosophy & Drive Topology` with a working HTML anchor.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.2.0:** [Epic 0 - Prompt 35](./PROMPT_ROADMAP.md#epic-0-prompt-35) - Defined the Anti-Folder philosophy and established standard nomenclature for the two operational Drive folders.`
> 
> **Output Actions:**
> 1. Silently update `README.md` exactly as instructed above."

<a id="epic-0-prompt-36"></a>
### Epic 0 - Prompt 36: UI Pipeline Orchestrator (Backend Bridge)
**Internal Simulation & Correction:** *Hard-coded variables prevent the user from adjusting pipeline settings on the fly. We need to build FastAPI endpoints and SQLite configurations to act as a bridge between the frontend UI and the Python worker.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (The Backend Bridge)**
> We are shifting the UI into a dynamic 'Pipeline Orchestrator.' 
> 1. **Update `db_init.py`:** Inject three new default JSON key-value pairs into `Config_System`:
>    - `ui_gmail_filters`: `["CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"]`
>    - `ui_ai_config`: `{"drive_model": "gemini-1.5-pro", "gmail_model": "gemini-1.5-flash"}`
>    - `ui_post_processing`: `{"auto_archive_gmail": false, "quarantine_unconfident": true}`
> 2. **Update `main.py`:** Create two endpoints (`GET /api/settings/pipeline` and `POST /api/settings/pipeline`) to read/write these specific keys in `Config_System`.
> 3. **Update `sync_engine.py`:** Remove the hard-coded `IGNORED_GMAIL_LABELS`. Inside `sync_gmail()`, dynamically query `Config_System` for `ui_gmail_filters`. **Safety Fallback:** Always append `'SPAM', 'TRASH', 'DRAFT'` to the user's list before evaluating the intersection.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 3. The Frontend User Interface (UI)
> * **Action:** Insert a new subsection: `### 3.1 The Pipeline Orchestrator (Backend UI Bridge)`
> * **Content:** Explain how `[main.py](./main.py)` exposes endpoints that save UI configurations directly into SQLite. Explain that `[sync_engine.py](./sync_engine.py)` dynamically reads these at runtime, replacing hard-coded logic.
> * **Constraint - Tables:** Update the **Table of Contents** at the top of the file to include `3.1 The Pipeline Orchestrator (Backend UI Bridge)`.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.3.0:** [Epic 0 - Prompt 36](./PROMPT_ROADMAP.md#epic-0-prompt-36) - Built the Backend Bridge for the UI Pipeline Orchestrator, dynamically linking UI configs to the Python engines.`
> 
> **Output Actions:**
> 1. Silently update `db_init.py`, `main.py`, and `sync_engine.py`.
> 2. Silently update `README.md` exactly as instructed above."

---

<a id="epic-0-prompt-37"></a>
### Epic 0 - Prompt 37: UI Pipeline Orchestrator (Frontend Vertical Stepper)
**Internal Simulation & Correction:** *With the backend bridge active, the Google Apps Script UI needs a visual layout to control it. A Material Design Vertical Stepper or Accordion is required to cleanly segment the pipeline into 3 logical phases for the user.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Apps Script UI)**
> We need to build the visual interface for the Pipeline Orchestrator in our Google Apps Script frontend.
> 1. **Update the Apps Script HTML (`index.html` or equivalent):** Implement a Material Design Vertical Stepper (or Accordions) with three sections:
>    - **Epic 0 - Prompt 1: Ingestion Filters:** Checkboxes bound to the Gmail labels (`CATEGORY_PROMOTIONS`, etc.).
>    - **Epic 0 - Prompt 2: AI Config:** Dropdowns to select LLM models for Gmail and Drive.
>    - **Epic 0 - Prompt 3: Post-Processing:** Checkboxes for Auto-Archive and Quarantine holds.
> 2. **Update the Frontend JS/GS Logic:** Add an initialization function that fetches the current state from `GET /api/settings/pipeline` via our webhook bridge to populate the UI. Add a 'Save Pipeline Config' button that bundles the UI state into JSON and sends it to `POST /api/settings/pipeline`.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 3.1 The Pipeline Orchestrator (Backend UI Bridge)
> * **Action:** Rename the header to `### 3.1 The Pipeline Orchestrator`. Append a new paragraph detailing the Frontend UI.
> * **Content:** Explain the 3-Phase Material Design layout (Ingestion Filters, AI Config, Post-Processing) built into the Apps Script UI, and how it empowers the user to visually dictate the AI's behavior and routing logic.
> * **Constraint - Tables:** Update the **Table of Contents** to reflect the renamed header.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.4.0:** [Epic 0 - Prompt 37](./PROMPT_ROADMAP.md#epic-0-prompt-37) - Built the Material Design 3-Phase Vertical Stepper in the Apps Script UI to control the pipeline.`
> 
> **Output Actions:**
> 1. Silently update the relevant Apps Script `.html` and `.gs` files.
> 2. Silently update `README.md` exactly as instructed above."

<a id="epic-0-prompt-38"></a>
### Epic 0 - Prompt 38: Taxonomy Upgrade & AI Tuning Hooks (Backend)
**Internal Simulation & Correction:** *To prevent purpose duplication and allow user-defined extraction rules, the SQLite schema needs upgrading. We must add `is_global` and `custom_extraction_rules` columns, and instruct the Python LLM engine to dynamically inject these rules into the Epic 0 - Prompt 2 prompt.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Database & LLM Engine)**
> 1. **Update `db_init.py`:** Modify the SQLite schema creation. 
>    - In `Taxonomy_Purposes`, add `is_global BOOLEAN DEFAULT 0` and `custom_extraction_rules TEXT`. 
>    - In `Taxonomy_Correspondents`, add `custom_extraction_rules TEXT`.
>    - Update the seed data logic to insert the Universal Purposes (e.g., 'Receipt / Invoice', 'Bill / Statement', 'Policy / Terms Update') with `is_global = 1`.
> 2. **Update `llm_engine.py`:** Modify the Epic 0 - Prompt 2 Extraction logic. Before finalizing the prompt sent to Gemini, query the database for the identified Correspondent and Purpose. If `custom_extraction_rules` exist for either, explicitly append those instructions to the prompt's extraction constraints.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 4. Database Schema
> * **Action:** Insert a new subsection: `### 4.2 Global Purposes & AI Tuning Hooks`
> * **Content:** Explain the difference between Global and Domain-Specific Purposes to prevent taxonomy bloat. Explain how `custom_extraction_rules` allow users to inject rule-based constraints directly into the `[llm_engine.py](./llm_engine.py)` prompt at runtime without modifying code.
> * **Constraint - Tables:** Update the **Table of Contents** at the top of the file to include `4.2 Global Purposes & AI Tuning Hooks`.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.5.0:** [Epic 0 - Prompt 38](./PROMPT_ROADMAP.md#epic-0-prompt-38) - Upgraded SQLite schema to support Global Purposes and dynamic AI Tuning Hooks.`
> 
> **Output Actions:**
> 1. Silently update `db_init.py` and `llm_engine.py`.
> 2. Silently update `README.md` exactly as instructed above."

---

<a id="epic-0-prompt-39"></a>
### Epic 0 - Prompt 39: Taxonomy Upgrade & AI Tuning Hooks (Frontend UI)
**Internal Simulation & Correction:** *Now that the backend supports global purposes and custom AI rules, the Apps Script UI needs to display them properly using HTML `<optgroup>` tags and provide text areas for users to write their custom LLM extraction instructions.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Apps Script UI & API Bridge)**
> 1. **Update `main.py` (FastAPI):** Ensure there are endpoints (e.g., `PUT /api/entities/correspondents/{id}`) to accept and save `custom_extraction_rules` strings to the database.
> 2. **Update Apps Script HTML/JS:** >    - **Dropdowns:** When rendering the 'Purpose' dropdown in the manual review modal, parse the `is_global` boolean. Group universal purposes under an `<optgroup label="Global Purposes">` at the top, and specific purposes under `<optgroup label="Category-Specific">` below a divider.
>    - **Rule Editors:** Add a Text Area labeled 'Custom AI Extraction Rules' to the Correspondent and Purpose profile edit views. Wire the Save button to transmit this text to the FastAPI backend.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 3. The Frontend User Interface (UI)
> * **Action:** Insert a new subsection: `### 3.2 Entity Management & Prompt Tuning UI`
> * **Content:** Detail how the UI groups Global vs. Specific Purposes using Material dropdowns. Explain that the text areas in the profile views act as a direct, no-code pipeline for users to tune the AI's extraction behavior for specific vendors.
> * **Constraint - Tables:** Update the **Table of Contents** at the top of the file to include this new subsection.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.6.0:** [Epic 0 - Prompt 39](./PROMPT_ROADMAP.md#epic-0-prompt-39) - Built the Entity Management UI, introducing grouped taxonomy dropdowns and no-code AI prompt tuning text areas.`
> 
> **Output Actions:**
> 1. Silently update `main.py` and the Apps Script UI files.
> 2. Silently update `README.md` exactly as instructed above."

<a id="epic-0-prompt-40"></a>
### Epic 0 - Prompt 40: The Privacy Guarantee (Walled Garden)
**Internal Simulation & Correction:** *Nexus Hub handles highly sensitive personal data. We need to explicitly state the 'Walled Garden' privacy philosophy in the executive summary so users understand their data never leaves their personal Google ecosystem and is not used to train public AI models.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Continuous Documentation (`README.md`)**
> * **Location:** Section 1. Executive Summary & Core Features.
> * **Action:** Insert a new subsection titled `### The Privacy Guarantee: Your Data, Your Walled Garden`.
> * **Content:** Explain that Nexus Hub is built on absolute data sovereignty. Because it is self-hosted entirely within the user's Google Workspace and GCP environment, data never transits a third-party server. Emphasize that the Gemini API is used under Google Cloud's enterprise terms, meaning private documents and emails are **never** used to train public foundation models. 
> * **Constraint - Tables:** Update the **Table of Contents** at the top of the file to include this new subsection.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.7.0:** [Epic 0 - Prompt 40](./PROMPT_ROADMAP.md#epic-0-prompt-40) - Documented the 'Walled Garden' Privacy Guarantee and enterprise AI data protection policies.`
> 
> **Output Actions:**
> 1. Silently update `README.md` exactly as instructed above."

---

<a id="epic-0-prompt-41"></a>
### Epic 0 - Prompt 41: Security Architecture & Network Boundaries
**Internal Simulation & Correction:** *Instead of a separate SECURITY.md file, we need a dedicated section within the master README that explains the technical security implementations, specifically the Webhook HMAC signatures and VM network boundaries.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Continuous Documentation (`README.md`)**
> * **Location:** We are creating a new Level 1 Section. Insert `## 10. Security Architecture & Network Boundaries` immediately before the 'AI-Assisted Development CONOPS' section. (You must renumber the CONOPS section to 11, and the Glossary to 12).
> * **Action:** Add technical explanations for how the system is secured against outside access.
> * **Content:** >   - **Webhook Authentication:** Explain the HMAC-SHA256 protocol. The FastAPI backend silently drops any incoming requests that do not possess a cryptographic signature matching the shared secret, making the API immune to unauthorized web scraping or execution.
>   - **VM Firewalls & Containerization:** Note that the Python backend runs inside an isolated Docker network on the GCP VM, further reducing the attack surface. 
> * **Constraint - Tables:** Update the **Table of Contents** to include Section 10 and renumber Sections 11 and 12 accordingly. 
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.8.0:** [Epic 0 - Prompt 41](./PROMPT_ROADMAP.md#epic-0-prompt-41) - Added a dedicated Security Architecture section detailing HMAC webhook verification and VM network isolation.`
> 
> **Output Actions:**
> 1. Silently update `README.md` exactly as instructed above."

---

<a id="epic-0-prompt-42"></a>
### Epic 0 - Prompt 42: OAuth Boundaries & Scope Justification
**Internal Simulation & Correction:** *During installation, users are prompted to grant broad Google permissions. We must transparently document exactly why each OAuth scope is required and how the tokens are securely managed on the headless VM.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Continuous Documentation (`README.md`)**
> * **Location:** Section 10. Security Architecture & Network Boundaries (which was created in the previous stage).
> * **Action:** Insert a new subsection: `### 10.1 OAuth Boundaries & Scope Justification`.
> * **Content:** Transparently document the required Google Workspace permissions and their explicit purposes to reassure users:
>   - `gmail.modify`: Required to read incoming emails, extract payloads, and subsequently apply the 'ARCHIVED' or processed labels to achieve the Zero-Inbox state.
>   - `drive`: Required to download newly uploaded PDFs for Document AI OCR, and to move files between the 'Nexus Dropbox' and permanent storage.
>   - `contacts.readonly`: Required solely for the Entity Bootstrapping phase to securely transform personal contacts into taxonomy correspondents.
>   - **Token Management:** Explicitly state that the `token.json` resides exclusively inside the headless, firewalled VM and is never exposed to the frontend Apps Script UI.
> * **Constraint - Tables:** Update the **Table of Contents** to include this new subsection.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.9.0:** [Epic 0 - Prompt 42](./PROMPT_ROADMAP.md#epic-0-prompt-42) - Documented OAuth scope justifications and token management security protocols.`
> 
> **Output Actions:**
> 1. Silently update `README.md` exactly as instructed above."

<a id="epic-0-prompt-43"></a>
### Epic 0 - Prompt 43: UI Tooltip Sweep & Continuous UX Protocol
**Internal Simulation & Correction:** *Recent UI additions (Pipeline Orchestrator, AI Tuning Hooks) lack inline documentation. We must sweep the Apps Script UI to add tooltips to all new elements, and update our CONOPS to mandate that UI text is always maintained alongside the master documentation.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Apps Script UI Tooltips)**
> We must ensure our complex AI UI is self-documenting for the end-user. Sweep the Apps Script HTML/JS files and inject Material Design tooltips (or standard title/help-text attributes) for the following new elements:
> * **Phase 1 Ingestion Filters:** Add tooltips explaining that toggling these drops the emails *before* they consume expensive AI quota.
> * **Phase 2 AI Models:** Add tooltips explaining the tradeoff (e.g., Gemini 1.5 Flash for speed/cost, Pro for complex reasoning).
> * **Taxonomy Dropdowns:** Add tooltips explaining the difference between Global Purposes and Category-Specific Purposes.
> * **Custom AI Extraction Rules:** Add a detailed tooltip to this text area explaining that this text is dynamically injected into the LLM prompt to force specific data extraction (e.g., 'Extract the invoice total').
> 
> **Task 2: Continuous Documentation (`README.md` CONOPS Update)**
> * **Location:** Section 10.2 The Continuous Documentation Protocol.
> * **Action:** Update the blockquote for the **Standard Prompt Footer**.
> * **Content:** Add a new bullet point to the standard footer that says: `* If modifying the UI, ensure all new interactive elements include inline user education (tooltips or help text) explaining their function.`
> * **Constraint - Hotlinks:** Maintain any existing relative Markdown links in this section.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.10.0:** [Epic 0 - Prompt 43](./PROMPT_ROADMAP.md#epic-0-prompt-43) - Performed a UI tooltip sweep on all AI pipeline controls and updated the AI CONOPS to mandate the Continuous UX Protocol.`
> 
> **Output Actions:**
> 1. Silently update the Apps Script UI files with the new tooltips.
> 2. Silently update `README.md` exactly as instructed above."

<a id="epic-0-prompt-44"></a>
### Epic 0 - Prompt 44: Fail-Fast Installation Scripts & Traceability
**Internal Simulation & Correction:** *The setup scripts are currently blind execution chains. We need to refactor `setup.sh` and `update.sh` into a Fail-Fast architecture. If a step fails, it must explicitly reference the exact section in `INSTRUCTIONS.md` to fix it, write to a local log, and attempt to fire a Pushover mobile alert.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Bash Scripts)**
> Refactor `setup.sh` and `update.sh` to use an assert-driven, fail-fast sequence.
> 1. **Checkpoints:** Break the script into discrete checks (e.g., Docker installed, `.env` exists, `credentials.json` exists, `token.json` generation successful, Docker containers return 200 OK).
> 2. **Traceability:** If any check fails, the script must `exit 1` and print a highly visible error message that points the user to the exact Phase and Step in `[INSTRUCTIONS.md](./INSTRUCTIONS.md)`. Example: `[!] FAILURE: credentials.json not found. Please review INSTRUCTIONS.md -> Phase 0, Step 3.`
> 3. **Error Handling:** Create an error trap function. If the script fails, it must:
>    - Append the failure reason to a local file named `setup_diagnostics.log` in the root directory.
>    - Check if `NEXUS_WEBHOOK_URL` is populated in the `.env` file. If yes, execute a `curl` POST to send the error message to the Pushover API.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 8. VM Lifecycle & Containerization.
> * **Action:** Insert a new subsection: `### 8.1 Fail-Fast Provisioning`.
> * **Content:** Explain that `[setup.sh](./setup.sh)` and `[update.sh](./update.sh)` utilize a fail-fast architecture. If a dependency or configuration is missing, the script halts immediately, references the exact fix in `INSTRUCTIONS.md`, and pushes a notification to the user's mobile device via the Pushover webhook while saving a local `setup_diagnostics.log`.
> * **Constraint - Tables:** Update the **Table of Contents** at the top of the file to include this new subsection.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the top of the 'Version History' section: `- **v2026.0.11.0:** [Epic 0 - Prompt 44](./PROMPT_ROADMAP.md#epic-0-prompt-44) - Refactored installation scripts into a Fail-Fast architecture with direct documentation traceability and mobile webhook alerts.`
> * Ensure all UI/CLI additions include standard user education/tooltips per the Continuous UX Protocol.
> 
> **Output Actions:**
> 1. Silently update `setup.sh` and `update.sh`.
> 2. Silently update `README.md` exactly as instructed above."

<a id="epic-0-prompt-45"></a>
### Epic 0 - Prompt 45: Quota Governor Dashboard (API Burn Rate UI)
**Internal Simulation & Correction:** *The Intelligent Quota Governor throttles background processing when daily limits are approached, but the user currently has no visibility into this. We need to build a FastAPI endpoint to expose the current `operation_cost` and a visual progress bar in the Apps Script UI.*

**Copy/Paste this to Gemini Code Assist:**
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (API & UI)**
> 1. **Update `main.py` (FastAPI):** Create a new endpoint `GET /api/health/quota` that queries the database for today's current API burn rate (operation cost) and returns it alongside the maximum daily limit.
> 2. **Update Apps Script HTML/JS:** Build a 'Quota Governor' metric card in the UI dashboard. It should display a visual progress bar representing the daily API usage and explicitly state if the system is currently in a 'Throttled' state.
> 3. **Continuous UX Protocol:** Add a tooltip to the progress bar explaining that historical batches are automatically throttled at 70% capacity to reserve bandwidth for real-time incoming Gmail webhooks.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 6. The Intelligent Quota Governor.
> * **Action:** Append a new paragraph at the end of the section.
> * **Content:** Explain that the frontend UI features a live Quota Governor dashboard that visualizes the daily API burn rate. Mention that this allows the user to see exactly when the system enters a protective throttled state without needing to check backend logs.
> * **Constraint - Hotlinks:** Wrap `[main.py](./main.py)` in a relative Markdown link.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet point to the top of the 'Version History' section: `- **v2026.0.12.0:** [Epic 0 - Prompt 45](./PROMPT_ROADMAP.md#epic-0-prompt-45) - Built the Quota Governor Dashboard in the Apps Script UI to visualize daily API burn rates and throttling status.`
> 
> **Output Actions:**
> 1. Silently update `main.py` and the Apps Script UI files.
> 2. Silently update `README.md` exactly as instructed above."

---

## EPIC 1: Autonomous Profiling & Lifecycle Management (v1.x.x)
*Notice to AI: We are now executing Epic 1. Update the README version history to v1.x.x for the following prompts.*

<a id="epic-1-prompt-1"></a>
### Epic 1 - Prompt 1: Core Audit Fixes (Gmail Tuning & HMAC Trap)
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. We are starting Epic 1.
> 
> **Task 1: Code Implementation (`llm_engine.py`)**
> 1. Modify the SELECT query in `process_gmail_thread` to fetch `tc.custom_extraction_rules as c_rules` and `tp.custom_extraction_rules as p_rules`.
> 2. Fetch all purposes where `is_global = 1 AND is_gmail_enabled = 1`. 
> 3. When building the `whitelist_paths`, iterate through global purposes and append them to the current correspondent. 
> 4. Inject a new key `"rules": c_rules` (if they exist) into the `entity_profiles` dictionary for the prompt context.
> 
> **Task 2: Code Implementation (`update.sh`)**
> 1. Delete the raw `curl` health check (it fails due to HMAC).
> 2. Replace it with a `while` loop checking native Docker health: `docker inspect --format="{{json .State.Health.Status}}" nexus-api`.
> 3. Wait up to 30 seconds for the status to equal `"healthy"`. If it fails, trigger the `trap_error` function.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.1.1.0:** [Epic 1.1](#epic-1-prompt-1) - Applied audit fixes for Gmail global tuning hooks and refactored CI/CD to use Docker health checks.`
> 
> **Output Actions:**
> 1. Silently update `llm_engine.py` and `update.sh`.
> 2. Silently update `README.md`."

<a id="epic-1-prompt-2"></a>
### Epic 1 - Prompt 2: Gmail Post-Processing & Auto-Archive
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Backend & Frontend)**
> 1. **Update `db_init.py`:** In `Taxonomy_Purposes`, add column: `auto_archive BOOLEAN DEFAULT 0`.
> 2. **Update `sync_engine.py`:** If a matched Purpose has `auto_archive == 1`, execute a Gmail API call to remove the `INBOX` label from the thread.
> 3. **Update Apps Script UI:** Add a toggle switch next to each Tier 3 Purpose labeled 'Auto-Archive on Match'. Wire this to update the DB. Include a descriptive tooltip.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 5. The Synchronization Engine.
> * **Action:** Insert subsection: `### 5.1 Post-Processing & Auto-Archive`. Explain the capability to automatically drop the INBOX label. Update Table of Contents.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.1.2.0:** [Epic 1.2](#epic-1-prompt-2) - Built Gmail API post-processing for Tier 3 Auto-Archiving.`
> 
> **Output Actions:**
> 1. Silently update the codebase.
> 2. Silently update `README.md`."

<a id="epic-1-prompt-3"></a>
### Epic 1 - Prompt 3: Advanced Inbox Retention Engine
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Retention Engine & UI)**
> 1. **Update `db_init.py`:** Add table `Config_Retention_Rules` (cols: id, target_category, action, days_old, is_active).
> 2. **Create `retention_worker.py`:** Query this table, search Gmail for matching threads, and execute batch Archive/Trash API commands.
> 3. **Update Apps Script UI:** Create an 'Inbox Cleanup Rules' tab to manage rules and trigger a manual run. Add tooltips explaining Archive vs Trash.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 5.1 Post-Processing & Auto-Archive.
> * **Action:** Rename to `### 5.1 Post-Processing & Retention Rules`. Append paragraph detailing batch sweeping logic. Update Table of Contents.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.1.3.0:** [Epic 1.3](#epic-1-prompt-3) - Engineered the Advanced Inbox Retention Engine.`
> 
> **Output Actions:**
> 1. Silently update DB/UI, create `retention_worker.py`.
> 2. Silently update `README.md`."

<a id="epic-1-prompt-4"></a>
### Epic 1 - Prompt 4: The Drive Relocation Engine
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Drive API Execution)**
> 1. **Update `db_init.py`:** In `Config_System`, add JSON key: `drive_permanent_archive_id`.
> 2. **Update `sync_engine.py`:** After extraction, if `drive_permanent_archive_id` is populated, use Drive API `files().update` to remove the file from the Dropbox parent ID and move it to the archive parent ID.
> 3. **Update Apps Script UI:** Add an input field for 'Permanent Archive Folder ID' in the Pipeline Orchestrator tab with an explanatory tooltip.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 4.1 The Anti-Folder Philosophy & Drive Topology.
> * **Action:** Append paragraph explaining the programmatic parent directory rewrite logic.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.1.4.0:** [Epic 1.4](#epic-1-prompt-4) - Built the Drive Relocation Engine to clear the staging dropzone.`
> 
> **Output Actions:**
> 1. Silently update codebase.
> 2. Silently update `README.md`."

---

<a id="epic-1-prompt-4-1"></a>
### Epic 1 - Prompt 4.1: Mid-Epic Audit Remediation (Bug Fixes)
> "I am the Lead Architect. We have just completed Epic 1.4. Before we move on to the Historical Import Engine, we must patch several critical vulnerabilities identified during a static analysis of the codebase up to this point. Please read `audit/AUDIT_REPORT_APR_2026.md` in the workspace for context.
> 
> **Task 1: Security & Hardening (`main.py` & `llm_engine.py`)**
> 1. **Patch HMAC Middleware (`main.py`):** Update the `verify_nexus_signature` middleware. It must enforce the signature check on `POST`, `PUT`, `DELETE`, and `PATCH` methods (not just `POST`).
> 2. **Configure CORS (`main.py`):** Import `CORSMiddleware` from `fastapi.middleware.cors` and add it to the `app`, allowing all origins (`["*"]`), methods, and headers.
> 3. **Prevent SQL Injection (`llm_engine.py`):** In the `ask_rag()` function, implement strict sanitization before executing the AI-generated SQL string. Assert that the string `upper().startswith("SELECT")`. If the string contains `DROP`, `DELETE`, `UPDATE`, `INSERT`, or `ALTER`, raise a `ValueError` immediately and do not execute it.
> 
> **Task 2: Resilience & Pipeline Fixes (`sync_engine.py` & `llm_engine.py`)**
> 1. **Fix RAG Schema Mismatch (`llm_engine.py`):** In the `ask_rag()` schema definition string, change `taxonomy_id` to `purpose_id` to match the actual database schema.
> 2. **Fix Missing Drive Invocation (`sync_engine.py`):** Inside the `sync_drive()` function's loop, you must actually invoke `process_drive_document()` (passing the downloaded file content) before executing the Drive Relocation logic.
> 3. **Isolate API Exceptions (`sync_engine.py`):** Inside both `sync_gmail()` and `sync_drive()`, wrap the calls to the LLM processing functions in a `try/except Exception as e:` block. If a failure occurs for a specific artifact, log the error and use `continue` to move to the next item in the batch without crashing the entire `run_sync` loop.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add a new bullet to the 'Version History' section: `- **v2026.1.4.1:** [Epic 1.4.1](#epic-1-prompt-4-1) - Executed Mid-Epic Audit Remediation: Patched HMAC bypass, secured RAG SQL injection, fixed Drive LLM invocation, and isolated API exceptions.`
> 
> **Output Actions:**
> 1. Silently update `main.py`, `llm_engine.py`, and `sync_engine.py`.
> 2. Silently update `README.md` exactly as instructed."
> 3. 
---

<a id="epic-1-prompt-5"></a>
### Epic 1 - Prompt 5: The Entity Profiler & Template Engine
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. We are finalizing Epic 1.
> 
> **Task 1: Code Implementation (Template Extraction)**
> 1. Create a new directory in the root called `prompts/`.
> 2. Extract the hardcoded LLM instructions from `llm_engine.py`. Create at least three XML-fenced text files in the new directory: `gmail_extraction.tmpl`, `drive_extraction.tmpl`, and `entity_profiler.tmpl`.
> 3. Update `llm_engine.py` to dynamically read these `.tmpl` files from the disk when constructing the Gemini payload, rather than relying on hardcoded strings.
> 
> **Task 2: Code Implementation (Autonomous Profiling)**
> 1. In `llm_engine.py`, create a new function: `generate_sender_profile(sender_email, email_body)`. This must use the `entity_profiler.tmpl` to generate a 15-word definition of the sender and guess their parent Correspondent category.
> 2. In `sync_engine.py`, update the routing logic. Before standard triage, check if the sender exists in `Taxonomy_Senders`. If they are unknown, pause, trigger `generate_sender_profile()`, save the new profile and guessed Correspondent ID to the database, and *then* proceed with standard extraction.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.1.5.0:** [Epic 1.5](#epic-1-prompt-5) - Engineered the Entity Profiler for autonomous classification of unknown senders and externalized LLM prompts to XML templates.`
> 
> **Output Actions:**
> 1. Silently create the `prompts/` directory and `.tmpl` files.
> 2. Silently update `llm_engine.py` and `sync_engine.py`.
> 3. Silently update `README.md` exactly as instructed."

---

<a id="epic-1-prompt-6"></a>
### Epic 1 - Prompt 6: The Historical Import Engine & Queue
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. We are building an asynchronous buffering system to handle massive historical data ingestion without triggering Google API rate limits.
> 
> **Task 1: Schema Update (`db_init.py`)**
> 1. Create a new table: `Ingestion_Queue`.
> 2. Columns: `id INTEGER PRIMARY KEY`, `source TEXT` (e.g., 'gmail'), `source_id TEXT` (the Gmail message/thread ID), `status TEXT DEFAULT 'PENDING'` (states: PENDING, PROCESSING, COMPLETE, FAILED), `added_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP`.
> 
> **Task 2: API Endpoint (`main.py`)**
> 1. Create a new endpoint: `POST /api/ingestion/queue-historical`. It must accept a JSON payload containing a `search_query` string (e.g., 'before:2025-01-01').
> 2. **Logic:** The endpoint must use the Gmail API (`users().messages().list`) passing the `q=search_query` parameter. It must iterate through pagination tokens to fetch *only the IDs* of all matching messages. 
> 3. Bulk insert these IDs into the `Ingestion_Queue` table with `status = 'PENDING'`. Return a success JSON with the total number of items queued.
> 
> **Task 3: The Throttled Worker (`sync_engine.py`)**
> 1. Modify the main daemon loop. After performing the standard delta-sync, query the `Ingestion_Queue` for `status = 'PENDING' LIMIT 20`.
> 2. For each queued ID, change status to `PROCESSING`, fetch the full payload via the Gmail API, run the standard LLM extraction pipeline, and finally update the queue status to `COMPLETE`.
> 3. Ensure error handling updates the status to `FAILED` if the LLM or API times out, allowing it to be retried or audited later.
> 
> **Task 4: UI Implementation (`Index.html` & `JS_Actions.html`)**
> 1. In the Mission Control dashboard (`#tab-dashboard`), build a 'Historical Import' widget.
> 2. Include a text input for a Gmail search string, a 'Queue Import' button, and a small counter showing the current number of PENDING items in the queue.
> 3. Wire the button to send the search string to the new `POST` endpoint and display a success toast/notification.
> 
> **Task 5: Documentation & Versioning**
> 1. **In `README.md`:** Add to Version History: `- **v2026.1.6.0:** [Epic 1.6](#epic-1-prompt-6) - Engineered the asynchronous Historical Import Engine and SQLite ingestion buffer.`
> 2. Insert a brief section in the README explaining how to use standard Gmail search syntax in the UI to safely import old data.
> 
> **Output Actions:**
> 1. Silently execute the code implementation across `db_init.py`, `main.py`, `sync_engine.py`, and the frontend UI.
> 2. Silently update `README.md` exactly as instructed."

---

<a id="epic-1-prompt-7"></a>
### Epic 1 - Prompt 7: The Materialization Pipeline & Lineage Tracking
> "I am the Lead Architect. We are building the Materialization Pipeline to convert transient HTML emails into permanent PDFs in Google Drive, establishing a strict lineage between the source and the new artifact.
> 
> **Task 1: Schema Updates (`db_init.py`)**
> 1. In `Workspace_Artifacts`, add `parent_artifact_id TEXT` (self-referencing foreign key).
> 2. In `Workspace_Artifacts`, add `lifecycle_status TEXT DEFAULT 'ACTIVE'`. (Options: 'ACTIVE', 'MATERIALIZED', 'TRASHED').
> 
> **Task 2: Backend Lineage & Deduplication (`main.py`)**
> 1. **Update AST Parser:** Modify the `/api/artifacts/search` and `/api/analytics/threads` endpoints. By default, append a SQL clause to exclude `lifecycle_status = 'MATERIALIZED'` so the UI and Sankey charts do not double-count parent emails that have been converted to PDFs. 
> 
> **Task 3: The Materialization Engine (`sync_engine.py`)**
> 1. Create a new function: `materialize_artifact(artifact_id)`.
> 2. **Logic:** Fetch the raw HTML body of the Gmail artifact. (Stub out the actual PDF rendering tool, e.g., `# TODO: Implement WeasyPrint or API conversion here`).
> 3. Upload the generated PDF bytes to the Google Drive Dropzone via the Drive API.
> 4. Insert the new Drive artifact into the DB, setting its `parent_artifact_id` to the original email's ID.
> 5. Update the original email's `lifecycle_status` to `'MATERIALIZED'`.
> 
> **Task 4: The Workflow Hub UI (`Index.html` & `JS_Actions.html`)**
> 1. Add a 'Workflow Hub' icon/button in the top right navigation header.
> 2. Clicking it opens a modal overlay. Include a section for 'Materialization Pipeline'.
> 3. Add a button: "Materialize Selected Items". Wire this to send the `appState.selectedIds` array to a new `POST /api/workflows/materialize` endpoint.
> 4. **Grid UI Update:** In `renderKnowledgeGrid()`, if an item has a `parent_artifact_id` or acts as a parent, add a visual 'Linked' icon or badge to the `.artifact-card`.
> 
> **Task 5: Documentation & Versioning**
> 1. **In `README.md`:** Add to Version History: `- **v2026.1.7.0:** [Epic 1.7](#epic-1-prompt-7) - Engineered the Materialization Pipeline, Lineage Tracking, and Workflow Hub to normalize HTML emails into Drive PDFs.`
> 
> **Output Actions:**
> 1. Silently execute the code implementation across `db_init.py`, `main.py`, `sync_engine.py`, and the frontend UI.
> 2. Silently update `README.md` exactly as instructed."

---

<a id="epic-1-prompt-8"></a>
### Epic 1 - Prompt 8: The Google Tasks Action Engine
> "I am the Lead Architect. We are integrating the Google Tasks API to autonomously generate actionable to-do items for system alerts and artifacts flagged by the LLM as requiring user action.
> 
> **Task 1: GCP & Schema Preparation (`db_init.py` & `INSTRUCTIONS.md`)**
> 1. **Schema Update:** In the `Workspace_Artifacts` table, add a new column: `google_task_id TEXT DEFAULT NULL`. This is critical to prevent duplicate task generation during sync loops.
> 2. **System Config:** In `Config_System`, add a new key: `nexus_task_list_id` to store the specific Google Tasks list we will push to.
> 3. **Documentation:** Update `INSTRUCTIONS.md` to instruct the user to enable the 'Google Tasks API' in their GCP console and authorize the `https://www.googleapis.com/auth/tasks` scope.
> 
> **Task 2: The Task Generation Engine (`sync_engine.py`)**
> 1. **Create Function:** Build a new function: `push_to_google_tasks(artifact_data)`.
> 2. **Logic Trigger:** Inside the main ingestion loops (`sync_gmail`, `sync_drive`), after the LLM classification is complete, check if the AI flagged the item with `action_required = 1` OR if it is a `system_alert`.
> 3. **Execution:** If true and `google_task_id` is NULL, call the Google Tasks API (`tasks().insert`) to create a new task in the designated list. 
> 4. **Payload Formatting:** Set the Task `title` to the artifact's Subject/Name. Set the `notes` to include a summary of why action is needed and a direct hyperlink to the artifact in Drive or Gmail.
> 5. **State Save:** Extract the resulting Task ID from the Google API response and save it to the `google_task_id` column in the database.
> 
> **Task 3: Documentation & Versioning**
> 1. **In `README.md`:** Add to Version History: `- **v2026.1.8.0:** [Epic 1.8](#epic-1-prompt-8) - Engineered the Google Tasks Action Engine for autonomous workflow generation.`
> 2. Update the README's Lifecycle Management section to explain how flagged artifacts automatically populate the user's Google Tasks.
> 
> **Output Actions:**
> 1. Silently execute the code implementation across `db_init.py` and `sync_engine.py`.
> 2. Silently update `README.md` and `INSTRUCTIONS.md` exactly as instructed."

---

## EPIC 2: The Core API & Graph Migration (v2.x.x)
*Notice to AI: We are now executing Epic 2. Update the README version history to v2.x.x for the following prompts.*

<a id="epic-2-prompt-1"></a>
### Epic 2 - Prompt 1: Telemetry & Effectiveness Schema Upgrade
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. We are starting Epic 2.
> 
> **Task 1: Code Implementation (`db_init.py`)**
> 1. **Update `Artifact_History`:** Add `processing_time_ms INTEGER`, `api_tokens_used INTEGER`, and `is_human_corrected BOOLEAN DEFAULT 0`.
> 
> **Task 2: Code Implementation (`sync_engine.py` & `llm_engine.py`)**
> 1. **Inject Telemetry:** Wrap the core LLM execution block in a timer (`time.time()`). Calculate elapsed ms.
> 2. **Log Tokens:** Extract `usage_metadata.total_token_count` from the Gemini response.
> 3. **Commit Telemetry:** Include `processing_time_ms` and `api_tokens_used` when inserting success logs.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.2.1.0:** [Epic 2.1](#epic-2-prompt-1) - Upgraded database schema and workers to capture execution telemetry.`
> 
> **Output Actions:**
> 1. Silently update DB and engines.
> 2. Silently update `README.md`."

<a id="epic-2-prompt-2"></a>
### Epic 2 - Prompt 2: The ROI & Aggregation API
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`main.py`)**
> 1. **Create Endpoint:** Build `GET /api/analytics/roi-dashboard`.
> 2. **Effectiveness:** Calculate 'First-Pass Accuracy' (Items where `is_human_corrected = 0` / total items) and 'Exception Rate'.
> 3. **Telemetry:** Query average `processing_time_ms` and `api_tokens_used` across the last 1000 records. 
> 4. **Throughput:** Calculate total artifacts processed in 30 days, grouped by source (Gmail vs Drive). Return as JSON.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 9. Telemetry, Diagnostics & Notifications
> * **Action:** Insert subsection: `### 9.2 The ROI & Analytics Aggregator`. Detail the grouping metrics.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.2.2.0:** [Epic 2.2](#epic-2-prompt-2) - Engineered the ROI Analytics endpoint.`
> 
> **Output Actions:**
> 1. Silently update `main.py` and `README.md`."

<a id="epic-2-prompt-3"></a>
### Epic 2 - Prompt 3: The Unified Search AST Engine
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`main.py`)**
> 1. **Create Endpoint:** Build `GET /api/artifacts/search` accepting `q` (query string), `limit` (default 50), and `offset` (default 0).
> 2. **AST Parser:** Build logic to parse exact matches (`Correspondent:"Amazon"`), exclusions (`!Purpose:Receipt`), and temporal bounds (`Date:YYYY-MM` or `Date:YYYY-MM-DD`). For `YYYY-MM`, use Python `calendar` to generate a SQLite `BETWEEN 'YYYY-MM-01' AND 'YYYY-MM-31'` clause. For `YYYY-MM-DD`, enforce an exact match.
> 3. **Pagination Bounding:** If `q` is empty, default query to `document_date` within the last 30 days. Execute `SELECT COUNT(*)` first to return `total_matches` alongside the paginated array.
> 
> **Task 2: Continuous Documentation (`README.md`)**
> * **Location:** Section 7. The Frontend SPA.
> * **Action:** Insert subsection: `### 7.1 The Query-First Omnibox & AST`. Detail the parser, temporal routing, and limit/offset architecture.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.2.3.0:** [Epic 2.3](#epic-2-prompt-3) - Engineered the Backend Search AST supporting exclusions, temporal parsing, and pagination.`
> 
> **Output Actions:**
> 1. Silently update `main.py` and `README.md`."

<a id="epic-2-prompt-4"></a>
### Epic 2 - Prompt 4: Threads Sankey API & Color Schema
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`db_init.py`)**
> 1. Add `brand_color TEXT` to `Taxonomy_Correspondents`.
> 2. Update `seed_default_taxonomy` to include hex codes for default correspondents.
> 
> **Task 2: Code Implementation (`main.py`)**
> 1. **Create Endpoint:** Build `GET /api/analytics/threads` accepting `q` and `node_limit` (default 15).
> 2. **Grouping Logic:** Use AST logic to filter the base set. Group the flow (Source -> Entity -> Correspondent -> Purpose) by volume descending. `LIMIT` by `node_limit`, and `SUM()` the rest into an 'Other' node. Include `brand_color` in the response.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.2.4.0:** [Epic 2.4](#epic-2-prompt-4) - Engineered the Threads API with long-tail grouping and brand color injection.`
> 
> **Output Actions:**
> 1. Silently update `db_init.py`, `main.py`, and `README.md`."

<a id="epic-2-prompt-5"></a>
### Epic 2 - Prompt 5: Mission Control Heatmap API
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`main.py`)**
> 1. **Create Dashboard Endpoint:** Build `GET /api/dashboard/mission-control`. Calculate 'Total Artifacts', 'Action Required', and 'Quarantine' counts.
> 2. **Create Heatmap Endpoint:** Build `GET /api/analytics/heatmap` accepting `tier`, `timeframe_months`, and `item_limit`. Filter by months, group by `strftime('%Y-%m')` and the selected tier. Return JSON matrix.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.2.5.0:** [Epic 2.5](#epic-2-prompt-5) - Engineered Mission Control API with SQLite temporal grouping.`
> 
> **Output Actions:**
> 1. Silently update `main.py` and `README.md`."

<a id="epic-2-prompt-6"></a>
### Epic 2 - Prompt 6: User Preferences & Boot Routing
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`main.py` & `db_init.py`)**
> 1. Ensure `Config_System` stores UI preferences (default: `key='default_view'`, `value='dashboard'`).
> 2. Update `/api/settings` endpoints to expose/modify this value.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.2.6.0:** [Epic 2.6](#epic-2-prompt-6) - Added persistent user preferences to support dynamic frontend boot routing.`
> 
> **Output Actions:**
> 1. Silently update `db_init.py`, `main.py`, and `README.md`."

<a id="epic-2-prompt-7"></a>
### Epic 2 - Prompt 7: Zero-Shot Taxonomy Rules API
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`main.py` & `llm_engine.py`)**
> 1. **Create Endpoint:** Build `POST /api/taxonomy/zero-shot-rule`. It must accept a JSON payload containing an array of `artifact_ids` and a string `instruction` (e.g., "Always extract the total without tax").
> 2. **Processing Logic:** Fetch the current `purpose_id` shared by these artifacts. Fetch the existing `custom_extraction_rules` for that purpose from the database. Append the user's new `instruction` to the existing rules and update the `Taxonomy_Purposes` table. Return a success status.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.2.7.0:** [Epic 2.7](#epic-2-prompt-7) - Built the Zero-Shot Rule generation API for bulk UI tuning.`
> 
> **Output Actions:**
> 1. Silently update `main.py` and `llm_engine.py`.
> 2. Silently update `README.md`."

---

## EPIC 3: The Nexus Paradigm Frontend (v3.x.x)
*Notice to AI: We are now executing Epic 3. Update the README version history to v3.x.x for the following prompts.*

<a id="epic-3-prompt-1"></a>
### Epic 3 - Prompt 1: Global Observability & Quota Dashboards
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. We are starting Epic 3.
> 
> **Task 1: Code Implementation (Apps Script UI)**
> 1. **Relocate Quota UI:** Take the 'Quota Governor' progress bar UI built in Epic 0 (Prompt 45) and relocate it into a new persistent Global Header at the top of `Index.html`.
> 2. **Health Badge:** Add a global System Health badge to this top header. Set frontend logic to ping `/api/health` every 60 seconds, dynamically changing color (Green/Yellow/Red) with tooltips.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.1.0:** [Epic 3.1](#epic-3-prompt-1) - Built the Global Observability header and integrated the Quota Governor Dashboard.`
> 
> **Output Actions:**
> 1. Silently update Apps Script UI files and `README.md`."

<a id="epic-3-prompt-2"></a>
### Epic 3 - Prompt 2: The Knowledge Grid Shell
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`CSS_Styles.html` & UI)**
> 1. **Update DOM:** Replace the existing legacy table with `<div id="knowledge-grid" class="artifact-grid">`.
> 2. **CSS Grid:** Define `.artifact-grid` as responsive `display: grid`.
> 3. **Card Anatomy:** Define `.artifact-card` with dynamic side-borders (red for Gmail, blue for Drive). Refactor the renderer to generate these HTML cards.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.2.0:** [Epic 3.2](#epic-3-prompt-2) - Replaced the legacy table with the responsive, metadata-first Knowledge Grid.`
> 
> **Output Actions:**
> 1. Silently update CSS and JS renderers.
> 2. Silently update `README.md`."

<a id="epic-3-prompt-3"></a>
### Epic 3 - Prompt 3: The Command-Line Omnibox
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (UI & JS)**
> 1. **Build Omnibox DOM:** Create a large search bar above the Knowledge Grid with nested Filter/Clear buttons. Add a typeahead overlay div.
> 2. **Tab-to-Complete:** Attach `keyup`/`keydown`. If a user types 'Med' and sees 'MedStar Health', pressing `Tab` locks "Correspondent:MedStar Health" into the string.
> 3. **Execution:** On `Enter`, convert text to UI 'Chips', and fire the fetch to `/api/artifacts/search`.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.3.0:** [Epic 3.3](#epic-3-prompt-3) - Built the Command-Line Omnibox with Tab-autocomplete prediction.`
> 
> **Output Actions:**
> 1. Silently update HTML/JS UI files and `README.md`."

<a id="epic-3-prompt-4"></a>
### Epic 3 - Prompt 4: Aggregate Context Drawer & Zero-Shot Rules
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`JS_State.html` & `JS_Actions.html`)**
> 1. **Multi-Select State:** Ensure `appState.selectedIds` tracks Shift/Ctrl clicks on `.artifact-card` elements.
> 2. **Aggregate Drawer:** If `selectedIds.size > 1`, group the metadata in the right-hand details pane.
> 3. **Zero-Shot UI:** Inject a 'Submit with AI (Create Rule)' button into the Drawer. Transmit the selected IDs and the user's custom instruction to `POST /api/taxonomy/zero-shot-rule`.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.4.0:** [Epic 3.4](#epic-3-prompt-4) - Implemented the Aggregate Context Drawer supporting bulk Zero-Shot Rule generation.`
> 
> **Output Actions:**
> 1. Silently update JS state/actions and `README.md`."

<a id="epic-3-prompt-5"></a>
### Epic 3 - Prompt 5: The 'Select All' Bulk Pattern
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (UI)**
> 1. **Selection Banner:** Add a hidden banner below the Omnibox. If a user selects all visible items, display: "All X items selected. Select all Y matching items."
> 2. **Global Select Logic:** If the user clicks the global select, set `isGlobalSelectActive = true`. When performing bulk edits, send the AST query string to the backend instead of an array of IDs to prevent DOM freezing.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.5.0:** [Epic 3.5](#epic-3-prompt-5) - Built the global 'Select All' UX pattern for massive query-based bulk operations.`
> 
> **Output Actions:**
> 1. Silently update HTML/JS and `README.md`."

<a id="epic-3-prompt-6"></a>
### Epic 3 - Prompt 6: System Analytics Dashboard
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Chart.js Integration)**
> 1. Include `Chart.js` via CDN. Add a 'System Analytics' nav item.
> 2. Build `#tab-analytics` containing 3 KPI metric cards and two `<canvas>` grids.
> 3. Write `renderAnalyticsDashboard()` to fetch from `/api/analytics/roi-dashboard` and instantiate a Doughnut chart (Manual Rework vs Automation) and a Bar chart (Throughput).
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.6.0:** [Epic 3.6](#epic-3-prompt-6) - Implemented the System Analytics Dashboard.`
> 
> **Output Actions:**
> 1. Silently update UI files and `README.md`."

<a id="epic-3-prompt-7"></a>
### Epic 3 - Prompt 7: Threads UI & Color Weaving
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Google Charts Sankey)**
> 1. Load Google Charts script. Create `#tab-threads` with a node-limit slider (5-50).
> 2. Write `hexToRgba(hex, opacity)` to convert DB brand colors to 0.45 opacity.
> 3. Write `renderThreadsView()` fetching from `/api/analytics/threads`. Apply the `rgba` values to link colors for transparent weaving.
> 4. Wire node clicks to update the Omnibox and switch views to the Knowledge Grid.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.7.0:** [Epic 3.7](#epic-3-prompt-7) - Implemented the Threads UI Sankey diagram with interactive routing and color weaving.`
> 
> **Output Actions:**
> 1. Silently update UI files and `README.md`."

<a id="epic-3-prompt-8"></a>
### Epic 3 - Prompt 8: Mission Control UI & Boot Routing
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (Mission Control)**
> 1. Map 'Home' icon to `#tab-dashboard` (Mission Control). Create `#tab-home` for the Knowledge Grid.
> 2. Build the Heatmap UI with a Chart.js Matrix (or Google Calendar chart) fetching from `/api/analytics/heatmap`. Wire cell clicks to inject `Date:YYYY-MM` into the Omnibox.
> 3. **Boot Routing:** In the init function, read the DB `default_view`. Automatically render Mission Control, Threads, or the Grid based on user preference.
> 
> **Task 2: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.3.8.0:** [Epic 3.8](#epic-3-prompt-8) - Finalized Mission Control dashboard and dynamic boot routing.`
> 
> **Output Actions:**
> 1. Silently update UI files and `README.md`."

---

## EPIC 4: Infrastructure as Code (v4.x.x)
*Notice to AI: We are now executing Epic 4. Update the README version history to v4.x.x for the following prompts.*

<a id="epic-4-prompt-1"></a>
### Epic 4 - Prompt 1: The Zero-Touch Provisioner (`provision.sh`)
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. We are starting Epic 4.
> 
> **Task 1: Code Implementation (`scripts/provision.sh`)**
> 1. **Delete Legacy File:** Ensure the old `setup.sh` file from the root directory is explicitly deleted from the repository, as it is now obsolete.
> 2. Write a bash script (`chmod +x`) in the new `scripts/` folder using `gcloud compute instances create` for an `e2-micro` VM.
> 3. Add `gcloud compute firewall-rules create` for `tcp:8000`.
> 4. Pass a multi-line inline `--metadata startup-script` that runs apt updates, installs python/sqlite3/git, creates a venv, installs requirements, and configures the `systemd` daemon.
> 
> **Task 2: Continuous Documentation (`README.md` & `INSTRUCTIONS.md`)**
> * **Location:** Create a new Section in README: `11. Infrastructure as Code (IaC)`.
> * **Action:** Detail how to run `./scripts/provision.sh` locally. Update `INSTRUCTIONS.md` to completely remove all references to manual SSH provisioning and replace them with the `gcloud` CLI commands.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.4.1.0:** [Epic 4.1](#epic-4-prompt-1) - Built the Zero-Touch Provisioner for automated GCP VM deployment and deprecated manual setup scripts.`
> 
> **Output Actions:**
> 1. Silently delete `setup.sh`, create `scripts/provision.sh`, and update documentation."

<a id="epic-4-prompt-2"></a>
### Epic 4 - Prompt 2: The CI/CD Deployment Script (`deploy.sh`)
> "You are the Lead Developer and Technical Documentation Architect for 'Nexus Hub'. 
> 
> **Task 1: Code Implementation (`scripts/deploy.sh`)**
> 1. **Delete Legacy File:** Ensure the old `update.sh` file from the root directory is explicitly deleted from the repository.
> 2. Create `scripts/deploy.sh`.
> 3. Add a `clasp push` section to sync the Apps Script UI locally.
> 4. Use `gcloud compute ssh` to execute a remote string on the VM: Pull git updates, activate venv, run `pip install`, execute `db_init.py` migrations, and `sudo systemctl restart nexus-hub`.
> 5. Use fail-fast error traps and color-coded `echo` feedback.
> 
> **Task 2: Continuous Documentation (`README.md` & `INSTRUCTIONS.md`)**
> * **Location:** Section 11. Infrastructure as Code (IaC).
> * **Action:** Add subsection `11.1 The One-Click Deployer`. Update `INSTRUCTIONS.md` to document this local one-click deployment architecture.
> 
> **Task 3: Roadmap Anchors & Version History**
> * **In `README.md`:** Add to Version History: `- **v2026.4.2.0:** [Epic 4.2](#epic-4-prompt-2) - Engineered the CI/CD deploy script integrating clasp and gcloud, officially deprecating legacy shell scripts.`
> 
> **Output Actions:**
> 1. Silently delete `update.sh`, create `scripts/deploy.sh`, and update documentation."

## EPIC 5: Post-Deployment Hardening & Cleanup (v5.x.x)
*Notice to AI: We are now executing Epic 5. Update the README version history to v5.x.x for the following prompts.*

<a id="epic-5-prompt-1"></a>
### Epic 5 - Prompt 1: Progressive Rollout (Feature Flags)
> "I am the Lead Architect. We have completed the core infrastructure (Epics 0-4) and are preparing for our first live cloud deployment. To ensure a safe, debuggable boot, we are implementing a Progressive Rollout (Feature Flag) architecture to explicitly gate the advanced pipelines we built previously.
> 
> **Task 1: The Configuration Layer (`db_init.py`)**
> 1. In the `seed_default_config()` function (or equivalent initialization), inject the following keys into `Config_System` with a default value of `'0'` (string representing disabled): `feature_retention_sweeper`, `feature_drive_relocator`, `feature_materialization`, `feature_google_tasks`.
> 
> **Task 2: The Execution Gatekeepers (`sync_engine.py` & `retention_worker.py`)**
> 1. Locate the execution calls for the advanced features: the retention worker daemon, the drive relocator logic, `materialize_artifact()`, and `push_to_google_tasks()`.
> 2. Wrap each of these functional blocks in a conditional check that queries `Config_System`.
> 3. If the corresponding flag equals `'0'`, use `logger.debug()` to print that the feature is bypassed due to Safe Mode, and `continue` or `return` safely.
> 
> **Task 3: The Control Panel UI (`Index.html` & `JS_Actions.html`)**
> 1. Add a 'System Toggles' section to the Settings modal (or Mission Control dashboard).
> 2. Create UI toggle switches for each of the 4 features. Wire them to fetch the current state on boot and update the `Config_System` table via the backend API when clicked.
> 
> **Task 4: Documentation & Versioning**
> 1. **In `README.md`:** Add to Version History: `- **v2026.5.1.0:** [Epic 5.1](#epic-5-prompt-1) - Implemented Progressive Rollout feature flags to safeguard the first-time cloud deployment.`
> 2. Update the deployment instructions in the README to explicitly state that the system boots in "Safe Mode" and features must be toggled on manually via the UI.
> 
> **Output Actions:**
> 1. Silently execute the code implementation across `db_init.py`, `sync_engine.py`, `retention_worker.py`, and the frontend UI.
> 2. Silently update `README.md` exactly as instructed."