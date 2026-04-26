# Nexus Hub for Google
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Google Cloud](https://img.shields.io/badge/Google_Cloud-e2--micro-4285F4?style=flat-square&logo=googlecloud)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker)
![Gemini](https://img.shields.io/badge/AI-Gemini_Pro-8E75B2?style=flat-square&logo=googlegemini)
![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=flat-square&logo=sqlite)

The Nexus Hub unifies the management of entities across Gmail, Google Drive, and Google Calendar. By enforcing a strict taxonomy and dynamic custom data extraction, the system transforms discrete files and emails into a centralized relational database. It relies on a hybrid architecture: a responsive, standalone Google Apps Script frontend backed by a persistent Google Cloud VM running a Python synchronization engine.

## Features

- **Automated Provisioning:** Provides `setup.sh` for an idempotent Ubuntu VM setup, installing Docker, Node.js, and `@google/clasp`.
- **CI/CD Lifecycle:** Contains `update.sh` for streamlined trunk-based deployment, managing migrations, codebase fetching, and Google Apps Script force pushes via `clasp`.
- **Diagnostic Suite:** Implemented `diagnostics.py` to isolate points of failure, verifying SQLite database integrity and Google Workspace OAuth validity, and uploading reports securely to Google Drive.
- **Google Workspace API Bridge:** Created `auth.py` for headless OAuth 2.0 authentication, handling necessary scopes for Gmail Modify and Drive access.
- **Apps Script Frontend Integration:** Added `Code.gs` serving as the web app router and secure client-side cryptographic bridge.
- **Backend Webhook Security:** Implemented `main.py` using FastAPI, complete with HMAC-SHA256 signature validation and UNIX timestamp replay protection to securely receive payloads from Apps Script.
- **Centralized Database:** Built-in `db_init.py` ensures a strict, WAL-enabled, and JSON-validated SQLite schema for robust metadata synchronization across the workspace.
- **Delta Synchronization Engine:** Developed `sync_engine.py` for highly efficient delta fetching from Google Drive and Gmail APIs.
- **LLM Metadata Extraction:** Implemented `llm_engine.py` leveraging the Google GenAI SDK for Two-Stage Triage processing of Google Drive OCR texts and Single-Pass contextual extraction for Gmail threads.
- **Frontend Material UI:** Developed a zero-dependency Google Apps Script frontend utilizing a Split-Pane layout, dynamic data grids, and an Audit Timeline.
- **Programmatic Color Management:** Implemented `branding_engine.py` to calculate Euclidean distances in RGB space to match brand colors to the strict Gmail API allowed palette, seamlessly syncing label and folder colors across the workspace.
- **Telemetry & Hardening:** Enhanced system resiliency via Docker Compose configuration with built-in log rotation (`json-file`, max 10MB), explicit SQLite `Error_Logs` tracking, database concurrency protection (`locked_by_system`), and robust LLM taxonomy normalization logic to handle hallucinations and aggressively enforce the exception queue fallback.

## Version History

- **v1.1.0:** Phase 16 - Telemetry and Hardening update, including Docker log rotation, `Error_Logs` table, and LLM Taxonomy Normalization.
- **v1.0.0:** Phase 12 - Implemented `branding_engine.py` for automated cross-workspace label and folder color synchronization.
- **v0.9.0:** Phase 9 - Implemented the zero-dependency Material Design UI (HTML/CSS/JS) via Apps Script templates.
- **v0.8.0:** Phase 8 - Implemented `llm_engine.py` to handle Gemini AI data extraction and artifact DB logging.
- **v0.7.0:** Phase 7 - Implemented `sync_engine.py` Delta Synchronization Engine for Gmail & Drive.
- **v0.6.0:** Phase 6 - Implemented `diagnostics.py` and diagnostic ping routing in `main.py` and `Code.gs`.
- **v0.5.0:** Phase 5 - Implemented `auth.py` for Google Workspace headless authentication.
- **v0.4.0:** Phase 4 - Implemented `Code.gs` Apps Script Router & Cryptographic Webhook Client.
- **v0.3.0:** Phase 3 - Implemented `main.py` Webhook Receiver with HMAC Signature & Replay Protection middleware.
- **v0.2.0:** Phase 2 - Implemented Database Initialization (`db_init.py`) with STRICT and JSON validation constraints.
- **v0.1.0:** Phase 1 - VM Infrastructure and CI/CD Pipeline implemented (`setup.sh`, `update.sh`).

## High-Level Architecture

Nexus Hub operates on a hybrid architecture:
1. **Frontend (Google Apps Script):** A secure, zero-trust web app serving the Material Design UI and acting as a secure webhook router.
2. **Backend (GCP e2-micro VM):** A persistent stateful engine running Python (FastAPI/Sync Engine), Docker, and a centralized SQLite index (`nexus.db`).
3. **AI Pipeline:** Uses Document AI for OCR and Gemini API for complex RAG/Semantic categorization.

```mermaid
flowchart LR
    User([User]) --> UI[Apps Script UI]
    UI -- "HMAC Secured" --> VM[GCP Python Engine]
    
    subgraph Google Workspace
        Drive[Google Drive]
        Gmail[Gmail]
    end
    
    Workspace -- "Pub/Sub & Polling" --> VM
    VM <--> DB[(SQLite Core)]
    VM -- "RAG & OCR" --> AI[Gemini API]
    
    style VM fill:#e6f4ea,stroke:#1e8e3e,stroke-width:2px
    style AI fill:#fce8e6,stroke:#d93025,stroke-width:2px
    style DB fill:#fef7e0,stroke:#f9ab00,stroke-width:2px
```

## Documentation

- [Master Architecture Specification](documentation/ARCHITECTURE.md)
- [Prompt Audit Log](documentation/PROMPT_AUDIT.md)
- [Step-by-Step Instructions](documentation/INSTRUCTIONS.md)

## License

Licensed under the **GNU General Public License, Version 3.0 (GPLv3)**. See the `LICENSE` file for details.
