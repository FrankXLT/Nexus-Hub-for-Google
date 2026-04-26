# Nexus Hub: Code Generation Prompt Roadmap

**Instructions for the Human Developer:** Do not paste this entire file into Gemini Code Assist at once. Treat this as a sequential playbook. 
1. Ensure `ARCHITECTURE.md` is open or referenced in your IDE chat context.
2. Paste **Stage 0** to anchor the agent. 
3. Wait for its acknowledgment. 
4. Proceed phase-by-phase, only moving to the next stage when the current code is perfect.

---

## Stage 0: The Context Anchor
**Goal:** Prevent the agent from generating unsolicited code while forcing it to digest the master architecture and the continuous documentation rules.

**Copy/Paste this to Gemini Code Assist:**
> "I am the Lead Architect, and you are my Junior Developer. We are building the 'Nexus Hub for Google'. Please read the `ARCHITECTURE.md` file in this repository to understand the master specification. 
>
> **Continuous Documentation Rules:** Throughout this project, you are responsible for maintaining three living documents alongside the code:
> 1. `PROMPT_AUDIT.md`: After every completed stage, you will log a summary of what was built, decisions made, and files altered. This acts as our recovery memory.
> 2. `README.md`: You will continuously update this with feature summaries, version history, and high-level architecture overviews as they are built.
> 3. `INSTRUCTIONS.md`: You will iteratively write the step-by-step user manual here, including exact GCP setup instructions, API enabling, Service Account creation, and deployment steps.
> 
> **CRITICAL INSTRUCTION:** Do NOT write any code yet. Your only task right now is to reply with exactly: 'Architecture digested and documentation rules acknowledged. I understand the hybrid Apps Script/GCP structure and my responsibility to maintain the Audit, Readme, and Instructions files. Awaiting Phase 1 instructions.'"

---

## Stage 1: Infrastructure & CI/CD
**Internal Simulation & Correction:** *Left to its own devices, the agent will write generic bash scripts, forget to install `clasp`, and write a destructive `update.sh` that wipes the SQLite database. The prompt below explicitly forces idempotency and safe Git pulling.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 1 based on Section 3 of ARCHITECTURE.md. Generate two bash scripts:
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

## Stage 2: Centralized SQLite Index 
**Internal Simulation & Correction:** *The agent will default to using SQLAlchemy (bloat) and standard SQLite tables. It will also likely format the `custom_data` columns as TEXT instead of JSON. The prompt below forces lightweight standard libraries and strict SQLite 3.37+ constraints.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 2 based on Section 5.2 of ARCHITECTURE.md. Write the Python initialization script (`db_init.py`) to create the `nexus.db` database.
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

## Stage 3: Python Webhook & HMAC Security Bridge
**Internal Simulation & Correction:** *The agent will frequently forget replay-attack protection, or it might hardcode secrets. It must be forced to use `python-dotenv` and explicit timestamp math.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 3 based on Section 6.2 and 9.2 of ARCHITECTURE.md. Write the FastAPI backend application (`main.py`) that will receive requests from Apps Script.
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

## Stage 4: Google Apps Script Backend (The Secure Router)
**Internal Simulation & Correction:** *The agent might hardcode the HMAC secret. This prompt forces the creation of a secure setup utility.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 4 based on Section 6.3 and 9.5 of ARCHITECTURE.md. Generate the `Code.gs` file.
> 
> **Strict Constraints:**
> 1. Write the `doGet(e)` function to serve `Index.html`.
> 2. Write a one-time setup function `configureHMAC(secretString)`. This function saves the string to `PropertiesService.getScriptProperties()`. Add a prominent comment telling the user to run this once and then delete the string from the editor.
> 3. Write `sendToNexusVM(endpoint, payload)`. It MUST pull the HMAC secret from `PropertiesService`, generate the HMAC-SHA256 signature natively, append a timestamp, and transmit via `UrlFetchApp.fetch()`.
> 4. Add a JSDoc comment explicitly warning that this function must only be called via `google.script.run` from the client-side.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md, README.md, and draft the Apps Script deployment steps in INSTRUCTIONS.md."

---

## Stage 5: Python Headless OAuth Bootstrapper
**Internal Simulation & Correction:** *The agent will assume it can open a local web browser to authenticate. It must be forced to write a headless-compatible OAuth flow.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 5. We need to build the authentication bridge for the Python VM to talk to Workspace APIs. Write an `auth.py` script.
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

## Stage 6: Isolated Health Checks & Diagnostic Logging
**Internal Simulation & Correction:** *The agent might try to log diagnostics into the main SQLite database, which defeats the purpose if the database is down. It must be forced to use Google Drive for isolated logging.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 6 based on Section 8.3 of ARCHITECTURE.md. We need to build the diagnostic suite to isolate points of failure.
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

## Stage 7: Delta Sync & Tenacity Backoff
**Internal Simulation & Correction:** *The agent will likely try to write a script that does a full folder scan `drive.files().list()`. It must be forced to use the `Changes.list` endpoint and the `tenacity` library for error handling.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 5 based on Section 4.1 and 4.3 of ARCHITECTURE.md. Write a Python module (`sync_engine.py`) that fetches changes from Google Drive and Gmail.
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

## Stage 8: The LLM Processing Engine
**Internal Simulation & Correction:** *The agent might try to use outdated Gemini SDKs or fail to parse the JSON outputs safely. It must be forced to use the latest `google-genai` SDK and implement structured output parsing.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 8 based on Section 4.2 and Section 9.3 of ARCHITECTURE.md. Write the `llm_engine.py` module to handle the batch processing and Gemini API interactions.
> 
> **Strict Constraints:**
> 1. Use the official Google GenAI SDK to interact with the Gemini models.
> 2. Implement the Two-Stage Triage logic for Google Drive and the Single-Pass logic for Gmail as defined in the architecture.
> 3. Inject the exact prompts from Section 9.3. 
> 4. **CRITICAL:** You must force the LLM to return `application/json` using the `response_mime_type` configuration, and you must wrap the JSON parsing (`json.loads`) in a `try/except` block to prevent crashes if the LLM hallucinates formatting.
> 5. If Stage 2 extraction succeeds, write the database `UPDATE` to `Workspace_Artifacts` and the `INSERT` to `Artifact_History`.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md and README.md. Detail any required Gemini API key configurations in INSTRUCTIONS.md."

---

## Stage 9: Frontend UI (Material Design & State)
**Internal Simulation & Correction:** *The agent might try to write a monolithic HTML file or use heavy external frameworks. It must be forced to use the separated Apps Script architecture and lightweight vanilla JS/CSS.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 9 based on Section 7 and Section 9.1 of ARCHITECTURE.md. We are returning to the Google Apps Script environment to build the frontend.
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

## Stage 10: Final Codebase & Architecture Audit
**Internal Simulation & Correction:** *Agents often suffer from 'context drift' by Stage 9 and may have silently dropped a constraint from Stage 2. This forces a complete retrospective sweep of the local directory against the master spec.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 10: The Final QA Audit. You have completed the primary build. You must now act as the Lead QA Engineer. 
> 
> **Tasks:**
> 1. Read the `PROMPT_AUDIT.md` to see what you previously claimed to build.
> 2. Scan the actual codebase you just generated (`.py`, `.gs`, `.html`, `.sh` files).
> 3. Cross-reference the actual codebase against the strict constraints outlined in `ARCHITECTURE.md`.
> 
> **Output:**
> Generate a new file named `ARCHITECTURE_AUDIT.md`. This file MUST contain the following sections:
> 
> - **1. File Manifest:** A list of every file generated and its current state.
> - **2. Security Compliance:** Verify explicitly if the HMAC-SHA256 signature is validating timestamps in `main.py`, and if `auth.py` is properly configured for a headless VM (no browser auto-open). Check if any secrets are hardcoded.
> - **3. Database Integrity Check:** Confirm that `db_init.py` includes the `STRICT` keyword on ALL tables, uses `PRAGMA journal_mode=WAL`, and enforces Foreign Keys.
> - **4. Resiliency Check:** Confirm that the Google API and Gemini API calls use the `tenacity` exponential backoff, and that JSON responses from Gemini are wrapped in safe `try/except` blocks.
> - **5. Discrepancies & Deviations:** Self-report any constraints from `ARCHITECTURE.md` that were missed, skipped, or implemented differently than requested.
> 
> Do not write any new application code during this stage. Only generate the `ARCHITECTURE_AUDIT.md` file."

## Stage 11: Database Utility Refactor (Audit Fix)
**Internal Simulation & Correction:** *The audit revealed the DB is returning tuples instead of dictionary-like objects. This prompt forces the implementation of `sqlite3.Row` across the connection layer.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 11. In your Architecture Audit, you noted a discrepancy regarding database connection factories. We need to fix this.
> 
> **Tasks:**
> 1. Update `db_init.py` (and any other files that establish a database connection, like `main.py`, `sync_engine.py`, or `llm_engine.py`).
> 2. Immediately after establishing `sqlite3.connect()`, you MUST set `conn.row_factory = sqlite3.Row`.
> 3. Refactor any existing `SELECT` queries in the codebase that rely on tuple indexing (e.g., `row[0]`) to use dictionary key indexing (e.g., `row['artifact_id']`).
> 
> **Post-Execution Documentation:** Append this fix to `PROMPT_AUDIT.md`."

## Stage 12: Visual Branding & Color Sync Engine
**Internal Simulation & Correction:** *The agent missed Section 2.2. It must be forced to write the algorithm that limits colors to the strict Gmail API hex palette and syncs them to Google Drive.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 12 based on Section 2.2 of ARCHITECTURE.md. We need to build the Programmatic Color Management system. Write a new Python module: `branding_engine.py`.
> 
> **Strict Constraints:**
> 1. The script must contain a hardcoded list/dictionary of the 35 specific background/text hex color pairs allowed by the Gmail API.
> 2. Write an algorithm that takes a requested brand color (e.g., from the `Taxonomy_Entities` table) and finds the closest matching allowed Gmail color pair using simple Euclidean distance in RGB color space.
> 3. Write a function `sync_workspace_colors()`. It must use the `google-api-python-client` to apply the matched color pair to the corresponding nested Label in Gmail.
> 4. It must then take that exact same hex color and apply it to the `folderColorRgb` property of the matching Google Drive nested folder.
> 
> **Post-Execution Documentation:** Append updates to PROMPT_AUDIT.md and README.md."

## Stage 13: Feature Audit & Regression Check
**Internal Simulation & Correction:** *When refactoring database logic (Stage 11), agents frequently miss isolated tuple indexes (e.g., `row[0]`) buried inside try/except blocks. For Stage 12, they often format the Drive API `folderColorRgb` payload incorrectly. This forces a surgical scan of those specific implementations.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 13: The Feature & Regression Audit. You must act as the Lead QA Engineer to verify the fixes implemented in Stages 11 and 12.
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

## Stage 14: Internal Documentation & Tooltip Generation
**Internal Simulation & Correction:** *The agent will likely write a generic, surface-level readme. It must be forced to act as a Technical Writer, creating a granular, module-by-module breakdown, extracting a structured JSON for the UI tooltips, and leaving explicit placeholders for the Lead Architect to insert visual diagrams.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 14 based on Section 7.4 of ARCHITECTURE.md. We need to generate the internal 'How It Works' documentation that will power the UI's Help Section and contextual tooltips. You must act as the Lead Technical Writer.
> 
> **Tasks:**
> 1. Read the finalized codebase (`sync_engine.py`, `llm_engine.py`, `main.py`, `Code.gs`, etc.).
> 2. Create a highly detailed `HOW_IT_WORKS.md` file explaining the exact lifecycle of a document from Google Drive ingestion to SQLite insertion, and the lifecycle of an email via Pub/Sub. 
> 3. **CRITICAL:** Wherever a complex flow occurs, you must leave an explicit placeholder for the Lead Architect to add a graphic. Format it exactly like this: `[MERMAID_DIAGRAM_PLACEHOLDER: Name of specific system flow]`.
> 4. Create a new file named `tooltips.json`. Extract every configurable parameter from the `Config_System` table and the UI Settings module. Write a concise, 1-2 sentence user-friendly explanation for each parameter to be used as a UI tooltip.
> 
> **Post-Execution Documentation:** Append this phase to `PROMPT_AUDIT.md`. Do not write any Mermaid code; leave the placeholders intact."

## Stage 15: Documentation Expansion & Correction
**Internal Simulation & Correction:** *The agent provided a highly summarized HOW_IT_WORKS.md and entirely skipped the tooltips.json requirement. This prompt acts as a Lead Architect reprimand, forcing deep technical expansion and completion of missing tasks.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 15. I have reviewed your `HOW_IT_WORKS.md` and you missed several critical architectural requirements from Section 7.4. 
> 
> **Tasks & Corrections:**
> 1. **You forgot `tooltips.json`.** You must extract every configurable parameter from the UI Settings and `Config_System` table and write a 1-2 sentence technical explanation for each in a new `tooltips.json` file.
> 2. **Expand `HOW_IT_WORKS.md`.** Your current draft is too high-level. You must append three entirely new sections to the document:
>    - **Section 3: The Exception Queue & Manual UI Overrides:** Explain exactly what happens when a document is flagged as 'Purpose/Review', how the Apps Script UI fetches it, how the HMAC cryptographic handshake secures the user's manual correction, and how that correction is appended to the `Artifact_History` timeline.
>    - **Section 4: The Tuning Loop (AI Self-Correction):** Explain how a user's manual override triggers the Bulk AI Correction loop to generate a new routing rule.
>    - **Section 5: Programmatic Color Management:** Explain how the dual-snapping Euclidean algorithm ensures WCAG contrast compliance and syncs hex codes between Gmail labels and Drive folders.
> 3. Leave `[MERMAID_DIAGRAM_PLACEHOLDER: The UI Cryptographic Handshake]` under Section 3.
> 
> **Post-Execution Documentation:** Ensure these expansions reflect the depth of our actual python/GS implementation."

## Stage 16: Telemetry, Normalization & Compose Hardening
**Internal Simulation & Correction:** *The agent needs to augment existing files (`db_init.py`, `llm_engine.py`) and create a new one (`docker-compose.yml`). We must ensure it doesn't accidentally wipe out the existing logic in those Python files, but strictly augments them.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 16 based on our architectural review for Telemetry and Hardening. You will be augmenting our existing codebase.
> 
> **Tasks:**
> 1. **Docker Compose:** Create a `docker-compose.yml` file. It must define the Python sync engine service, map a persistent volume for the `/data` directory (where `nexus.db` lives), load variables from `.env`, and implement a logging driver with `max-size: 10m` and `max-file: 3`.
> 2. **Database Updates:** Modify `db_init.py`. 
>    - Add a new `STRICT` table: `Error_Logs` with columns: `log_id` (PK), `timestamp`, `module_name`, `artifact_id` (FK, nullable), `error_message`, and `stack_trace` (JSON).
>    - Add a boolean column `locked_by_system` (default 0) to the `Workspace_Artifacts` table to prevent race conditions during sync.
> 3. **Taxonomy Normalization:** Update `llm_engine.py`. Before the LLM output is evaluated against the database whitelist, inject a pre-processing function to normalize common plural/misspelled tags (e.g., converting 'Receipts' -> 'Receipt'). If normalization fails and the tag still does not match the whitelist, aggressively enforce the 'Purpose/Review' exception fallback.
> 
> **Post-Execution Documentation:** Append these hardening updates to `PROMPT_AUDIT.md` and summarize the new telemetry architecture in `README.md`."