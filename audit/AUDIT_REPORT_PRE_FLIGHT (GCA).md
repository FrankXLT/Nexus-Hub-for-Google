# AUDIT_REPORT_PRE_FLIGHT (GCA)

## Phase 1 Findings: Bottom-Up Audit (Ground Floor to UI)

**1. Schema Check:**
- **Data Integrity:** The `db_init.py` schema for `Workspace_Artifacts` defines `purpose_id` as the foreign key connecting items to the `Taxonomy_Purposes` hierarchy. The SQL queries in `main.py` (`search_artifacts` and `analytics_threads`) and `llm_engine.py` (`process_gmail_thread`) accurately reflect these columns by correctly joining `Workspace_Artifacts` -> `Taxonomy_Purposes` -> `Taxonomy_Correspondents` via the `purpose_id`.
- **Ingestion_Queue / Config_System:** Both match expectations for queueing and key-value storage. 

**2. Execution Gatekeepers (Epic 5 Safe Mode):**
- **Broken Connection:** The four system toggles (`feature_retention_sweeper`, `feature_drive_relocator`, `feature_materialization`, `feature_google_tasks`) requested in Epic 5 are **completely missing** from the `seed_default_configs()` in `db_init.py`.
- **Missing Wrappers:** `sync_engine.py` and `retention_worker.py` do not contain the gatekeeping logic to check these `Config_System` flags. The functions execute without checking for Safe Mode bypass.

**3. Queue Resilience:**
- **Verified:** The `/api/ingestion/queue-historical` endpoint securely writes payload items to the `Ingestion_Queue` with a status of `'PENDING'`.
- **Verified:** `sync_engine.py` correctly queries `Ingestion_Queue` for `'PENDING'` items, transitions them to `'PROCESSING'`, processes them, and safely updates them to `'COMPLETE'` or `'FAILED'`.

**4. Worker Idempotency:**
- **Broken Connection (Schema Mismatch):** In `sync_engine.py`, the system attempts to check `artifact_data['google_task_id'] is None`. However, the `Workspace_Artifacts` table schema in `db_init.py` **does not have a `google_task_id` column**. This will throw a KeyError/SQLite Row error at runtime.
- **Broken Connection (Missing Function):** `sync_engine.py` attempts to call `push_to_google_tasks(creds, artifact_data, conn)`, but this function is neither defined in the file nor imported from anywhere else.

**5. API Routing (Orphaned Endpoints):**
- The following backend endpoints in `main.py` are orphaned and never correctly routed by `Code.gs` (Apps Script backend):
  - `GET /api/dashboard/mission-control`
  - `GET /api/analytics/heatmap`
  - `GET /api/analytics/threads`
  - `GET /api/analytics/roi-dashboard`
  - `GET & POST /api/prompts`
  - `GET, POST, DELETE /api/retention/rules`
  - `POST /api/retention/sweep`

---

## Phase 2 Findings: Top-Down Audit (UI to Ground Floor)

**1. The Sidebar & Toggles:**
- **Broken Path:** The requested 'System Toggles' for the 4 Epic 5 features (`feature_retention_sweeper`, etc.) do not exist in the UI (`Index.html` or `JS_Actions.html`). Only standard pipeline configuration and a 'Run Diagnostics' button exist. 

**2. The Omnibox & Chips:**
- **Verified:** Clicking the chips correctly injects AST syntax into the `#ast-input` omnibox. Pressing 'Enter' properly routes to `executeASTSearch()`, which triggers `searchArtifacts()` in `Code.gs` and sends a GET request to `/api/artifacts/search` with the `q`, `limit`, and `offset` variables successfully passed.

**3. The View Modifiers:**
- **Verified:** Clicking the view control buttons toggles DOM visibility via `switchWorkspaceView()`. It correctly renders `tab-grid` or `tab-threads` and successfully triggers `renderThreadsView()` for Sankey diagram generation.

**4. Card Interactions:**
- **Verified:** Selecting multiple cards bundles their IDs into `appState.selectedIds`. Clicking the "Submit with AI (Create Rule)" zero-shot button correctly bundles the IDs and text, pushing to `submitZeroShotRule()` -> `Code.gs` -> `POST /api/taxonomy/zero-shot-rule`. The backend endpoint properly delegates to `append_zero_shot_rule()` which saves to `Taxonomy_Purposes`.

**5. Lineage:**
- **Verified:** The DOM generation correctly checks if `artifact.parent_artifact_id` exists. If true, it renders the '🔗 PDF' lineage badge and adds the `.stacked` CSS class.

---

## Deployment Blockers (Prioritized)

1. **Google Tasks Crashes Sync Engine:** `sync_engine.py` calls an undefined `push_to_google_tasks()` function. Additionally, it queries `google_task_id`, which is completely missing from the SQLite schema (`db_init.py`). This will fatally crash the `sync_drive()` loop.
2. **Missing Backend Bridges (`Code.gs`):** The `JS_Actions.html` frontend calls `google.script.run` for multiple methods that do not exist in `Code.gs`: `getUserPreferences()`, `getHeatmapData()`, `getROIDashboard()`, `getThreadsData()`, and `pingHealthAPI()`. The UI will throw errors upon loading.
3. **Missing Epic 5 Safe Mode:** The requested system toggles (feature flags) are missing from the UI, the Database seed (`db_init.py`), and the worker execution wrappers (`sync_engine.py`, `retention_worker.py`). The system will bypass Safe Mode entirely upon boot.