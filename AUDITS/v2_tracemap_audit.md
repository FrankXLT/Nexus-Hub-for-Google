# V2 Tracemap Audit: Nexus Architecture

## 1. File Structure
A visual representation of the backend, defaults, and frontend layers.

```text
c:\Users\frank\Github\Nexus-for-Google\
├── DEFAULTS/
│   ├── agent_classifier.tmpl
│   ├── agent_profiler_commercial.tmpl
│   ├── agent_profiler_personal.tmpl
│   ├── drive_extraction_stage1.tmpl
│   ├── drive_extraction_stage2.tmpl
│   ├── drive_extraction.tmpl
│   ├── entity_profiler.tmpl
│   ├── gmail_extraction.tmpl
│   ├── quarantine_consolidation.tmpl
│   └── zero_trust_defaults.json
├── backend/
│   ├── auth.py
│   ├── branding_engine.py
│   ├── db_init.py
│   ├── db_mapper.py
│   ├── diagnostics.py
│   ├── llm_engine.py
│   ├── main.py
│   ├── notifier.py
│   ├── patch_sync.py
│   ├── patch.py
│   ├── requirements.txt
│   ├── retention_worker.py
│   ├── sync_engine.py
│   └── update_llm.py
└── frontend/
    ├── Code.gs
    ├── CSS_Styles.html
    ├── debug.gs
    ├── Index.html
    ├── JS_Actions.html
    └── JS_State.html
```

## 2. Database Layer
The current SQLite schema explicitly enforced by `backend/db_init.py`. It confirms the existence of the new V2 Zero Trust architecture.

**Active Tables:**
- `Config_System`: Global settings and API Quota tracking.
- `Sync_State`: Google API pagination/history tokens.
- `Config_Prompts`: Dynamic LLM prompts.
- `Config_Retention_Rules`: Advanced retention sweep settings.
- `categories`: Zero-Trust relational taxonomy hierarchy (Tier 1).
- `purposes`: Document intent definitions (Tier 3).
- `entities`: Correspondents definition mapped to categories with a `nexus_state` column.
- `blacklist`: Domain and purpose blacklists.
- `Workspace_Artifacts`: Master index for Google Workspace items.
- `Artifact_History`: Immutable audit log.
- `Error_Logs`: Dead-Letter Queue (DLQ).
- `Ingestion_Queue`: Asynchronous buffering for historical ingestion.
- `quarantine_queue`: New Zero Trust table that holds items lacking trust validation pending manual approval.

*Verification:* The schema strictly uses `categories`, `purposes`, and `entities` instead of legacy Taxonomy_* tables, and `quarantine_queue` is successfully enforced.

## 3. API Layer & Legacy SQL Check
Current state of the FastAPI application in `backend/main.py` and sync logic in `backend/sync_engine.py`.

**Active FastAPI Endpoints (`main.py`):**
- **Ingestion & Data Flow:**
  - `POST /api/ingestion/queue-historical`
  - `POST /api/workflows/materialize`
  - `POST /api/bulk-update`
  - `POST /api/update`
- **Analytics & Dashboards:**
  - `GET /api/dashboard/mission-control`
  - `GET /api/analytics/heatmap`
  - `GET /api/analytics/threads`
  - `GET /api/analytics/roi-dashboard`
  - `GET /api/analytics/taxonomy`
- **Taxonomy & Zero Trust:**
  - `GET /api/taxonomy/flow`
  - `POST /api/taxonomy/discover`
  - `POST /api/taxonomy/zero-shot-rule`
  - `GET /api/taxonomy/blacklist`
  - `POST /api/taxonomy/blacklist`
  - `PUT /api/entities/correspondents/{id}`
  - `PUT /api/entities/purposes/{id}`
  - `GET /api/quarantine/queue`
- **Settings & Config:**
  - `GET /api/settings/pipeline`
  - `POST /api/settings/pipeline`
  - `GET /api/prompts`
  - `POST /api/prompts`
- **Health & Telemetry:**
  - `GET /api/health`
  - `POST /api/health`
  - `GET /api/health/quota`
  - `GET /api/orchestrator/telemetry`
- **Retention:**
  - `GET /api/retention/rules`
  - `POST /api/retention/rules`
  - `DELETE /api/retention/rules/{rule_id}`
  - `POST /api/retention/sweep`
- **LLM / Parsing:**
  - `GET /api/artifacts/search`
  - `POST /api/sandbox`
  - `POST /api/ask`

**Legacy SQL Check:**
- **`main.py` Status:** **CLEAN**. There are no queries targeting `Taxonomy_Correspondents`, `Taxonomy_Purposes`, or `Taxonomy_Categories`. All taxonomy queries have been updated to target `categories`, `purposes`, and `entities`.
- **`sync_engine.py` Status:** **CLEAN**. Functions such as `ingest_taxonomy_seed` insert directly into `categories`, `entities`, and `purposes`. Zero trust logic successfully writes directly into `quarantine_queue`. No legacy tables are queried. 

## 4. Frontend State
Core functions and orchestrator objects mapped from Google Apps Script and HTML interfaces.

**Apps Script Interface (`frontend/Code.gs`):**
- `doGet(e)`: Serves the `Index.html` web app interface.
- **Webhook & Data Exchange:** `sendToNexusVM()`, `bulkUpdateArtifacts()`, `searchArtifacts()`, `queueHistoricalImport()`.
- **Diagnostics:** `runSystemDiagnostics()`, `pingHealthAPI()`.
- **LLM Prompts & QA:** `runSandboxPrompt()`, `runAskAI()`, `submitZeroShotRule()`.
- **Analytics Retrieval:** `getHeatmapData()`, `getThreadsData()`, `getROIDashboard()`.
- **Settings & Rules:** `getUserPreferences()`, `updateSafeMode()`, `getPipelineSettings()`, `savePipelineSettings()`, `updateEntityRules()`.
- **Retention Execution:** `getRetentionRules()`, `addRetentionRule()`, `deleteRetentionRule()`, `triggerRetentionSweep()`.
- **Orchestration / Telemetry:** `getQuotaGovernor()`, `getOrchestratorTelemetry()`, `getQuarantineQueue()`.
- **Security:** `configureHMAC()`, `generateHMACSignature_()`.

**Orchestrator State (`frontend/JS_Actions.html`):**
- Governed by the `appActions` object.
- **Initialization:** `init()`, `initOrchestrator()`.
- **Zero Trust Routing:** `loadZeroTrustFlow()`, `filterZeroTrustTree()`, `clearQuarantineFilter()`, global `handleNodeClick()` event router.
- **Swimlane Handlers:** `expandSwimlane()`, `renderQuarantineBanner()`.
- **Visual Rendering:** Generates visual graphs via Mermaid/Sankey (`renderSankey()`, `generateDummyLinks()`) and Heatmaps (`renderVQB()`, `generateDummyHeatmapData()`).

## 5. AI Prompts
Files currently driving the decoupled AI extraction and profiling logic from `DEFAULTS/`:

- `agent_classifier.tmpl`
- `agent_profiler_commercial.tmpl`
- `agent_profiler_personal.tmpl`
- `drive_extraction_stage1.tmpl`
- `drive_extraction_stage2.tmpl`
- `drive_extraction.tmpl`
- `entity_profiler.tmpl`
- `gmail_extraction.tmpl`
- `quarantine_consolidation.tmpl`
- `zero_trust_defaults.json` (Configuration framework for bootstrap)
