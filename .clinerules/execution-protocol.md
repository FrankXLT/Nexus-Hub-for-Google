---
# ALWAYS ACTIVE
---
# Execution, Versioning & Audit Protocol

## Autonomous Versioning & Changelog Protocol
You are strictly responsible for maintaining Semantic Versioning (SemVer) and historical logging. `CHANGELOG.md` is the immutable record of executed work.
Before concluding ANY task, execute this sequence:
1. Read `CHANGELOG.md` to identify the current system version.
2. Calculate SemVer bump: `PATCH` (x.x.1) for fixes/UI tweaks; `MINOR` (x.1.x) for non-breaking features; `MAJOR` (1.x.x) for breaking Layer 1/2 changes.
3. Prepend a new entry to `CHANGELOG.md`:
   `## [vX.Y.Z] - YYYY-MM-DD`
   `### Added | Changed | Deprecated | Removed | Fixed | Security`
   `- **Layer [X]:** [Brief description of the change and the AI model executing it].`
4. Remove the completed task from `FEATURE_TRACKING.md` if it existed.

## Architectural Audit Protocol
When instructed to "run an audit," "perform a system audit," or similar, you must autonomously execute the 

You are required to update the project's audit scripts and rule definitions in execution-protocal.md for generating a highly detailed, comprehensive system state report. Complete fidelity is required. Every audit report must be a comprehensive, granular inventory matching the exact structural template below:


CRITICAL ANTI-LAZINESS CONSTRAINTS:
1. ZERO SHORTCUTS: You are strictly forbidden from summarizing, truncating, or using placeholders like "As identified previously," "...", or "Rest of code here."
2. EXHAUSTIVE GENERATION: You must generate the data for every single phase fresh for this output. Do not reference past audits.
3. STANDARD MARKDOWN: Use standard triple-backtick markdown for all code blocks, Mermaid diagrams, and raw file outputs.
4. **Version Determination:** Read `CHANGELOG.md` to identify the most recent Semantic Version and date.
5. **File Generation:** Create the `AUDITS/` directory if it does not exist. Save the report inside it using the strict naming convention: `[Version]_[YYYY-MM-DD]_audit_trace.md`.
6. **Constraint:** Audits are strictly read-only operations. Do not modify any operational code during an audit.
7. Any tools or ancillary files to create the report need to be in the `AUDITS/scripts` folder.

### Phase 1: Total Census
List EVERY file in the repository categorized by stack layer. For each file, you MUST read its contents and output a sub-list of every single defined class, function, or API route, followed by an explicit one-sentence functional description.
*Example Format:*
- **`backend/main.py`** (FastAPI Core Router)
  - `health_check()`: Verifies system operational readiness and database heartbeat.
  - `POST /api/taxonomy/tree`: Fetches the hierarchical Zero Trust mapping structure for the UI explorer.

### Phase 2: Hook Map
Trace the complete, explicit control flow from the Layer 7 user interface down to the Layer 1 database queries for every primary user action. Do not summarize; write out the functional sequence chains:
*Example Format:*
1. **AI Profiling Flow:** `frontend/Index.html` DOM Trigger -> `frontend/Code.gs` RPC (`sendToNexusVM`) -> `backend/main.py` endpoint (`/api/batch/process`) -> `backend/llm_engine.py` (`run_agent_profiler`) -> SQL state mutation in `entities` table.

### Phase 3: C4 Architecture Diagram
Generate a detailed Mermaid C4Container diagram illustrating the boundaries, communication links, and security layer constraints (e.g., HMAC signatures, WAL DB modes) matching the true current state of the repository.
- User/Admin boundaries.
- Frontend Orchestrator (HTML/JS/GAS).
- FastAPI Backend API.
- Sync Engine / Background Workers.
- SQLite Database (including WAL modes).
- External integrations (Google Workspace APIs, Gemini API).

### Phase 4: Database Verification
Map active backend Python SQL strings directly against the initialized Layer 1 tables in `db_init.py`. Explicitly verify that all columns, `STRICT` constraints, type definitions, and index keys are aligned, documenting any unqueried schema attributes or type discrepancies.

### Phase 5: Orphan Report
Perform a dead-code hunt. Explicitly check for and list:
- Dead/Unreferenced files or shell scripts.
- Disconnected UI elements, hidden layout blocks, or abandoned DOM triggers.
- Unused Python imports or helper functions.
- API routes defined in the router that lack corresponding call hooks in the frontend bridge.

### Phase 6: Database Entity-Relationship Diagram (ERD)
Generate a comprehensive Mermaid.js diagram mapping the entire SQLite database schema.
- Include every table in the database.
- List all fields (columns) and their specific data types inside each table node.
- Explicitly define the relationship links (Foreign Keys) between tables.

### Phase 7: Database Row Sampling
Query the database and generate a data sampling section for EVERY table.
- Fetch and display exactly the first 3 rows and the last 3 rows (ordered by primary key) for every table.
- Format the output as clean, readable text tables.
- Do not skip any tables.

### Phase 8: Default Prompt Files
Read the directory containing the system's prompt templates (`DEFAULTS/`).
- Create a clear subsection for each prompt file.
- Output the absolute entire contents of each prompt file verbatim from the first character to the last.Phase 7: Database Row Sampling
Query the database and display exactly the first 3 rows and the last 3 rows for EVERY table (ordered by primary key). Format as clean, readable text tables. Do not skip any tables, even system configs.


### Phase 9: Pipeline Flow Audits (Front-to-Back)
Analyze the codebase for the following five pipelines:
A. Gmail Pipeline
B. Drive Pipeline
C. Contacts/People API Pipeline
D. Batch Gmail Ingest
E. Legacy Label Ingest

For EACH of the five pipelines, output:
- **Flow Diagram:** A Mermaid.js sequence diagram tracing the execution path from frontend interaction to database/UI. Use `[mermaid code begins]` and `[mermaid code ends]`.
- **Vulnerability & Assumption Matrix:** A bulleted list detailing where the pipeline breaks, code assumptions (payload structures, JSON enforcement, timeouts), and watch-out flags.

## Resource Management & Cleanup Protocol
You must operate with zero digital footprint. Every operation you script must explicitly clean up after itself:
1. **Database Connections:** You must use Python context managers (`with sqlite3.connect(...)`) or explicit `try...finally` blocks to ensure `.close()` is called on every database connection and cursor, even if the query fails.
2. **Transactional Staging:** When performing the multi-stage SQLite table migrations (as defined in the Database Laws), you MUST ensure the `temporary_table` is explicitly dropped if the transaction fails or rolls back.
3. **File System & OS:** If your script writes temporary files, logs, or JSON dumps to disk for processing, you must include the `os.remove()` or `shutil.rmtree()` logic to delete them immediately upon completion or failure.
4. **Frontend State:** If you write UI logic that triggers a "Loading..." state or disables a button, you must guarantee that a `finally` block or `.catch()` promise resets that state, preventing the UI from locking up on an error.
5. Always begin new tasks in 'Plan Mode'. Analyze the repository, ask necessary clarifying questions, and present a structured implementation plan for 'Act Mode'. When all tasks are complete, return back to 'Act Mode'