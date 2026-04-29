## Targetget Feature: Automated DX Debug Panel & GitHub Issue Generator
* **Concept:** A dedicated UI tab for administrators to view system, API, and LLM errors. Users can select specific error logs and trigger an AI-assisted action to generate a sanitized, GitHub-ready bug report.
* **Potential Implementation:**
  * **Backend (`diagnostics.py`):** Create an endpoint to fetch filtered records from the `Error_Logs` SQLite table.
  * **LLM Engine:** Create a specific Gemini prompt template (`bug_report.tmpl`) instructed to act as a Senior QA Engineer. It must read the stack trace, summarize the root cause, and strictly redact any PII (names, emails, Drive folder IDs, etc.).
  * **Frontend (Apps Script UI):** Add a "Debug" tab. When an error is selected, the LLM summary is generated and displayed in a markdown-friendly `<textarea>` with a one-click "Copy for GitHub Issue" button.
* **Status:** Drafting / Backlog (Target: Epic 5)

## Feature Concept: The Edge Node SMS/RCS Forwarder

**Core Objective:** To bypass the lack of a public Google Messages REST API by utilizing the user's Android device as a secure, automated edge node. This bridges SMS and RCS communications directly into the Nexus Hub Knowledge Graph, treating mobile text messages with the same ingestion and classification rigor as emails or Drive documents.

### 1. The Edge Node Architecture (Android Automation)
Because Google aggressively sandboxes consumer messaging, the cloud cannot pull data; the device must push it.
* **The Trigger:** A local Android automation engine (e.g., Tasker or MacroDroid) listens for incoming SMS/RCS notifications.
* **The Payload Construction:** The automation extracts local device variables—specifically the Sender Number/Name (`%SMSRF`) and the Message Body (`%SMSRB`)—and formats them into a standardized JSON payload.
* **The Egress:** The device executes a background HTTP POST request, forwarding the payload to the Nexus Hub cloud backend.

### 2. Zero-Trust Ingress & Security
Opening a public-facing endpoint to receive text messages requires strict cryptographic validation to prevent spam or unauthorized data injection.
* **The Endpoint:** A dedicated FastAPI route: `POST /api/ingestion/sms`.
* **HMAC Validation:** The Android automation must compute and attach an `X-Nexus-Signature` header using the shared secret key. The backend drops any request that fails this signature check before parsing the body, keeping the Walled Garden intact.

### 3. LLM Pipeline & Normalization
Once securely received, the SMS payload is dropped seamlessly into the existing extraction pipeline, treating it as a lightweight email.
* **Entity Profiling:** The LLM evaluates the phone number and message context (e.g., "+15551234567" sending "Your HVAC maintenance is scheduled") to dynamically build or link a Correspondent Profile.
* **Taxonomy Classification:** The message is assigned a Tier 1-3 Purpose (e.g., `Purpose:Home Maintenance/Scheduling`).
* **Artifact Creation:** The text is injected into the SQLite database (`Workspace_Artifacts`) and becomes instantly searchable in the Command-Line Omnibox alongside standard emails.

### 4. Advanced Capabilities & Expansions
* **MMS & Receipt Processing:** If a contractor texts a photo of an invoice, the edge node can base64-encode the image and forward it. The backend decodes it, drops it into Drive, and runs Document AI.
* **Command-Line via SMS:** The edge node can act as a remote execution terminal. Texting a specific syntax (e.g., `#Nexus search Amazon receipts`) could trigger the API to parse the AST string and reply to the phone with a secure summary or Drive link, completely bypassing the web UI.
* Use AI to break messages with correspondents into discussion topic. each topic becomes the artifact.

