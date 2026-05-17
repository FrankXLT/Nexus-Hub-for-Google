# Nexus for Google: Unified Architectural Requirements Construct (UARC)

## 1. The Seven-Layer Description Model
This model establishes strict boundaries for data processing, isolation, and AI orchestration across the Nexus architecture. All features, scripts, and prompts must cleanly map to a single layer to prevent cross-contamination of logic.
```text
+-------------------------------------------------------+
|  Layer 7: Presentation & Visualization (Apps Script)  |
+-------------------------------------------------------+
|  Layer 6: Automation, Telemetry & Background Daemons  |
+-------------------------------------------------------+
|  Layer 5: Taxonomy Classification (Zero Trust Purpose)|
+-------------------------------------------------------+
|  Layer 4: Entity & Sub-Entity Profiling (LLM Engine)  |
+-------------------------------------------------------+
|  Layer 3: Ephemeral Staging & Quarantine Queue        |
+-------------------------------------------------------+
|  Layer 2: Ingestion, Token Economy & Delta Sync       |
+-------------------------------------------------------+
|  Layer 1: Core Storage & Schema Integrity (SQLite)    |
+-------------------------------------------------------+
```

### Layer Descriptions & Boundaries:

#### **Layer 1: Core Storage & Schema Integrity**
* **Scope:** The raw SQLite database (`nexus.db`) managed via `db_init.py`. 
* **Rules of Engagement:**
  * Enforces `STRICT` table typing, Write-Ahead Logging (`WAL` mode) for concurrent read/writes (allowing UI telemetry during syncs), and hard structural foreign keys.
  * **Zero Trust Initialization:** The database is dynamically seeded via `DEFAULTS/zero_trust_defaults.json`, linking universal and categorical purposes. 
  * **Single Source of Truth:** `Config_Prompts` is the absolute authority for AI instructions. Fallbacks to local `.tmpl` files are permitted *only* for disaster recovery and must log an immediate error.

#### **Layer 2: Ingestion, Token Economy & Delta Sync**
* **Scope:** The Data fetching pipeline (`sync_engine.py`).
* **Rules of Engagement:**
  * **No Full Polling:** Uses `historyId` (Gmail) and `pageTokens` (Drive) for strict delta fetching.
  * **Array Batching:** Implements O(1) Array Batching architecture for optimized Gemini API token economy during bulk operations.
  * **Kill Switches:** Hardware-level toggles stored in `pipeline_config`. If disabled, both real-time delta fetches *and* historical queue ingestion must be immediately bypassed.
  * **Legacy Label Engine:** Uses `fetch_legacy_gmail_labels` to migrate historical user folders, strictly filtering out Google system labels (`CATEGORY_UPDATES`, `UNREAD`, etc.).

#### **Layer 3: Ephemeral Staging & Quarantine Queue**
* **Scope:** Holding zone for unknown or low-confidence artifacts.
* **Rules of Engagement:**
  * Incoming artifacts with an LLM confidence score below the user-defined `ai_confidence_threshold` are routed here.
  * Ensures the Zero Trust taxonomy is never polluted by hallucinatory AI mappings. Requires human-in-the-loop validation via the UI Carousel.

#### **Layer 4: Entity & Sub-Entity Profiling (LLM Engine)**
* **Scope:** The intelligence layer (`llm_engine.py`).
* **Rules of Engagement:**
  * **Tool/JSON Conflict Avoidance:** When utilizing external API tools (e.g., `Google Search`), functions must *omit* the `response_mime_type="application/json"` constraint to prevent Gemini API `400 INVALID_ARGUMENT` crashes.
  * **Regex JSON Extraction:** Because the LLM may return conversational filler (especially when dropping the strict JSON mime type), all LLM outputs must be parsed through a robust regex stripper (`r'(\{.*\}|\[.*\])'`) to extract the data payload safely.
  * **Prompt Sourcing:** Prompts must be pulled directly from the `Config_Prompts` database table via `fetch_active_prompt()` to ensure user edits in the Sandbox UI are immediately active.

#### **Layer 5: Taxonomy Classification (Zero Trust Purpose)**
* **Scope:** The strict relational mapping of Entities to Purposes.
* **Rules of Engagement:**
  * **Two-Stage Triage (Drive):** Stage 1 identifies the correspondent and checks routing rules. Stage 2 executes deep OCR/extraction *only* if the entity taxonomy permits it.
  * **Safe Mode Gatekeeper:** During development and initial ingestion, Drive relocators are disabled. Artifacts are profiled but not physically moved in Google Drive.

#### **Layer 6: Automation, Telemetry & Background Daemons**
* **Scope:** Task scheduling and system health (`main.py` background tasks).
* **Rules of Engagement:**
  * Manages the `QuotaGovernor`, enforcing the `DAILY_QUOTA_LIMIT` and utilizing the 72-Hour Priority Lane mechanism to guarantee resources for real-time artifact ingestion over historical backlog.
  * Serves lightning-fast aggregate queries (e.g., `/api/telemetry/pulse`) directly from SQLite `COUNT(*)` to prevent draining Google API quotas.

#### **Layer 7: Presentation & Visualization (Apps Script Bridge)**
* **Scope:** The UI surfaces (`Index.html`, `JS_Actions.html`) and the Google Apps Script Router (`Code.gs`).
* **Rules of Engagement:**
  * **Secure Bridge:** UI components must never communicate directly with the Python VM. All payloads route through `Code.gs` using `HMAC-SHA256` payload signing.
  * **DOM Sanitization:** All raw strings returned from Google APIs (e.g., `"Amazon.com" <orders@amazon.com>`) must be sanitized using regex HTML replacement (`&quot;`, `&lt;`) before DOM injection via `.innerHTML` to prevent UI tearing.
  * **Payload Unwrapping:** Frontend fetch handlers must expect and unwrap standardized response objects (`{success: true, data: [...]}`).

---

## 2. Unbreakable Database Mutation Laws
To prevent database corruption and schema divergence across rapid AI development cycles, all backend database interactions must follow these laws:

1. **Idempotency Over All:** Every schema manipulation statement must be completely safe to execute infinitely (e.g., `CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE`).
2. **Explicit Structural Migrations:** AI agents are strictly forbidden from writing inline `try...except` blocks wrapped around `ALTER TABLE` operations to bypass table recreation constraints.
3. **SQLite Constraints Rule:** Because SQLite does not support adding `FOREIGN KEY` constraints via `ALTER TABLE`, any table alteration that alters relations must follow a formal migration script:
    * `BEGIN TRANSACTION;`
    * Create a new staging table with the modified schema, defaults, and `FOREIGN KEY` definitions.
    * Copy data from the old table: `INSERT INTO new_table SELECT ... FROM old_table;`
    * Drop the old table.
    * Rename the staging table to the final production table name.
    * `COMMIT;`
4. **Transaction Safety:** All data mutations (`INSERT`, `UPDATE`, `DELETE`) affecting multiple tables or background pipelines must be explicitly bound within standard transaction scopes.

---

## 3. DevOps & Deployment Protocols
* **Version Control Limitation:** Google Apps Script is hard-capped at 20 versioned deployments. Automated CI/CD scripts (`deploy.ps1`, `deploy.sh`) must update the *existing* head deployment (`clasp deploy -i $DEPLOYMENT_ID`) rather than constantly pushing new versions.
* **Pruning:** A deployment pruning utility must be maintained within the Fleet Health Dashboard to clear out stale Apps Script versions and maintain CI/CD pipeline integrity.