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

## Stage 17: The Master Documentation Rewrite
**Internal Simulation & Correction:** *The agent previously generated a superficial HOW_IT_WORKS.md. This prompt forces a complete rewrite, demanding extreme technical depth, procedural step-by-step lifecycles, and the inclusion of the UI data retrieval flow.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 17. Your previous draft of `HOW_IT_WORKS.md` was too high-level and took shortcuts. You must act as a Senior Technical Writer and completely rewrite `HOW_IT_WORKS.md` from scratch. 
> 
> **Strict Content Requirements:**
> 1. **System Overview:** Begin with a brief summary of the hybrid architecture.
> 2. **The Google Drive Pipeline (Deep Dive):** Break this down into 4 explicit procedural phases: (1) Ingestion & OCR Strip-down, (2) Triage & Routing Queue, (3) Threshold Batching & Extraction, (4) Archival & Exception Handling. Leave placeholder: `[MERMAID_DIAGRAM: Advanced Drive Pipeline]`.
> 3. **The Gmail Pipeline (Deep Dive):** Detail the single-pass extraction, Pub/Sub trigger vs. Polling fallback, and labeling sequence. Leave placeholder: `[MERMAID_DIAGRAM: Gmail Pub/Sub Flow]`.
> 4. **UI Data Retrieval & Presentation:** Create a new section detailing how the Material UI actually gets its data. Explain the `google.script.run` trigger, the HMAC secured GET request to the VM, the SQLite dictionary row fetching, and how the frontend `JS_State.html` handles the JSON payload to render the Split-Pane view without page reloads. Leave placeholder: `[MERMAID_DIAGRAM: UI Data Flow]`.
> 5. **Error Routing & Dead-Letter Queue:** Detail how Stage 16's `Error_Logs` table and `locked_by_system` booleans manage race conditions and API failures.
> 
> **Formatting:** Use bolding, numbered lists, and sub-headers. Do not summarize. Explain the *why* and *how* for every step. Do not write Mermaid code, only leave the exact placeholders requested."

## Stage 18: Container Dependency & Dockerfile Fix
**Internal Simulation & Correction:** *The agent documented a manual `pip install` on the host VM, violating the containerization architecture. It must generate a Dockerfile and requirements.txt to isolate the Python environment.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 18. I reviewed your INSTRUCTIONS.md and discovered a critical architectural violation. In Phase 8, you instruct the user to manually run `pip install google-genai` on the VM. This violates our strict Docker containerization constraint (Section 3.4).
> 
> **Tasks & Corrections:**
> 1. **Create `requirements.txt`:** Generate this file including all required Python libraries with strict versions (e.g., `fastapi`, `uvicorn`, `google-api-python-client`, `google-auth-oauthlib`, `tenacity`, `python-dotenv`, `google-genai`).
> 2. **Create `Dockerfile`:** Write a Dockerfile using `python:3.11-slim`. It must copy the repository files, install the `requirements.txt` via pip, and set the entrypoint to run the FastAPI `uvicorn` server from `main.py`.
> 3. **Update `docker-compose.yml`:** Ensure the compose file is configured to `build: .` from the new Dockerfile rather than using a raw python image.
> 4. **Fix `INSTRUCTIONS.md`:** Delete the manual `pip install` instructions. Update the manual to explain that Docker Compose will automatically build the image and install the Python dependencies.
> 
> **Post-Execution Documentation:** Append this containerization fix to `PROMPT_AUDIT.md`."

## Stage 19: Dynamic Prompt Extraction & Seeding
**Internal Simulation & Correction:** *The AI likely hardcoded the master prompts directly into `llm_engine.py` during Phase 8. This violates the goal of allowing users to update prompts via the UI. We must refactor the engine to fetch prompts dynamically from the `Config_Prompts` table and ensure this architectural shift is documented.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 19. We have an architectural flaw regarding how AI prompts are stored. Currently, the prompts from Section 9.3 are likely hardcoded in `llm_engine.py`. They must be fully database-driven so the user can update them later.
> 
> **Tasks:**
> 1. **Update `db_init.py` (Seeding):** Write a new function `seed_default_prompts(conn)`. This function must safely `INSERT OR IGNORE` the master prompts (from Section 9.3: Gmail Single-Pass, Drive Stage 1, Drive Stage 2) into the `Config_Prompts` table so the database is pre-loaded on the first boot.
> 2. **Refactor `llm_engine.py`:** Delete the hardcoded prompt strings. Write a helper function `fetch_active_prompt(prompt_key)` that queries the `Config_Prompts` table. 
> 3. **Dynamic Injection:** Ensure the routing and extraction functions in `llm_engine.py` call `fetch_active_prompt()` to retrieve their instructions *immediately before* making the call to the Gemini API.
> 4. **Update `main.py`:** Ensure the FastAPI server has a `GET /api/prompts` and `POST /api/prompts` endpoint (secured with the HMAC signature) so the Apps Script frontend can read and update these prompts in the database later.
> 5. **Update `HOW_IT_WORKS.md`:** Add a new sub-section under the LLM Engine explaining this dynamic prompt architecture. Explain how prompts are fetched from the database in real-time, allowing users to modify AI behavior without requiring a Docker container restart.
> 
> **Post-Execution Documentation:** Append this refactor to `PROMPT_AUDIT.md`."

---

## Stage 20: The AI Self-Tuning Engine (Feedback Loop)
**Internal Simulation & Correction:** *The system currently accepts manual UI corrections but does not use them to tune the LLM. We must build an asynchronous tuning loop that analyzes the error and updates the `Config_Prompts` table without blocking the UI's HTTP response, and document this technical mechanism.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 20 based on Section 9.3.4 (The Tuning Loop) of ARCHITECTURE.md. We need to implement the AI Self-Correction engine.
> 
> **Tasks:**
> 1. **Create the Tuning Logic:** In `llm_engine.py`, write a new asynchronous function `generate_tuning_rule(artifact_id, original_json, corrected_json)`. 
>    - This function must fetch the `raw_text` for the artifact from the database.
>    - It must send the raw text, the AI's original mistake, and the user's correction to the Gemini model using the precise prompt structure defined in Section 9.3.4.
>    - It must extract the generated `new_routing_rule` from Gemini's JSON response and append it to the existing prompt string in the `Config_Prompts` table for that specific Correspondent.
> 2. **Wire the Webhook:** Modify the `POST /api/update` endpoint in `main.py`. When a user submits a manual override, the API must return the `200 OK` response to the frontend immediately, but use FastAPI's `BackgroundTasks` to execute `generate_tuning_rule()` asynchronously in the background.
> 3. **Update `HOW_IT_WORKS.md`:** Review Section 4 (The Tuning Loop). Add a paragraph explicitly detailing the technical implementation: explain how FastAPI `BackgroundTasks` are used to process the Gemini AI tuning request asynchronously, ensuring the manual override webhook returns a 200 OK immediately to keep the UI snappy.
> 
> **Post-Execution Documentation:** Append this self-learning engine implementation to `PROMPT_AUDIT.md`."

## Stage 21: The Master Project Audit & Documentation Alignment
**Internal Simulation & Correction:** *By this stage, the agent has generated thousands of lines of code and documentation. It may have orphaned features or out-of-sync documents. This prompt forces a holistic reconciliation, demanding that it verify the implementation of the hardest features (dynamic prompts, tuning loop, containerization) and ensure the user manuals reflect the absolute final state.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute Phase 21: The Master Project Audit. You must now act as the Lead QA Engineer and Lead Technical Writer. We are preparing for the V1.x production release.
> 
> **Tasks:**
> 1. **Cross-Reference Roadmap vs. Audit:** Read `PROMPT_AUDIT.md`. Verify that Stages 1 through 20 have been executed. Specifically, confirm that the features from our late-stage pivots (Stage 18 Containerization, Stage 19 Dynamic Prompts, Stage 20 Async Tuning Loop) are actually present in the `.py` files, not just in your memory.
> 2. **Codebase vs. Architecture Check:** Scan the codebase to ensure no strict constraints were violated:
>    - Are there any hardcoded Gemini prompts left in `llm_engine.py`? (They should be fetched from the DB).
>    - Does `update.sh` correctly execute database migrations and restart Docker?
>    - Are `fastapi` and `BackgroundTasks` properly handling the async tuning loop in `main.py`?
> 3. **Documentation Alignment:** Review `README.md`, `INSTRUCTIONS.md`, and `HOW_IT_WORKS.md`. 
>    - Ensure `INSTRUCTIONS.md` clearly explains how Docker Compose handles the Python dependencies (no manual `pip install`).
>    - Ensure the `README.md` features list includes the Dead-Letter Queue, Dynamic Prompts, and the Self-Tuning Engine.
> 
> **Output:**
> 1. If you find any broken code or missing documentation constraints during this scan, silently fix them in the respective files.
> 2. Generate a final section at the bottom of `ARCHITECTURE_AUDIT.md` titled '## 7. V1.0 Master Release Audit'.
> 3. In this section, provide a Pass/Fail checklist for the 20 Stages, confirm the documentation is fully synced, and declare the codebase Ready for Production."

## Revised Stage 21: The Final Codebase Verification
**Internal Simulation & Correction:** *By this stage, the AI has generated extensive code, but the Lead Architect has manually taken over the documentation. This prompt restricts the agent strictly to a codebase audit to ensure the late-stage features (dynamic prompts, async webhook, and containerized migrations) actually exist in the `.py` and `.sh` files without risking further documentation corruption.*

**Copy/Paste this to Gemini Code Assist:**
> "Let's execute a revised Phase 21: The Final Codebase Verification. The Lead Architect has already manually polished the documentation suite. Your only job is to audit the Python codebase to ensure our latest features were implemented safely and correctly.
> 
> **Tasks:**
> 1. **Verify Dynamic Prompts:** Scan `llm_engine.py`. Confirm that `fetch_active_prompt()` is being actively used to query the `Config_Prompts` table. If there are any massive, hardcoded prompt strings still lingering in the file, delete them and replace them with the dynamic fetch call.
> 2. **Verify Async Tuning:** Scan `main.py`. Confirm that `BackgroundTasks` from `fastapi` is imported and utilized in the `/api/update` webhook endpoint to trigger the `generate_tuning_rule` function asynchronously. 
> 3. **Verify Containerization:** Scan `update.sh`. Ensure that any database migrations are executed *inside* the docker container (e.g., `docker compose run --rm nexus-api python3 db_init.py`) rather than directly on the host VM.
> 
> **Output:**
> 1. If you find any missing logic, silently patch the respective `.py` or `.sh` files now.
> 2. Append 'Phase 21: Final Codebase Verification' to `PROMPT_AUDIT.md`, logging that you verified the dynamic prompts, async webhook, and dockerized execution. Do not alter any other markdown files."