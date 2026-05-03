# Nexus - Pre-Flight Static Analysis Audit Report
**Auditor**: Lead QA Architect (Gemini / Cline)
**Methodology**: Read-only, Strict Bi-Directional Traceability

## Executive Summary
This audit revealed **multiple critical Deployment Blockers** across schema integrity, safe mode guardrails, and API routing. The frontend UI contains several dead references to Google Apps Script functions that are not defined, causing silent failures or mocked fallbacks. The worker engine contains missing function definitions that will crash the background loop.

---

## PHASE 1: Bottom-Up Audit (Ground Floor to UI)

### 1. Schema Check
**Status: 🔴 DEPLOYMENT BLOCKER**
- The `Workspace_Artifacts` schema in `db_init.py` does **not** contain the `google_task_id` column.
- **SQL Queries Alignment:** The queries in `main.py` and `llm_engine.py` are generally accurate regarding schema columns like `purpose_id` and `custom_data`. However, the lack of `google_task_id` will cause fatal crashes when the background worker attempts to query it.

### 2. Execution Gatekeepers (Epic 5 Safe Mode)
**Status: 🔴 DEPLOYMENT BLOCKER**
- The four system toggles (`feature_retention_sweeper`, `feature_drive_relocator`, `feature_materialization`, `feature_google_tasks`) are entirely **missing** from `Config_System` in `db_init.py`.
- **Worker Logic:** `sync_engine.py` and `retention_worker.py` **do not** read these toggles. The execution logic is completely exposed and unguarded, meaning features cannot be bypassed or safely disabled.

### 3. Queue Resilience
**Status: 🟢 PASS**
- **Historical Import:** `POST /api/ingestion/queue-historical` successfully writes to the `Ingestion_Queue` table with `status = 'PENDING'`.
- **Sync Engine:** `sync_engine.py` properly queries pending tasks and updates them to `PROCESSING`, and subsequently `COMPLETE` or `FAILED`.

### 4. Worker Idempotency
**Status: 🔴 DEPLOYMENT BLOCKER**
- **Google Tasks Engine:** `sync_engine.py` correctly attempts to evaluate `action_required == 1`, but it checks for `artifact_data['google_task_id'] is None`. Since this column does not exist in the schema, it will raise a KeyError/SQLite error.
- **Missing Function:** The function `push_to_google_tasks(creds, artifact_data, conn)` is called but never defined or imported in `sync_engine.py`, ensuring a hard crash.

### 5. API Routing
**Status: 🟡 WARNING (Orphaned Endpoints)**
The following endpoints in `main.py` are exposed but **never called** by the frontend or workers (or are unreachably wired due to missing `Code.gs` links):
- `GET /api/dashboard/mission-control`
- `GET /api/analytics/heatmap` (Called by UI, but missing in Code.gs)
- `GET /api/analytics/threads` (Called by UI, but missing in Code.gs)
- `GET /api/analytics/roi-dashboard` (Called by UI, but missing in Code.gs)
- `POST /api/update`
- `GET /api/prompts`
- `POST /api/prompts`
- `GET /api/retention/rules`
- `POST /api/retention/rules`
- `DELETE /api/retention/rules/{rule_id}`
- `POST /api/retention/sweep`

---

## PHASE 2: Top-Down Audit (UI to Ground Floor)

### 1. Missing Apps Script Router Methods
**Status: 🔴 DEPLOYMENT BLOCKER**
`JS_Actions.html` initiates calls via `google.script.run` for several endpoints that simply do not exist in the `Code.gs` bridge. This causes the UI to fail silently or perpetually render mock data.
- **Missing in `Code.gs`:**
  - `getUserPreferences()` (Breaks boot routing)
  - `getHeatmapData()` (Breaks Mission Control)
  - `getThreadsData()` (Breaks Sankey Threads)
  - `getROIDashboard()` (Breaks Analytics)
  - `pingHealthAPI()` (Breaks the System Health badge ping loop)

### 2. User Experience & Dead Elements
**Status: 🟡 WARNING**
- The UI contains buttons for `Inbox Cleanup` and `Audit Timeline` but lacks full end-to-end integration for features like setting `retention rules` through the UI (the retention API endpoints exist in `main.py` but have no UI payload delivery method).
- Due to the broken `getUserPreferences()`, boot routing fails and defaults to the local fallback mechanism rather than reading true database state.

## Conclusion
The backend is largely functional but suffers from critical disconnects in the Google Tasks module and schema definitions. The front-end UI and `main.py` API layer are heavily decoupled because `Code.gs` failed to act as the complete bridge for Epic 3 implementations. **A thorough remediation pass is required before going live.**
