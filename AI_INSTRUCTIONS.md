# AI Agent Guardrails & Instructions

This file acts as the primary rulebook for any AI assistant (Gemini, Claude, Cursor, etc.) contributing to this repository. You MUST adhere to these rules at all times.

## 1. The Golden Rule of Branching
**All active coding happens ONLY on the `development` branch.**
Before generating any code, creating a new file, or modifying an existing one, you MUST check the active git branch using `git branch --show-current`. If the active branch is NOT `development`, you must instruct the user to switch to it, or you must switch to it yourself if authorized.

## 2. Standardization & Commits
*   **Conventional Commits:** All git commits must strictly follow the Conventional Commits specification.
    *   Examples: `feat: add AI router`, `fix: resolve HMAC bypass`, `chore: update dependencies`, `docs: update README`.
*   **Idiomatic Code:** Match the existing styling of the project. If modifying the FastAPI backend, adhere to PEP 8 and Pythonic patterns. If modifying the UI, match the existing CSS layout structures without introducing massive refactors unless explicitly requested.

## 3. Task Tracking & Roadmap
The project utilizes living documents (e.g., `ROADMAP/PROMPT_ROADMAP.md` and `INSTRUCTIONS.md`) to manage Epics and tasks.
*   You must maintain the structure of these files.
*   Tasks should be clearly segmented into **"Planned"** and **"Completed"**.
*   When finishing a task, move it from the Planned section to the Completed section to maintain an accurate, up-to-date roadmap.

## 4. Database Safety Protocols
Nexus Hub uses SQLite in WAL mode. Database integrity is critical.
*   **Diff Requirements:** When asked to generate a deployment script (`update.sh`) or a new database migration script, you MUST first request or perform a `git diff pre-release..main` (or equivalent branch comparison) to understand the delta.
*   **Transaction Blocks:** ALL generated SQL that alters data or schema MUST be wrapped in explicit transaction blocks:
    ```sql
    BEGIN TRANSACTION;
    -- SQL Commands
    COMMIT;
    ```
*   **Idempotency:** Migration scripts must be idempotent (safe to run multiple times).

## 5. Execution Warning & Human Approval
*   **Read-Only Operations:** You may use read-only terminal commands (e.g., `cat`, `grep`, `git status`, `git log`) to explore the project autonomously.
*   **Destructive/Mutation Operations:** Before executing ANY terminal commands that alter the git history, push code to a remote repository, or drop/modify database files, you **MUST present the code/command to the human developer for review and explicitly ask for approval.** Do not assume permission to push to GitHub or alter historical commits.