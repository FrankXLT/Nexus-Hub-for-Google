### Feature: Automated DX Debug Panel & GitHub Issue Generator
* **Concept:** A dedicated UI tab for administrators to view system, API, and LLM errors. Users can select specific error logs and trigger an AI-assisted action to generate a sanitized, GitHub-ready bug report.
* **Potential Implementation:**
  * **Backend (`diagnostics.py`):** Create an endpoint to fetch filtered records from the `Error_Logs` SQLite table.
  * **LLM Engine:** Create a specific Gemini prompt template (`bug_report.tmpl`) instructed to act as a Senior QA Engineer. It must read the stack trace, summarize the root cause, and strictly redact any PII (names, emails, Drive folder IDs, etc.).
  * **Frontend (Apps Script UI):** Add a "Debug" tab. When an error is selected, the LLM summary is generated and displayed in a markdown-friendly `<textarea>` with a one-click "Copy for GitHub Issue" button.
* **Status:** Drafting / Backlog (Target: Epic 5)