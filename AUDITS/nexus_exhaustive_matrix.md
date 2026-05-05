# Nexus Exhaustive Matrix

## Phase 1: The Total Census (Inventory)

### Index.html Interactive Elements
- `<button class="menu-toggle" onclick="toggleSidebar()">`
- `<div class="nav-item" onclick="appState.switchTab('mission-control', event)">`
- `<div class="nav-item active" onclick="appState.switchTab('grid', event)">`
- `<div class="nav-item" onclick="appState.switchTab('correspondent-review', event)">`
- `<div class="nav-item" onclick="appState.switchTab('entity-management', event)">`
- `<div class="nav-item" onclick="appState.switchTab('prompt-sandbox', event)">`
- `<div class="nav-item" onclick="appState.switchTab('pipeline-orchestrator', event)">`
- `<div class="nav-item" onclick="appState.switchTab('inbox-cleanup', event)">`
- `<div class="nav-item" onclick="appState.switchTab('audit', event)">`
- `<div class="nav-item" onclick="appState.switchTab('analytics', event)">`
- `<div class="nav-item" onclick="appState.switchTab('ai-assistant', event)">`
- `<input type="checkbox" id="toggle-retention" onchange="appActions.updateSafeMode('feature_retention_sweeper', this.checked)" style="opacity: 0; width: 0; height: 0;">`
- `<input type="checkbox" id="toggle-relocator" onchange="appActions.updateSafeMode('feature_drive_relocator', this.checked)" style="opacity: 0; width: 0; height: 0;">`
- `<input type="checkbox" id="toggle-materialization" onchange="appActions.updateSafeMode('feature_materialization', this.checked)" style="opacity: 0; width: 0; height: 0;">`
- `<input type="checkbox" id="toggle-tasks" onchange="appActions.updateSafeMode('feature_google_tasks', this.checked)" style="opacity: 0; width: 0; height: 0;">`
- `<div class="nav-item" onclick="appActions.triggerDiagnostics()" style="margin: 0; padding: 12px 20px; background: transparent;" title="Trigger a comprehensive health check of all system components.">`
- `<button class="btn btn-primary" onclick="appActions.renderHeatmap()"><i class="material-icons">refresh</i> Refresh</button>`
- `<button class="icon-btn save" title="Save Query to Left Nav" onclick="appActions.showToast('Feature coming soon: Save Query')">`
- `<button class="icon-btn" title="Advanced Search Builder" onclick="appActions.showToast('Feature coming soon: Advanced Builder')">`
- `<button class="view-btn" id="view-sankey" onclick="appActions.switchWorkspaceView('threads')" style="background: transparent; color: var(--text-muted); border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;">Sankey Threads</button>`
- `<button class="view-btn active" id="view-grid" onclick="appActions.switchWorkspaceView('grid')" style="background: #333; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;">Knowledge Grid</button>`
- `<a href="#" id="global-select-link" onclick="appActions.activateGlobalSelect(); return false;" style="font-weight: bold; margin-left: 8px; color: #1a73e8; text-decoration: underline;">Select all matching items</a>`
- `<button class="chip" onclick="toggleChip(this, 'Purpose:Receipt')">`
- `<button class="chip" onclick="toggleChip(this, 'Action:Required')">`
- `<button class="chip" onclick="toggleChip(this, 'Has:Attachment')">`
- `<button class="chip" onclick="toggleChip(this, 'Source:Drive')">`
- `<button class="btn btn-primary" onclick="appActions.refreshData()"><i class="material-icons">refresh</i> Refresh</button>`
- `<button class="btn btn-primary" onclick="appActions.queueHistoricalImport()">Queue Import</button>`
- `<select id="filter-category" onchange="appActions.onCategoryChange()" style="padding: 5px; flex: 1;">`
- `<select id="filter-correspondent" onchange="appActions.onCorrespondentChange()" style="padding: 5px; flex: 1;" disabled>`
- `<select id="filter-purpose" onchange="appActions.applyFilters()" style="padding: 5px; flex: 1;" disabled>`
- `<button class="btn btn-secondary" onclick="appActions.bulkEdit()"><i class="material-icons">edit</i> Bulk Edit Selected</button>`
- `<button class="btn btn-secondary" onclick="document.getElementById('workflow-hub-modal').style.display='block'"><i class="material-icons">auto_fix_high</i> Workflow Hub</button>`
- `<button class="drawer-close-btn" onclick="appActions.closeContextDrawer()">`
- `<button class="btn btn-primary" onclick="appActions.refreshData()"><i class="material-icons">refresh</i> Refresh</button>`
- `<button class="drawer-close-btn" onclick="appActions.closeContextDrawer()">`
- `<button class="btn btn-primary" onclick="appActions.saveCorrespondentRules()">Save Correspondent Rules</button>`
- `<button class="btn btn-primary" onclick="appActions.savePurposeRules()">Save Purpose Rules</button>`
- `<button class="btn btn-primary" onclick="appActions.runSandbox()"><i class="material-icons">play_arrow</i> Run Sandbox</button>`
- `<button class="btn btn-primary" onclick="appActions.savePipelineSettings()"><i class="material-icons">save</i> Save Pipeline Config</button>`
- `<button class="btn btn-primary" onclick="appActions.renderAnalyticsDashboard()"><i class="material-icons">refresh</i> Refresh Data</button>`
- `<button class="btn btn-primary" onclick="appActions.askAI()" title="Submit your query to the AI."><i class="material-icons">send</i> Send</button>`
- `<button class="btn btn-secondary" onclick="document.getElementById('manual-review-modal').style.display='none'">Cancel</button>`
- `<button class="btn btn-primary" onclick="appActions.submitManualReview()">Save</button>`
- `<i class="material-icons" style="cursor: pointer;" onclick="document.getElementById('workflow-hub-modal').style.display='none'">close</i>`
- `<button class="btn btn-primary" onclick="appActions.materializeSelected()">Materialize Selected Items</button>`

### JS_Actions.html & JS_State.html Functions
- `activateGlobalSelect()`
- `applyFilters()`
- `approveCluster()`
- `askAI()`
- `buildHeatmap()`
- `bulkEdit()`
- `closeContextDrawer()`
- `executeASTSearch()`
- `getArtifact()`
- `hexToRgba()`
- `init()`
- `loadPipelineSettings()`
- `loadQuotaGovernor()`
- `loadUserPreferences()`
- `materializeSelected()`
- `onCategoryChange()`
- `onCorrespondentChange()`
- `openClusterDrawer()`
- `openManualReviewModal()`
- `pingHealth()`
- `populateCategoryDropdown()`
- `queueHistoricalImport()`
- `refreshData()`
- `rejectCluster()`
- `renderAnalyticsDashboard()`
- `renderDetailsPane()`
- `renderGrid()`
- `renderHeatmap()`
- `renderThreadsView()`
- `renderTimeline()`
- `renderZeroTrustQueue()`
- `runSandbox()`
- `saveCorrespondentRules()`
- `savePipelineSettings()`
- `savePurposeRules()`
- `selectAll()`
- `selectArtifact()`
- `setArtifacts()`
- `setHistory()`
- `setupOmnibox()`
- `showToast()`
- `startHealthPing()`
- `submitManualReview()`
- `submitZeroShotRule()`
- `switchTab()`
- `switchWorkspaceView()`
- `toggleChip()`
- `toggleRowSelection()`
- `toggleSelectAll()`
- `toggleSelection()`
- `toggleSidebar()`
- `triggerDiagnostics()`
- `updateBulkEstimate()`
- `updateSafeMode()`
- `updateSelectionBanner()`

### Code.gs Functions
- `addRetentionRule()`
- `bulkUpdateArtifacts()`
- `configureHMAC()`
- `deleteRetentionRule()`
- `doGet()`
- `generateHMACSignature_()`
- `getHeatmapData()`
- `getPipelineSettings()`
- `getQuotaGovernor()`
- `getROIDashboard()`
- `getRetentionRules()`
- `getThreadsData()`
- `getUserPreferences()`
- `include()`
- `materializeSelectedItems()`
- `pingHealthAPI()`
- `queueHistoricalImport()`
- `runAskAI()`
- `runSandboxPrompt()`
- `runSystemDiagnostics()`
- `savePipelineSettings()`
- `searchArtifacts()`
- `sendToNexusVM()`
- `submitZeroShotRule()`
- `triggerRetentionSweep()`
- `updateEntityRules()`
- `updateSafeMode()`

### main.py FastAPI Endpoints
- `POST /api/ingestion/queue-historical`
- `POST /api/workflows/materialize`
- `POST /api/taxonomy/zero-shot-rule`
- `GET /api/artifacts/search`
- `GET /api/dashboard/mission-control`
- `GET /api/analytics/heatmap`
- `GET /api/analytics/threads`
- `GET /api/analytics/roi-dashboard`
- `POST /api/update`
- `POST /api/sandbox`
- `POST /api/ask`
- `POST /api/bulk-update`
- `GET /api/prompts`
- `POST /api/prompts`
- `GET /api/settings/pipeline`
- `POST /api/settings/pipeline`
- `PUT /api/entities/correspondents/{id}`
- `PUT /api/entities/purposes/{id}`
- `GET /api/health/quota`
- `GET /api/retention/rules`
- `POST /api/retention/rules`
- `DELETE /api/retention/rules/{rule_id}`
- `POST /api/retention/sweep`
- `POST /api/health`
- `GET /api/health`

## Phase 2: The Cross-Reference Mapping

### HTML to JS
- `<button class="menu-toggle" onclick="toggleSidebar()">` -> Calls: `toggleSidebar`
- `<div class="nav-item" onclick="appState.switchTab('mission-control', event)">` -> Calls: `switchTab`
- `<div class="nav-item active" onclick="appState.switchTab('grid', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('correspondent-review', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('entity-management', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('prompt-sandbox', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('pipeline-orchestrator', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('inbox-cleanup', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('audit', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('analytics', event)">` -> Calls: `switchTab`
- `<div class="nav-item" onclick="appState.switchTab('ai-assistant', event)">` -> Calls: `switchTab`
- `<input type="checkbox" id="toggle-retention" onchange="appActions.updateSafeMode('feature_retention_sweeper', this.checked)" style="opacity: 0; width: 0; height: 0;">` -> Calls: `updateSafeMode`
- `<input type="checkbox" id="toggle-relocator" onchange="appActions.updateSafeMode('feature_drive_relocator', this.checked)" style="opacity: 0; width: 0; height: 0;">` -> Calls: `updateSafeMode`
- `<input type="checkbox" id="toggle-materialization" onchange="appActions.updateSafeMode('feature_materialization', this.checked)" style="opacity: 0; width: 0; height: 0;">` -> Calls: `updateSafeMode`
- `<input type="checkbox" id="toggle-tasks" onchange="appActions.updateSafeMode('feature_google_tasks', this.checked)" style="opacity: 0; width: 0; height: 0;">` -> Calls: `updateSafeMode`
- `<div class="nav-item" onclick="appActions.triggerDiagnostics()" style="margin: 0; padding: 12px 20px; background: transparent;" title="Trigger a comprehensive health check of all system components.">` -> Calls: `triggerDiagnostics`
- `<button class="btn btn-primary" onclick="appActions.renderHeatmap()"><i class="material-icons">refresh</i> Refresh</button>` -> Calls: `renderHeatmap`
- `<button class="icon-btn save" title="Save Query to Left Nav" onclick="appActions.showToast('Feature coming soon: Save Query')">` -> Calls: `showToast`
- `<button class="icon-btn" title="Advanced Search Builder" onclick="appActions.showToast('Feature coming soon: Advanced Builder')">` -> Calls: `showToast`
- `<button class="view-btn" id="view-sankey" onclick="appActions.switchWorkspaceView('threads')" style="background: transparent; color: var(--text-muted); border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;">Sankey Threads</button>` -> Calls: `switchWorkspaceView`
- `<button class="view-btn active" id="view-grid" onclick="appActions.switchWorkspaceView('grid')" style="background: #333; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px;">Knowledge Grid</button>` -> Calls: `switchWorkspaceView`
- `<a href="#" id="global-select-link" onclick="appActions.activateGlobalSelect(); return false;" style="font-weight: bold; margin-left: 8px; color: #1a73e8; text-decoration: underline;">Select all matching items</a>` -> Calls: `activateGlobalSelect`
- `<button class="chip" onclick="toggleChip(this, 'Purpose:Receipt')">` -> Calls: `toggleChip`
- `<button class="chip" onclick="toggleChip(this, 'Action:Required')">` -> Calls: `toggleChip`
- `<button class="chip" onclick="toggleChip(this, 'Has:Attachment')">` -> Calls: `toggleChip`
- `<button class="chip" onclick="toggleChip(this, 'Source:Drive')">` -> Calls: `toggleChip`
- `<button class="btn btn-primary" onclick="appActions.refreshData()"><i class="material-icons">refresh</i> Refresh</button>` -> Calls: `refreshData`
- `<button class="btn btn-primary" onclick="appActions.queueHistoricalImport()">Queue Import</button>` -> Calls: `queueHistoricalImport`
- `<select id="filter-category" onchange="appActions.onCategoryChange()" style="padding: 5px; flex: 1;">` -> Calls: `onCategoryChange`
- `<select id="filter-correspondent" onchange="appActions.onCorrespondentChange()" style="padding: 5px; flex: 1;" disabled>` -> Calls: `onCorrespondentChange`
- `<select id="filter-purpose" onchange="appActions.applyFilters()" style="padding: 5px; flex: 1;" disabled>` -> Calls: `applyFilters`
- `<button class="btn btn-secondary" onclick="appActions.bulkEdit()"><i class="material-icons">edit</i> Bulk Edit Selected</button>` -> Calls: `bulkEdit`
- `<button class="btn btn-secondary" onclick="document.getElementById('workflow-hub-modal').style.display='block'"><i class="material-icons">auto_fix_high</i> Workflow Hub</button>` -> Calls: `getElementById`
- `<button class="drawer-close-btn" onclick="appActions.closeContextDrawer()">` -> Calls: `closeContextDrawer`
- `<button class="btn btn-primary" onclick="appActions.refreshData()"><i class="material-icons">refresh</i> Refresh</button>` -> Calls: `refreshData`
- `<button class="drawer-close-btn" onclick="appActions.closeContextDrawer()">` -> Calls: `closeContextDrawer`
- `<button class="btn btn-primary" onclick="appActions.saveCorrespondentRules()">Save Correspondent Rules</button>` -> Calls: `saveCorrespondentRules`
- `<button class="btn btn-primary" onclick="appActions.savePurposeRules()">Save Purpose Rules</button>` -> Calls: `savePurposeRules`
- `<button class="btn btn-primary" onclick="appActions.runSandbox()"><i class="material-icons">play_arrow</i> Run Sandbox</button>` -> Calls: `runSandbox`
- `<button class="btn btn-primary" onclick="appActions.savePipelineSettings()"><i class="material-icons">save</i> Save Pipeline Config</button>` -> Calls: `savePipelineSettings`
- `<button class="btn btn-primary" onclick="appActions.renderAnalyticsDashboard()"><i class="material-icons">refresh</i> Refresh Data</button>` -> Calls: `renderAnalyticsDashboard`
- `<button class="btn btn-primary" onclick="appActions.askAI()" title="Submit your query to the AI."><i class="material-icons">send</i> Send</button>` -> Calls: `askAI`
- `<button class="btn btn-secondary" onclick="document.getElementById('manual-review-modal').style.display='none'">Cancel</button>` -> Calls: `getElementById`
- `<button class="btn btn-primary" onclick="appActions.submitManualReview()">Save</button>` -> Calls: `submitManualReview`
- `<i class="material-icons" style="cursor: pointer;" onclick="document.getElementById('workflow-hub-modal').style.display='none'">close</i>` -> Calls: `getElementById`
- `<button class="btn btn-primary" onclick="appActions.materializeSelected()">Materialize Selected Items</button>` -> Calls: `materializeSelected`

### JS to Code.gs
- JS calls Apps Script: `bulkUpdateArtifacts()`
- JS calls Apps Script: `getHeatmapData()`
- JS calls Apps Script: `getPipelineSettings()`
- JS calls Apps Script: `getQuotaGovernor()`
- JS calls Apps Script: `getROIDashboard()`
- JS calls Apps Script: `getThreadsData()`
- JS calls Apps Script: `getUserPreferences()`
- JS calls Apps Script: `materializeSelectedItems()`
- JS calls Apps Script: `pingHealthAPI()`
- JS calls Apps Script: `queueHistoricalImport()`
- JS calls Apps Script: `runAskAI()`
- JS calls Apps Script: `runSandboxPrompt()`
- JS calls Apps Script: `runSystemDiagnostics()`
- JS calls Apps Script: `savePipelineSettings()`
- JS calls Apps Script: `searchArtifacts()`
- JS calls Apps Script: `submitZeroShotRule()`
- JS calls Apps Script: `updateEntityRules()`
- JS calls Apps Script: `updateSafeMode()`

### Code.gs to FastAPI
- Code.gs calls FastAPI: `/api/artifacts/search`
- Code.gs calls FastAPI: `/api/ask`
- Code.gs calls FastAPI: `/api/bulk-update`
- Code.gs calls FastAPI: `/api/health`
- Code.gs calls FastAPI: `/api/ingestion/queue-historical`
- Code.gs calls FastAPI: `/api/retention/rules`
- Code.gs calls FastAPI: `/api/retention/sweep`
- Code.gs calls FastAPI: `/api/sandbox`
- Code.gs calls FastAPI: `/api/settings/pipeline`
- Code.gs calls FastAPI: `/api/taxonomy/zero-shot-rule`
- Code.gs calls FastAPI: `/api/workflows/materialize`

## Phase 3: The Comprehensive Orphan Report

### Broken UI Links
- None found

### Dead Frontend Code
- **[DEAD JS]**: `setHistory()` is never called.
- **[DEAD JS]**: `toggleSelectAll()` is never called.

### Dead Middleware
- **[DEAD GS]**: `addRetentionRule()` is never called.
- **[DEAD GS]**: `deleteRetentionRule()` is never called.
- **[DEAD GS]**: `getRetentionRules()` is never called.
- **[DEAD GS]**: `triggerRetentionSweep()` is never called.

### Dead Backend Routes
- **[DEAD API]**: `GET /api/dashboard/mission-control` is never called.
- **[DEAD API]**: `GET /api/analytics/heatmap` is never called.
- **[DEAD API]**: `GET /api/analytics/threads` is never called.
- **[DEAD API]**: `GET /api/analytics/roi-dashboard` is never called.
- **[DEAD API]**: `POST /api/update` is never called.
- **[DEAD API]**: `GET /api/prompts` is never called.
- **[DEAD API]**: `POST /api/prompts` is never called.
- **[DEAD API]**: `PUT /api/entities/correspondents/{id}` is never called.
- **[DEAD API]**: `PUT /api/entities/purposes/{id}` is never called.
