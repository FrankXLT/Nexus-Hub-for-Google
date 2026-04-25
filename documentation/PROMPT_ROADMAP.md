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

## Stage 6: Python Headless OAuth Bootstrapper
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

## Stage 7: Isolated Health Checks & Diagnostic Logging
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

## Stage 8: Delta Sync & Tenacity Backoff
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
