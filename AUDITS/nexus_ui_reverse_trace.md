# Nexus UI Reverse Trace

## UI Element: Sidebar Menu Toggle
- **HTML:** `<button class="menu-toggle" onclick="toggleSidebar()">` (`Index.html:19`)
  -> **JS:** Calls `toggleSidebar()` in `JS_Actions.html` (DOM Only)

## UI Element: Tab Navigation (Mission Control)
- **HTML:** `<div class="nav-item" onclick="appState.switchTab('mission-control', event)">` (`Index.html:26`)
  -> **JS:** Calls `switchTab()` in `JS_State.html` (DOM Only)

## UI Element: Epic 5 Safe Mode Toggle (Retention Sweeper)
- **HTML:** `<input type="checkbox" id="toggle-retention" onchange="appActions.updateSafeMode('feature_retention_sweeper', this.checked)">` (`Index.html:73`)
  -> **JS:** Calls `updateSafeMode()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.updateSafeMode()`
      -> **Code.gs:** `updateSafeMode()` executes `UrlFetchApp` to `/api/settings/pipeline`
        -> **FastAPI:** `@app.post("/api/settings/pipeline")` in `main.py`
          -> **Engine:** Calls `update_pipeline_settings()` in `main.py`

## UI Element: Epic 5 Safe Mode Toggle (Drive Relocator)
- **HTML:** `<input type="checkbox" id="toggle-relocator" onchange="appActions.updateSafeMode('feature_drive_relocator', this.checked)">` (`Index.html:80`)
  -> **JS:** Calls `updateSafeMode()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.updateSafeMode()`
      -> **Code.gs:** `updateSafeMode()` executes `UrlFetchApp` to `/api/settings/pipeline`
        -> **FastAPI:** `@app.post("/api/settings/pipeline")` in `main.py`
          -> **Engine:** Calls `update_pipeline_settings()` in `main.py`

## UI Element: Epic 5 Safe Mode Toggle (Materialization)
- **HTML:** `<input type="checkbox" id="toggle-materialization" onchange="appActions.updateSafeMode('feature_materialization', this.checked)">` (`Index.html:87`)
  -> **JS:** Calls `updateSafeMode()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.updateSafeMode()`
      -> **Code.gs:** `updateSafeMode()` executes `UrlFetchApp` to `/api/settings/pipeline`
        -> **FastAPI:** `@app.post("/api/settings/pipeline")` in `main.py`
          -> **Engine:** Calls `update_pipeline_settings()` in `main.py`

## UI Element: Epic 5 Safe Mode Toggle (Google Tasks)
- **HTML:** `<input type="checkbox" id="toggle-tasks" onchange="appActions.updateSafeMode('feature_google_tasks', this.checked)">` (`Index.html:94`)
  -> **JS:** Calls `updateSafeMode()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.updateSafeMode()`
      -> **Code.gs:** `updateSafeMode()` executes `UrlFetchApp` to `/api/settings/pipeline`
        -> **FastAPI:** `@app.post("/api/settings/pipeline")` in `main.py`
          -> **Engine:** Calls `update_pipeline_settings()` in `main.py`

## UI Element: Run Diagnostics
- **HTML:** `<div class="nav-item" onclick="appActions.triggerDiagnostics()">` (`Index.html:100`)
  -> **JS:** Calls `triggerDiagnostics()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.runSystemDiagnostics()`
      -> **Code.gs:** `runSystemDiagnostics()` executes `UrlFetchApp` to `/api/health`
        -> **FastAPI:** `@app.post("/api/health")` in `main.py`
          -> **Engine:** Calls `health_check_post()` in `main.py`

## UI Element: Refresh Heatmap
- **HTML:** `<button class="btn btn-primary" onclick="appActions.renderHeatmap()">` (`Index.html:114`)
  -> **JS:** Calls `renderHeatmap()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.getHeatmapData()`
      -> **Code.gs:** `getHeatmapData()` executes `UrlFetchApp` to `/api/analytics/heatmap`
        -> **FastAPI:** `@app.get("/api/analytics/heatmap")` in `main.py`
          -> **Engine:** Calls `analytics_heatmap()` in `main.py`

## UI Element: Interactive Search Chips
- **HTML:** `<button class="chip" onclick="toggleChip(this, 'Purpose:Receipt')">` (`Index.html:176`)
  -> **JS:** Calls `toggleChip()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.searchArtifacts()`
      -> **Code.gs:** `searchArtifacts()` executes `UrlFetchApp` to `/api/artifacts/search`
        -> **FastAPI:** `@app.get("/api/artifacts/search")` in `main.py`
          -> **Engine:** Calls `search_artifacts()` in `main.py`

## UI Element: Refresh Data (Knowledge Grid)
- **HTML:** `<button class="btn btn-primary" onclick="appActions.refreshData()">` (`Index.html:211`)
  -> **[BROKEN LINK]:** `refreshData()` in `JS_Actions.html` uses mock data and never calls `google.script.run`!

## UI Element: Queue Historical Import
- **HTML:** `<button class="btn btn-primary" onclick="appActions.queueHistoricalImport()">` (`Index.html:222`)
  -> **JS:** Calls `queueHistoricalImport()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.queueHistoricalImport()`
      -> **Code.gs:** `queueHistoricalImport()` executes `UrlFetchApp` to `/api/ingestion/queue-historical`
        -> **FastAPI:** `@app.post("/api/ingestion/queue-historical")` in `main.py`
          -> **Engine:** Calls `queue_historical()` in `main.py`

## UI Element: Filter Select Dropdowns
- **HTML:** `<select id="filter-category" onchange="appActions.onCategoryChange()">` (`Index.html:228`)
  -> **JS:** Calls `onCategoryChange()` in `JS_Actions.html` (DOM Only)

## UI Element: Bulk Edit Selected
- **HTML:** `<button class="btn btn-secondary" onclick="appActions.bulkEdit()">` (`Index.html:240`)
  -> **JS:** Calls `bulkEdit()` in `JS_Actions.html` (DOM Only - Opens Modal)

## UI Element: Refresh Data (Zero-Trust Queue)
- **HTML:** `<button class="btn btn-primary" onclick="appActions.refreshData()">` (`Index.html:268`)
  -> **[BROKEN LINK]:** `refreshData()` in `JS_Actions.html` uses mock data and never calls `google.script.run`!

## UI Element: Save Correspondent Rules
- **HTML:** `<button class="btn btn-primary" onclick="appActions.saveCorrespondentRules()">` (`Index.html:307`)
  -> **JS:** Calls `saveCorrespondentRules()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.updateEntityRules()`
      -> **Code.gs:** `updateEntityRules()` executes `UrlFetchApp` to `/api/entities/{entityType}/{id}`
        -> **FastAPI:** `@app.put("/api/entities/correspondents/{id}")` in `main.py`
          -> **Engine:** Calls `update_correspondent()` in `main.py`

## UI Element: Save Purpose Rules
- **HTML:** `<button class="btn btn-primary" onclick="appActions.savePurposeRules()">` (`Index.html:324`)
  -> **JS:** Calls `savePurposeRules()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.updateEntityRules()`
      -> **Code.gs:** `updateEntityRules()` executes `UrlFetchApp` to `/api/entities/{entityType}/{id}`
        -> **FastAPI:** `@app.put("/api/entities/purposes/{id}")` in `main.py`
          -> **Engine:** Calls `update_purpose()` in `main.py`

## UI Element: Run Sandbox
- **HTML:** `<button class="btn btn-primary" onclick="appActions.runSandbox()">` (`Index.html:332`)
  -> **JS:** Calls `runSandbox()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.runSandboxPrompt()`
      -> **Code.gs:** `runSandboxPrompt()` executes `UrlFetchApp` to `/api/sandbox`
        -> **FastAPI:** `@app.post("/api/sandbox")` in `main.py`
          -> **Engine:** Calls `sandbox_endpoint()` in `main.py` -> `run_sandbox_prompt()` in `llm_engine.py`

## UI Element: Save Pipeline Config
- **HTML:** `<button class="btn btn-primary" onclick="appActions.savePipelineSettings()">` (`Index.html:357`)
  -> **JS:** Calls `savePipelineSettings()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.savePipelineSettings()`
      -> **Code.gs:** `savePipelineSettings()` executes `UrlFetchApp` to `/api/settings/pipeline`
        -> **FastAPI:** `@app.post("/api/settings/pipeline")` in `main.py`
          -> **Engine:** Calls `update_pipeline_settings()` in `main.py`

## UI Element: Refresh Analytics Dashboard
- **HTML:** `<button class="btn btn-primary" onclick="appActions.renderAnalyticsDashboard()">` (`Index.html:416`)
  -> **JS:** Calls `renderAnalyticsDashboard()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.getROIDashboard()`
      -> **Code.gs:** `getROIDashboard()` executes `UrlFetchApp` to `/api/analytics/roi-dashboard`
        -> **FastAPI:** `@app.get("/api/analytics/roi-dashboard")` in `main.py`
          -> **Engine:** Calls `roi_dashboard()` in `main.py`

## UI Element: Send AI Query
- **HTML:** `<button class="btn btn-primary" onclick="appActions.askAI()">` (`Index.html:476`)
  -> **JS:** Calls `askAI()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.runAskAI()`
      -> **Code.gs:** `runAskAI()` executes `UrlFetchApp` to `/api/ask`
        -> **FastAPI:** `@app.post("/api/ask")` in `main.py`
          -> **Engine:** Calls `ask_endpoint()` in `main.py` -> `ask_rag()` in `llm_engine.py`

## UI Element: Save Manual Review
- **HTML:** `<button class="btn btn-primary" onclick="appActions.submitManualReview()">` (`Index.html:494`)
  -> **JS:** Calls `submitManualReview()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.bulkUpdateArtifacts()`
      -> **Code.gs:** `bulkUpdateArtifacts()` executes `UrlFetchApp` to `/api/bulk-update`
        -> **FastAPI:** `@app.post("/api/bulk-update")` in `main.py`
          -> **Engine:** Calls `bulk_update_endpoint()` in `main.py`

## UI Element: Materialize Selected Items
- **HTML:** `<button class="btn btn-primary" onclick="appActions.materializeSelected()">` (`Index.html:511`)
  -> **JS:** Calls `materializeSelected()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.materializeSelectedItems()`
      -> **Code.gs:** `materializeSelectedItems()` executes `UrlFetchApp` to `/api/workflows/materialize`
        -> **FastAPI:** `@app.post("/api/workflows/materialize")` in `main.py`
          -> **Engine:** Calls `materialize_items()` in `main.py` -> `materialize_artifact()` in `sync_engine.py`

## UI Element: Approve Cluster (Dynamic)
- **HTML:** `<button class="btn btn-primary" onclick="appActions.approveCluster('\${cluster.entity}', '\${idsJson}')">` (`JS_Actions.html:597`)
  -> **JS:** Calls `approveCluster()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.submitZeroShotRule()`
      -> **Code.gs:** `submitZeroShotRule()` executes `UrlFetchApp` to `/api/taxonomy/zero-shot-rule`
        -> **FastAPI:** `@app.post("/api/taxonomy/zero-shot-rule")` in `main.py`
          -> **Engine:** Calls `zero_shot_rule()` in `main.py` -> `append_zero_shot_rule()` in `llm_engine.py`

## UI Element: Reject Cluster (Dynamic)
- **HTML:** `<button class="btn btn-secondary" onclick="appActions.rejectCluster('\${idsJson}')">` (`JS_Actions.html:598`)
  -> **JS:** Calls `rejectCluster()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.submitZeroShotRule()`
      -> **Code.gs:** `submitZeroShotRule()` executes `UrlFetchApp` to `/api/taxonomy/zero-shot-rule`
        -> **FastAPI:** `@app.post("/api/taxonomy/zero-shot-rule")` in `main.py`
          -> **Engine:** Calls `zero_shot_rule()` in `main.py` -> `append_zero_shot_rule()` in `llm_engine.py`

## UI Element: Submit Zero-Shot Rule (Dynamic)
- **HTML:** `<button class="btn btn-primary" onclick="appActions.submitZeroShotRule()">` (`JS_Actions.html:1089`)
  -> **JS:** Calls `submitZeroShotRule()` in `JS_Actions.html`
    -> **Apps Script:** Calls `google.script.run.submitZeroShotRule()`
      -> **Code.gs:** `submitZeroShotRule()` executes `UrlFetchApp` to `/api/taxonomy/zero-shot-rule`
        -> **FastAPI:** `@app.post("/api/taxonomy/zero-shot-rule")` in `main.py`
          -> **Engine:** Calls `zero_shot_rule()` in `main.py` -> `append_zero_shot_rule()` in `llm_engine.py`