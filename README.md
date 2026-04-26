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
- **Google Workspace API Bridge:** Created `auth.py` for headless OAuth 2.0 authentication, handling necessary scopes for Gmail Modify and Drive access.
- **Backend Webhook Security:** Implemented `main.py` using FastAPI, complete with HMAC-SHA256 signature validation and UNIX timestamp replay protection.
- **Centralized Database & DLQ:** Built-in `db_init.py` ensures a strict, WAL-enabled SQLite schema. Includes a robust Dead-Letter Queue (`Error_Logs`) to catch and auto-retry API timeouts.
- **Delta Synchronization Engine:** Developed `sync_engine.py` for highly efficient delta fetching from Google Drive (Changes API) and Gmail (History API).
- **Self-Tuning LLM Engine:** Utilizes the Google GenAI SDK for RAG/Semantic categorization. Features a FastAPI `BackgroundTasks` loop that automatically rewrites and improves its own database-driven prompts based on user corrections.
- **Frontend Material UI:** A zero-dependency Google Apps Script frontend utilizing a Split-Pane layout, dynamic data grids, and an immutable Audit Timeline.

## Version History

- **v1.0.0:** Phase 19-21 - Decoupled hardcoded LLM prompts to SQLite, implemented FastAPI BackgroundTasks for the AI Self-Tuning loop, and finalized documentation.
- **v0.11.0:** Phase 16-18 - Containerized the Python backend via Docker Compose, added the Dead-Letter Queue, and implemented taxonomy normalization.
- **v0.10.0:** Phase 11-15 - Refactored database row factories, implemented programmatic visual branding, and deployed the Help Center tooltips.
- **v0.9.0:** Phase 9 - Implemented the zero-dependency Material Design UI (HTML/CSS/JS) via Apps Script templates.
- **v0.8.0:** Phase 8 - Implemented `llm_engine.py` to handle Gemini AI data extraction and artifact DB logging.
- **v0.7.0:** Phase 7 - Implemented `sync_engine.py` Delta Synchronization Engine for Gmail & Drive.
- **v0.6.0:** Phase 6 - Implemented `diagnostics.py` and diagnostic ping routing.
- **v0.5.0:** Phase 5 - Implemented `auth.py` for Google Workspace headless authentication.
- **v0.4.0:** Phase 4 - Implemented `Code.gs` Apps Script Router & Cryptographic Webhook Client.
- **v0.3.0:** Phase 3 - Implemented `main.py` Webhook Receiver with HMAC Signature & Replay Protection.
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
