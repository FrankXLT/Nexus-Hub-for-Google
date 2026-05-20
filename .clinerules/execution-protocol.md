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
When instructed to "run an audit," "perform a system audit," or similar, you must autonomously execute the **Hybrid Audit Workflow** defined below. You are strictly forbidden from attempting to manually type out file directories, prompt templates, or database rows.

### The Hybrid Execution Workflow
**Step 1: Deterministic Baseline Generation (Terminal)**
1. Open your terminal and execute: `python AUDITS/scripts/audit_builder.py`
2. Wait for the script to finish. It will autonomously generate a new file in the `AUDITS/` directory named `[Version]_[YYYY-MM-DD]_audit_trace.md`. This script mathematically extracts Phase 1 (File Census), Phase 6 (ERD), Phase 7 (Row Sampling), and Phase 8 (Prompt Files).

**Step 2: Architectural Reasoning (LLM Generation)**
1. Read the newly generated `[Version]_[YYYY-MM-DD]_audit_trace.md` file into your context.
2. Locate the placeholders marked `> [PENDING MANUAL AI ARCHITECT GENERATION]` for Phases 2, 3, 4, 5, and 9.
3. Analyze the codebase and use your architectural reasoning to generate the missing content for these specific phases (definitions below).
4. Edit the file to replace the placeholders with your generated Markdown and Mermaid diagrams. Save the completed file.

### Phase Definitions for Step 2 Generation:
* **Phase 2: Hook Map:** Trace the complete, explicit control flow from the Layer 7 user interface down to the Layer 1 database queries for every primary user action. Do not summarize; write out the functional sequence chains.
* **Phase 3: C4 Architecture Diagram:** Generate a detailed Mermaid `C4Container` diagram illustrating the boundaries, communication links, and security layer constraints matching the true current state of the repository.
* **Phase 4: Database Verification:** Map active backend Python SQL strings directly against the initialized Layer 1 tables in `db_init.py`. Explicitly verify that all columns, `STRICT` constraints, type definitions, and index keys are aligned, documenting any unqueried schema attributes or type discrepancies.
* **Phase 5: Orphan Report:** Perform a dead-code hunt. Explicitly list dead/unreferenced files, disconnected UI elements, unused Python imports, and API routes that lack frontend hooks.
* **Phase 9: Pipeline Flow Audits (Front-to-Back):** Analyze the codebase for the Gmail, Drive, Contacts, Batch, and Legacy Ingest pipelines. For EACH pipeline, output a Mermaid.js `sequenceDiagram` tracing the execution path, and a "Vulnerability & Assumption Matrix" detailing where the pipeline breaks, code assumptions, and watch-out flags.

**CRITICAL ANTI-LAZINESS CONSTRAINTS:**
1. ZERO SHORTCUTS: When generating the manual phases, you are strictly forbidden from summarizing, truncating, or using placeholders like "As identified previously," "...", or "Rest of code here."
2. STANDARD MARKDOWN: Use standard triple-backtick markdown for all code blocks and Mermaid diagrams.

## Resource Management & Cleanup Protocol
You must operate with zero digital footprint. Every operation you script must explicitly clean up after itself:
1. **Database Connections:** You must use Python context managers (`with sqlite3.connect(...)`) or explicit `try...finally` blocks to ensure `.close()` is called on every database connection and cursor, even if the query fails.
2. **Transactional Staging:** When performing the multi-stage SQLite table migrations (as defined in the Database Laws), you MUST ensure the `temporary_table` is explicitly dropped if the transaction fails or rolls back.
3. **File System & OS:** If your script writes temporary files, logs, or JSON dumps to disk for processing, you must include the `os.remove()` or `shutil.rmtree()` logic to delete them immediately upon completion or failure.
4. **Frontend State:** If you write UI logic that triggers a "Loading..." state or disables a button, you must guarantee that a `finally` block or `.catch()` promise resets that state, preventing the UI from locking up on an error.
5. Always begin new tasks in 'Plan Mode'. Analyze the repository, ask necessary clarifying questions, and present a structured implementation plan for 'Act Mode'. When all tasks are complete, return back to 'Act Mode'