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
When instructed to "run an audit," execute the V3 Exhaustive Matrix autonomously:
1. Identify the current version from `CHANGELOG.md`.
2. Perform a deep static analysis generating a Markdown document containing:
   - **Phase 1:** Total Census (Files, purposes, functions, API endpoints).
   - **Phase 2:** Hook Map (Trace UI -> Middleware -> Backend endpoints).
   - **Phase 3:** C4 Architecture Diagram (Generate Mermaid C4Container).
   - **Phase 4:** Database Verification (Map DB schema against active Python queries).
   - **Phase 5:** Orphan Report (List dead code, disconnected endpoints, unused triggers).
3. Save the report in the `AUDITS/` directory named: `[Version]_[YYYY-MM-DD]_audit_trace.md`.
4. **Constraint:** Audits are strictly read-only. Do not modify operational code during an audit.

## Resource Management & Cleanup Protocol
You must operate with zero digital footprint. Every operation you script must explicitly clean up after itself:
1. **Database Connections:** You must use Python context managers (`with sqlite3.connect(...)`) or explicit `try...finally` blocks to ensure `.close()` is called on every database connection and cursor, even if the query fails.
2. **Transactional Staging:** When performing the multi-stage SQLite table migrations (as defined in the Database Laws), you MUST ensure the `temporary_table` is explicitly dropped if the transaction fails or rolls back.
3. **File System & OS:** If your script writes temporary files, logs, or JSON dumps to disk for processing, you must include the `os.remove()` or `shutil.rmtree()` logic to delete them immediately upon completion or failure.
4. **Frontend State:** If you write UI logic that triggers a "Loading..." state or disables a button, you must guarantee that a `finally` block or `.catch()` promise resets that state, preventing the UI from locking up on an error.
5. Always begin new tasks in 'Plan Mode'. Analyze the repository, ask necessary clarifying questions, and present a structured implementation plan for 'Act Mode'. When all tasks are complete, return back to 'Act Mode'