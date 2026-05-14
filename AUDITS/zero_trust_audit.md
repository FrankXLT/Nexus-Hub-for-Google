# Master Tracemap Audit: Nexus for Google

## 1. File Structure (Backend)

```text
C:\USERS\FRANK\GITHUB\NEXUS-FOR-GOOGLE\BACKEND
├── auth.py
├── branding_engine.py
├── db_init.py
├── db_mapper.py
├── diagnostics.py
├── llm_engine.py
├── main.py
├── notifier.py
├── patch.py
├── patch_sync.py
├── requirements.txt
├── retention_worker.py
├── sync_engine.py
└── update_llm.py
```

## 2. Function Level (Core Python Functions)

*   **`auth.py`**
    *   `authenticate()`: Manages headless OAuth 2.0 flow and token refresh.
*   **`branding_engine.py`**
    *   `hex_to_rgb()`: Converts hex strings to RGB tuples.
    *   `color_distance()`: Euclidean distance calculation for color matching.
    *   `get_closest_gmail_color()`: Matches custom hex to Google's allowed color palette.
    *   `sync_workspace_colors()`: Propagates matching colors to Drive folders and Gmail labels.
*   **`db_init.py`**
    *   `init_db()`: Initializes DB with explicit WAL mode, STRICT tables, and zero-trust schema rules.
    *   `seed_default_configs()`, `seed_default_taxonomy()`, `seed_default_prompts()`: Core data seeders.
*   **`db_mapper.py`**
    *   `generate_report()`: Auto-generates a Markdown/Mermaid database architecture report.
*   **`diagnostics.py`**
    *   `check_database()`, `check_oauth_token()`, `check_api_health()`: Core diagnostic runners.
    *   `upload_diagnostic_log()`: Securely uploads health reports to Google Drive.
    *   `run_all_diagnostics()`: Orchestrator that compiles results and triggers notifications.
*   **`llm_engine.py`**
    *   `fetch_active_prompt()`, `get_genai_client()`, `call_gemini()`: Core API integration routines.
    *   `process_gmail_thread()`: Single-pass AI ingestion for Gmail.
    *   `process_drive_document()`: Two-stage triage and taxonomy mapping for Drive OCR documents.
    *   `ask_rag()`: Natural language text-to-SQL logic block over `Workspace_Artifacts`.
    *   `run_agent_profiler()`, `run_agent_classifier()`: Specific AI agents for zero-trust evaluations.
    *   `append_zero_shot_rule()`, `generate_tuning_rule()`: Iterative prompt self-improvement logic.
    *   `persist_llm_results()`: Hardened function for DB mutation tracking.
*   **`main.py`**
    *   `verify_nexus_signature()`: Crucial middleware enforcing HMAC-SHA256 verification and replay protection on API endpoints.
    *   `start_cron_jobs()`: Startup initialization for background loops.
*   **`notifier.py`**
    *   `send_urgent_webhook()`: Broadcasts priority alerts out of the system.
    *   `send_daily_digest()`: Aggregates errors/quarantined items and emails a digest to the user.
*   **`retention_worker.py`**
    *   `run_retention_sweep()`: Executes rule-based actions (Archive/Trash) on old messages based on `Config_Retention_Rules`.
*   **`sync_engine.py`**
    *   `QuotaGovernor`: Class to enforce Google API request budgets and 72-Hour priority lanes.
    *   `run_sync()`: Orchestrates standard fetch loops against Contacts, Drive, and Gmail.
    *   `sync_contacts_pipeline()`, `sync_gmail_pipeline()`, `sync_drive_pipeline()`: Zero Trust "Swimlane" implementations processing data through the Agent profiles.
    *   `materialize_artifact()`: Orchestrates turning raw/HTML inputs into hardened Google Drive PDFs.

## 3. API Layer (FastAPI Endpoints in `main.py`)

*   **Ingestion & Workflows**
    *   `POST /api/ingestion/queue-historical`: Queues historical email syncs.
    *   `POST /api/workflows/materialize`: Re-formats transient data into static materialized PDFs.
    *   `POST /api/bulk-update`: Handles bulk metadata modifications and issues history audits.
    *   `POST /api/update`: Secure internal webhook receiver for single artifact modifications.
*   **Search & Discovery**
    *   `GET /api/artifacts/search`: Parses search ASTs (e.g. `!purpose:"Spam"`) into parameterized SQL queries.
    *   `POST /api/ask`: Natural Language RAG QA interface.
*   **Taxonomy & AI Tuning**
    *   `POST /api/taxonomy/zero-shot-rule`: Appends instruction sets to purpose schemas.
    *   `POST /api/taxonomy/discover`: Injects dynamically discovered edge nodes into the database.
    *   `GET/POST /api/taxonomy/blacklist`: Configures hard blocks (domains/purposes).
    *   `PUT /api/entities/correspondents/{id}`, `PUT /api/entities/purposes/{id}`: Manual override interfaces for classification rules.
    *   `GET/POST /api/prompts`: CRUD endpoints for system master templates.
*   **Settings & Retention**
    *   `GET/POST /api/settings/pipeline`: Manages global Safe Mode flags and AI context overrides.
    *   `GET/POST/DELETE /api/retention/rules`, `POST /api/retention/sweep`: Full management layer for sweeping operations.
*   **Dashboards & Analytics**
    *   `GET /api/dashboard/mission-control`: Base system KPIs (Total, Required Action, Quarantine).
    *   `GET /api/analytics/heatmap`: Volumetric mapping of items over `X` months.
    *   `GET /api/analytics/threads`: Deep node mapping.
    *   `GET /api/analytics/roi-dashboard`: Aggregates model First-Pass accuracy and Token usage metrics.
    *   `GET /api/analytics/taxonomy`: Sankey/flow mapping nodes across the system.
    *   `GET /api/taxonomy/flow`: View categories & purposes mapping.
*   **Health & Status**
    *   `GET/POST /api/health`: Executes system-wide validations.
    *   `GET /api/health/quota`: Fetch daily tracked Quota Governor API limits.

## 4. Database Layer (SQLite `nexus.db`)

*   **System & Orchestration Tables**
    *   `Config_System`: Global KV store, holds Safe Mode toggles and quota tracking.
    *   `Sync_State`: Enforces strict delta-sync state mapping per API module (`drive`, `gmail`).
    *   `Config_Prompts`: In-DB storage for real-time modifiable LLM system prompts.
    *   `Config_Retention_Rules`: Defines age-based rules for mailbox sweeps.
*   **Taxonomy & Zero Trust Directory**
    *   `categories`: High-level nodes (e.g., 'Finance', 'Personal').
    *   `entities`: System edge nodes. Enhanced with `nexus_state` to track linkage properties.
    *   `purposes`: Actionable intents mapped to entities, defining scopes ('Universal', 'Categorical').
    *   `blacklist`: Deny-list table tracking domain strings or purpose strings.
*   **Data Pipelines**
    *   `Workspace_Artifacts`: The master data index representing real-time system state per document.
    *   `Artifact_History`: An immutable append-only ledger tracking all actions taken by humans or AI.
    *   `Ingestion_Queue`: A highly active queue system tracking processing status of historical backlogs.
    *   `quarantine_queue`: Holds untested/untrusted data inputs until explicit admin classification is confirmed (Zero Trust verification).
    *   `Error_Logs`: The Dead Letter Queue capturing Python stack traces.

## 5. Active Scripts/Workers

*   **Periodic Sync Thread (`run_sync`)**: Triggered in `main.py`'s background task every 3600 seconds. Manages polling `drive` and `gmail` while rigorously tracking limits inside the `QuotaGovernor`.
*   **Daily Digest Thread (`daily_digest`)**: Triggered in `main.py`'s background task every 86400 seconds. Collects data from the Dead Letter Queue and `quarantine_queue` and emails a consolidated HTML report to the user.
*   **Retention Sweeper (`run_retention_sweep`)**: Explicit execution worker (`retention_worker.py`) that applies the configured label sweeps across the Gmail account.

## 6. AI Protocols (Rules & Constraints)

The overarching rules discovered inside the workspace markdown (`AI_INSTRUCTIONS.md`, `INSTRUCTIONS.md`, `CONTRIBUTING.md`, `FEATURE_TRACKING.md`, `DEBUGGING.md`) dictate the following operational constraints:

1.  **Branching & The Vault:**
    *   Active development strictly occurs on the `development` branch.
    *   `main` branch acts as the protected "Vault" and requires pull requests merged down from `pre-release`.
2.  **Tracking & State Management:**
    *   AI implementations MUST document changes in `FEATURE_TRACKING.md` using a strict Two-Column markdown table structure (`Prompts or Strategy` & `Prompt Audit or Author Summary`).
    *   When an AI executes pull requests, it is responsible for calculating Semantic Version bumps and parsing Git history into a formatted `CHANGELOG.md`.
3.  **Idempotency & Database Integrity:**
    *   The backend database utilizes SQLite WAL mode.
    *   All database manipulations (schemas or data scripts) MUST be completely idempotent (safe to retry infinitely).
    *   Mutating queries must be explicitly wrapped in `BEGIN TRANSACTION;` and `COMMIT;` blocks.
4.  **Operational Security (Execution Approvals):**
    *   While read-only commands (e.g., `grep`, `cat`) are permitted freely, the AI is STRICTLY forbidden from executing destructive actions (e.g., git commit history manipulations, schema drops, remote pushes) without explicit presentation to and authorization from the Human user.
5.  **Hotfix Workflow:**
    *   Production fixes bypass standard workflows by being branched off `main` as `hotfix-[version]`, then must be recursively merged back down to `pre-release` and `development` to ensure parity.
6.  **AI Coding Conventions:**
    *   Conventional commits must be used on every commit (`feat:`, `fix:`, `chore:`, etc.).
    *   Lazy coding (such as truncating outputs with `// ... rest of the code`) is explicitly banned. Valid snippets and full files are required.