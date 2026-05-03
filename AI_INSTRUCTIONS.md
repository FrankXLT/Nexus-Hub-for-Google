# AI Agent Guardrails & Instructions

This file acts as the primary rulebook for any AI assistant (Gemini, Claude, Cursor, etc.) contributing to this repository. You MUST adhere to these rules at all times.

## Task Routing Matrix

Use the matrix below (if you are asked to [X], read Section [Y]) to find the specific guidelines required for your current task:

*   **Task: Writing New Code or Fixing Bugs** -> Reference: Section 2 (Branching & Coding Standards)
*   **Task: Generating Code or Configurations** -> Reference: Section 3 (AI Coding Best Practices)
*   **Task: Modifying Database or Deployment Scripts** -> Reference: Section 4 (Database Safety & Idempotency)
*   **Task: Reviewing a Pull Request or Versioning** -> Reference: Section 5 (Versioning & Changelogs)
*   **Task: Updating Tracking or Documentation** -> Reference: Section 6 (Task Tracking & Documentation)
*   **Task: Handling Production Hotfixes** -> Reference: Section 7 (Bug Tracking and Hotfix Protocols)

## 1. Execution Warning & Human Approval
*   **Read-Only Operations:** You may use read-only terminal commands (e.g., `cat`, `grep`, `git status`, `git log`) to explore the project autonomously.
*   **Destructive/Mutation Operations:** Before executing ANY terminal commands that alter the git history, push code to a remote repository, or drop/modify database files, you **MUST present the code/command to the human developer for review and explicitly ask for approval.** Do not assume permission to push to GitHub or alter historical commits.

## 2. Branching & Coding Standards
*   **The Golden Rule of Branching:** All active coding happens ONLY on the `development` branch.
*   **Conventional Commits:** All git commits must strictly follow the Conventional Commits specification.
    *   Examples: `feat: add AI router`, `fix: resolve HMAC bypass`, `chore: update dependencies`, `docs: update README`.
*   **Idiomatic Code:** Match the existing styling of the project. If modifying the FastAPI backend, adhere to PEP 8 and Pythonic patterns. If modifying the UI, match the existing CSS layout structures without introducing massive refactors unless explicitly requested.

## 3. AI Coding Best Practices
*   **Context Verification:** You must verify the current active branch using `git branch --show-current` before generating or executing any terminal commands. If the active branch is NOT `development`, you must instruct the user to switch to it, or you must switch to it yourself if authorized.
*   **Chain of Thought:** You must briefly explain your logic and strategy before outputting any code blocks.
*   **No Lazy Coding:** You must never output truncated code blocks (e.g., `// ... rest of the code remains the same`). You must output the fully functional file or explicit diffs that are easy to copy/paste.
*   **Idempotency Focus:** When writing configuration files or deployment scripts, you must ensure they are safe to run multiple times without causing errors.

## 4. Database Safety & Idempotency
Nexus uses SQLite in WAL mode. Database integrity is critical.
*   **Diff Requirements:** When asked to generate a deployment script (`update.sh`) or a new database migration script, you MUST first request or perform a `git diff pre-release..main` (or equivalent branch comparison) to understand the delta.
*   **Transaction Blocks:** ALL generated SQL that alters data or schema MUST be wrapped in explicit transaction blocks:
    ```sql
    BEGIN TRANSACTION;
    -- SQL Commands
    COMMIT;
    ```
*   **Idempotency:** Migration scripts must be idempotent (safe to run multiple times).

## 5. Versioning & Changelogs
*   **Versioning & Pull Request Automation:** When reviewing a Pull Request (e.g., from `pre-release` to `main`), you must analyze the git diff and the commit messages (which must follow Conventional Commits). Based on the presence of features (`feat:`), bug fixes (`fix:`), or breaking changes, you must automatically calculate and propose the exact next Semantic Version number (Major.Minor.Patch) relative to the target branch's current version.
*   **Automated Changelog Generation:** Whenever a Pull Request is submitted, you must summarize all changes (commits, features, bugs) from that branch and append them to `CHANGELOG.md`. The `CHANGELOG.md` file must be strictly organized into two primary sections:
    *   **Development to Pre-Release:** A detailed log of all changes transitioning from the `development` branch into the `pre-release` testing environment.
    *   **Pre-Release to Main:** The finalized, official release notes detailing exactly what is being merged into the stable `main` branch.

## 6. Task Tracking & Documentation
The project utilizes living documents (e.g., `FEATURE_TRACKING.md` and `INSTRUCTIONS.md`) to manage Epics and tasks.
*   You must maintain the structure of these files.
*   Tasks should be clearly segmented into **"Planned"** and **"Completed"**.
*   When finishing a task, move it from the Planned section to the Completed section to maintain an accurate, up-to-date roadmap.
*   **FEATURE_TRACKING.md Formatting:**
    *   The file must be sectioned by the current Feature or Epic being worked on (using `##` headers).
    *   Under each section, there must be a Markdown table with exactly two columns: `Prompts or Strategy` and `Prompt Audit or Author Summary`.
        *   **Column 1 (Prompt or Strategy):** The exact text of the prompt provided to an AI, OR the human developer's strategic outline/pseudo-code for the feature.
        *   **Column 2 (Prompt Audit or Author Summary):** A detailed log from the AI agent or human developer containing a summary of actions, files modified, date/time, baseline modified from, and the author (Human or AI model).
*   **Fork Pull Requests:** When a Pull Request is merged from an external Fork, you are explicitly responsible for analyzing those external changes and automatically generating a summary to be injected into the appropriate section of `FEATURE_TRACKING.md`.

## 7. Bug Tracking and Hotfix Protocols
All bugs must be documented in `FEATURE_TRACKING.md` under a `## Bugs & Hotfixes` header, utilizing the standard two-column format.
*   **Development Bugs:** If a bug is found in the `development` branch, it is fixed directly in `development`.
*   **Pre-Release Bugs:** If a bug is found in `pre-release`, it must be fixed in `development` and merged into `pre-release` via a new PR. You must NEVER modify `pre-release` directly.
*   **Production Hotfixes (Main):** If a critical bug is found in `main`, you must instruct the user to create a temporary `hotfix-[version]` branch directly from `main`. The fix is applied there, Pull Requested back into `main`, and a Patch version bump is applied. Crucially, you must then instruct the user to immediately merge the updated `main` branch back down into `pre-release` and `development` to prevent regression.