# Nexus Dependency Trace

## Phase 1: Frontend Execution Trace

### Chain 1: Application Load
- `document.addEventListener("DOMContentLoaded")` (`Index.html:523`)
  -> Calls `appActions.init()` in `JS_Actions.html`
    -> Calls `appActions.loadUserPreferences()`
      -> Sends HTTP Request to `[API Endpoint: /api/settings/pipeline]` via `Code.gs: getUserPreferences()`
        -> Triggers `get_pipeline_settings()` in `main.py`
    -> Calls `appActions.loadPipelineSettings()`
      -> Sends HTTP Request to `[API Endpoint: /api/settings/pipeline]` via `Code.gs: getPipelineSettings()`
        -> Triggers `get_pipeline_settings()` in `main.py`
    -> Calls `appActions.loadQuotaGovernor()`
      -> Sends HTTP Request to `[API Endpoint: /api/health/quota]` via `Code.gs: getQuotaGovernor()`
        -> Triggers `get_health_quota()` in `main.py`
    -> Calls `appActions.startHealthPing()`
      -> Sends HTTP Request to `[API Endpoint: /api/health]` via `Code.gs: pingHealthAPI()`
        -> Triggers `health_check_get()` in `main.py`

### Chain 2: Run Diagnostics
- `div.nav-item` click (`Index.html:100`)
  -> Calls `appActions.triggerDiagnostics()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/health]` via `Code.gs: runSystemDiagnostics()`
      -> Triggers `health_check_post()` in `main.py`

### Chain 3: Render Heatmap
- `button` click (`Index.html:114`)
  -> Calls `appActions.renderHeatmap()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/analytics/heatmap]` via `Code.gs: getHeatmapData()`
      -> Triggers `analytics_heatmap()` in `main.py`
        -> Modifies `[None - Reads from Database]`

### Chain 4: Execute AST Search
- `omnibox` enter key (`JS_Actions.html:150`) or `heatmap` click (`JS_Actions.html:118`)
  -> Calls `appActions.executeASTSearch(query)` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/artifacts/search?q=...]` via `Code.gs: searchArtifacts()`
      -> Triggers `search_artifacts()` in `main.py`

### Chain 5: Safe Mode Toggle (Retention Sweeper)
- `input checkbox` change (`Index.html:69`)
  -> Calls `appActions.updateSafeMode('feature_retention_sweeper', this.checked)` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/settings/pipeline]` via `Code.gs: updateSafeMode()`
      -> Triggers `update_pipeline_settings()` in `main.py`
        -> Modifies `[Config_System Database]`

### Chain 6: Save Pipeline Config
- `button` click (`Index.html:357`)
  -> Calls `appActions.savePipelineSettings()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/settings/pipeline]` via `Code.gs: savePipelineSettings()`
      -> Triggers `update_pipeline_settings()` in `main.py`
        -> Modifies `[Config_System Database]`

### Chain 7: Queue Historical Import
- `button` click (`Index.html:222`)
  -> Calls `appActions.queueHistoricalImport()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/ingestion/queue-historical]` via `Code.gs: queueHistoricalImport()`
      -> Triggers `queue_historical()` in `main.py`
        -> Modifies `[Ingestion_Queue Database]`

### Chain 8: Bulk Edit / Submit Manual Review
- `button` click (`Index.html:240`, `Index.html:494`)
  -> Calls `appActions.bulkEdit()` / `appActions.submitManualReview()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/bulk-update]` via `Code.gs: bulkUpdateArtifacts()`
      -> Triggers `bulk_update_endpoint()` in `main.py`
        -> Modifies `[Workspace_Artifacts Database]`

### Chain 9: Materialize Selected Items
- `button` click (`Index.html:511`)
  -> Calls `appActions.materializeSelected()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/workflows/materialize]` via `Code.gs: materializeSelectedItems()`
      -> Triggers `materialize_items()` in `main.py`
        -> Modifies `[Workspace_Artifacts Database and Google Drive]`

### Chain 10: Refresh Analytics Dashboard
- `button` click (`Index.html:416`)
  -> Calls `appActions.renderAnalyticsDashboard()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/analytics/roi-dashboard]` via `Code.gs: getROIDashboard()`
      -> Triggers `roi_dashboard()` in `main.py`

### Chain 11: Ask AI Assistant
- `button` click (`Index.html:476`)
  -> Calls `appActions.askAI()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/ask]` via `Code.gs: runAskAI()`
      -> Triggers `ask_endpoint()` in `main.py`
        -> Sends Request to `[Gemini API]`

### Chain 12: Run Sandbox
- `button` click (`Index.html:332`)
  -> Calls `appActions.runSandbox()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/sandbox]` via `Code.gs: runSandboxPrompt()`
      -> Triggers `sandbox_endpoint()` in `main.py`
        -> Sends Request to `[Gemini API]`

### Chain 13: Save Entity Rules (Correspondents/Purposes)
- `button` click (`Index.html:307`, `Index.html:324`)
  -> Calls `appActions.saveCorrespondentRules()` / `appActions.savePurposeRules()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/entities/{entityType}/{id}]` via `Code.gs: updateEntityRules()`
      -> Triggers `update_correspondent()` / `update_purpose()` in `main.py`
        -> Modifies `[Taxonomy_Correspondents / Taxonomy_Purposes Database]`

### Chain 14: Submit Zero-Shot Rule
- `button` click (`JS_Actions.html:1089`)
  -> Calls `appActions.submitZeroShotRule()` in `JS_Actions.html`
    -> Sends HTTP Request to `[API Endpoint: /api/taxonomy/zero-shot-rule]` via `Code.gs: submitZeroShotRule()`
      -> Triggers `zero_shot_rule()` in `main.py`
        -> Modifies `[Taxonomy_Purposes Database]`


## Phase 2: Backend Execution Trace

### Chain 1: Initialization & Cron Jobs
- `@app.on_event("startup")` (`main.py:37`)
  -> Calls `start_cron_jobs()` in `main.py`
    -> Modifies `nexus.db` (via `db_init.init_db()`)
    -> Calls `initialize_drive_structure()` in `sync_engine.py`
      -> Modifies Google Drive (creates folder structure)
    -> Spawns `daily_digest()` background loop
      -> Calls `notifier.send_daily_digest(html_body)` in `notifier.py`
        -> Sends HTTP Request to `[Gmail API]`

### Chain 2: Queue Historical Ingestion
- `@app.post("/api/ingestion/queue-historical")` (`main.py:183`)
  -> Calls `queue_historical()` in `main.py`
    -> Sends HTTP Request to `[Gmail API]` via `service.users().messages().list()`
    -> Modifies `[Ingestion_Queue Database]`

### Chain 3: Materialization Pipeline
- `@app.post("/api/workflows/materialize")` (`main.py:223`)
  -> Calls `materialize_items()` in `main.py`
    -> Triggers `materialize_artifact(a_id)` in `sync_engine.py` (via BackgroundTasks)
      -> Modifies `[Google Drive]` and `[Workspace_Artifacts Database]`

### Chain 4: Zero-Shot Rule Generation
- `@app.post("/api/taxonomy/zero-shot-rule")` (`main.py:235`)
  -> Calls `zero_shot_rule()` in `main.py`
    -> Triggers `append_zero_shot_rule()` in `llm_engine.py`
      -> Modifies `[Taxonomy_Purposes Database]`

### Chain 5: Read-Only API Endpoints (Search, Mission Control, Heatmap, Threads, ROI)
- `@app.get("/api/artifacts/search")` (`main.py:253`)
- `@app.get("/api/dashboard/mission-control")` (`main.py:360`)
- `@app.get("/api/analytics/heatmap")` (`main.py:396`)
- `@app.get("/api/analytics/threads")` (`main.py:485`)
- `@app.get("/api/analytics/roi-dashboard")` (`main.py:597`)
- `@app.get("/api/health/quota")` (`main.py:918`)
  -> Call respective handler functions in `main.py`
    -> Read `[nexus.db Database]`

### Chain 6: Update Data (Prompt Tuning Feedback Loop)
- `@app.post("/api/update")` (`main.py:656`)
  -> Calls `update_data()` in `main.py`
    -> Triggers `generate_tuning_rule()` in `llm_engine.py` (via BackgroundTasks)
      -> Modifies `[Taxonomy_Correspondents / Taxonomy_Purposes Database]`

### Chain 7: Sandbox Execution
- `@app.post("/api/sandbox")` (`main.py:675`)
  -> Calls `sandbox_endpoint()` in `main.py`
    -> Triggers `run_sandbox_prompt()` in `llm_engine.py`
      -> Sends HTTP Request to `[Gemini API]`

### Chain 8: RAG Assistant
- `@app.post("/api/ask")` (`main.py:693`)
  -> Calls `ask_endpoint()` in `main.py`
    -> Triggers `ask_rag(question)` in `llm_engine.py`
      -> Sends HTTP Request to `[Gemini API]`
      -> Executes raw SQL against `[nexus.db Database]`

### Chain 9: Bulk Update
- `@app.post("/api/bulk-update")` (`main.py:709`)
  -> Calls `bulk_update_endpoint()` in `main.py`
    -> Modifies `[Workspace_Artifacts Database]`

### Chain 10: Settings & Entities Updates
- `@app.get("/api/settings/pipeline")` (`main.py:813`)
- `@app.post("/api/settings/pipeline")` (`main.py:843`)
- `@app.put("/api/entities/correspondents/{id}")` (`main.py:885`)
- `@app.put("/api/entities/purposes/{id}")` (`main.py:900`)
  -> Call respective handler functions in `main.py`
    -> Modifies `[Config_System, Taxonomy_Correspondents, Taxonomy_Purposes Database]`

### Chain 11: Trigger Retention Sweep
- `@app.post("/api/retention/sweep")` (`main.py:988`)
  -> Calls `trigger_retention_sweep()` in `main.py`
    -> Executes `subprocess` calling `retention_worker.py`
      -> Modifies `[nexus.db Database]` and `[Google Workspace APIs]`

### Chain 12: Sync Engine Worker (Background Execution Loop)
- External Cron/Daemon execution of `sync_engine.py`
  -> Calls `run_sync()` in `sync_engine.py`
    -> Calls `sync_gmail()` and `sync_drive()` in `sync_engine.py`
      -> Sends HTTP Requests to `[Gmail API]` and `[Drive API]`
      -> Triggers `process_gmail_thread()` and `process_drive_document()` in `llm_engine.py`
        -> Sends HTTP Request to `[Gemini API]`
      -> Modifies `[Workspace_Artifacts Database]`


## Phase 3: Orphans / Dead Code

- `Code.gs: getRetentionRules()` - Defined but never called from `JS_Actions.html` or `Index.html`.
- `Code.gs: addRetentionRule()` - Defined but never called from the UI.
- `Code.gs: deleteRetentionRule()` - Defined but never called from the UI.
- `Code.gs: triggerRetentionSweep()` - Defined but never called from the UI.
- `@app.get("/api/prompts")` in `main.py` - Endpoint exists but is never hit by the App Script frontend.
- `@app.post("/api/prompts")` in `main.py` - Endpoint exists but is never hit by the App Script frontend.
