# Nexus for Google: Unified Architectural Requirements Construct (UARC)

## 1. The Seven-Layer Description Model
This model establishes strict boundaries for data processing, isolation, and AI orchestration across the Nexus architecture. All features and prompts must cleanly map to a single layer.

```text
+-------------------------------------------------------+
|  Layer 7: Presentation & Visualization (VQB UI)       |
+-------------------------------------------------------+
|  Layer 6: Automation & Workflow Materialization      |
+-------------------------------------------------------+
|  Layer 5: Taxonomy Classification (Zero Trust Purpose)|
+-------------------------------------------------------+
|  Layer 4: Entity & Sub-Entity Profiling               |
+-------------------------------------------------------+
|  Layer 3: Ephemeral Staging & Quarantine Queue       |
+-------------------------------------------------------+
|  Layer 2: Ingestion, Token Economy & Array Batching   |
+-------------------------------------------------------+
|  Layer 1: Core Storage & Schema Integrity (SQLite STRICT)|
+-------------------------------------------------------+
```

### Layer Descriptions & Boundaries:
* **Layer 1: Core Storage & Schema Integrity**
    * Scope: The raw SQLite database (`nexus.db`). Enforces STRICT tables, Write-Ahead Logging (WAL), and hard structural foreign keys. 
* **Layer 2: Ingestion, Token Economy & Array Batching**
    * Scope: Ingestion workers (`sync_engine.py`) and Google Apps Script triggers (`Code.gs`). Maximizes token economy by batching artifact payloads into O(1) JSON structures before executing LLM endpoints.
* **Layer 3: Ephemeral Staging & Quarantine Queue**
    * Scope: Data states that fail safety or confidence parameters. Temporarily buffers payloads requiring human-in-the-loop validation without altering the live production graph.
* **Layer 4: Entity & Sub-Entity Profiling**
    * Scope: Global domain and sender identification. Leverages the web-grounded commercial profiler to construct parent-child operational relationships (`parent_entity_id`) and maps raw communications to an active `workspace_alias`.
* **Layer 5: Taxonomy Classification**
    * Scope: Intent and purpose mapping. Executes contextual array classification to evaluate metadata against zero-trust definitions (Category and Purpose) without mutating parent entity data.
* **Layer 6: Automation & Workflow Materialization**
    * Scope: Downstream actions. Executes real-time file replication, Gmail label updates, and event hooks strictly based on high-confidence classifications derived from Layer 5.
* **Layer 7: Presentation & Visualization (VQB UI)**
    * Scope: The visual UI surfaces (`Index.html`, `JS_Actions.html`). Renders the interactive visual query boxes, heatmap telemetry, and Sankey data graphs purely derived from live Layer 1 state queries.

## 2. Unbreakable Database Mutation Laws
To prevent database corruption and schema divergence across rapid AI development cycles, all backend database interactions must follow these laws:

1. **Idempotency Over All:** Every schema manipulation statement must be completely safe to execute infinitely (e.g., CREATE TABLE IF NOT EXISTS, INSERT OR IGNORE).
2. **Explicit Structural Migrations:** AI agents are strictly forbidden from writing inline `try...except` blocks wrapped around ALTER TABLE operations to bypass table recreation constraints.
3. **SQLite Constraints Rule:** Because SQLite does not support adding FOREIGN KEY constraints via ALTER TABLE, any table alteration that alters relations must follow a formal migration script:
    * BEGIN TRANSACTION;
    * Create a new staging table with the modified schema, defaults, and FOREIGN KEY definitions.
    * Copy data from the old table: INSERT INTO new_table SELECT ... FROM old_table;
    * Drop the old table.
    * Rename the staging table to the final production table name.
    * COMMIT;
4. **Transaction Safety:** All data mutations (INSERT, UPDATE, DELETE) affecting multiple tables or background pipelines must be explicitly bound within standard transaction scopes.