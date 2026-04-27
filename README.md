# Nexus Hub for Google
![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Google Cloud](https://img.shields.io/badge/Google_Cloud-e2--micro-4285F4?style=flat-square&logo=googlecloud)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker)
![Gemini](https://img.shields.io/badge/AI-Gemini_Pro-8E75B2?style=flat-square&logo=googlegemini)
![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57?style=flat-square&logo=sqlite)
![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)
![License](https://img.shields.io/badge/license-GPLv3-green.svg)
![Platform](https://img.shields.io/badge/platform-Google_Workspace-orange.svg)

Nexus Hub is a self-hosted, AI-powered knowledge management system that unifies your Google Workspace ecosystem. Acting as the spiritual successor to Google Inbox, it transforms unstructured emails and Google Drive documents into a centralized, queryable relational database.

By leveraging Google's Gemini Large Language Models (LLMs) and a strictly governed Zero-Trust Taxonomy, Nexus Hub autonomously categorizes, extracts, and organizes your digital life while keeping your data entirely within your personal Google Cloud environment.

## Features

* **Zero-Touch Autonomy:** Natively monitors Gmail and Google Drive via delta-syncs and Pub/Sub webhooks, automatically tagging and sorting incoming artifacts without manual intervention.
* **Three-Tier Hierarchical Taxonomy:** Groups entities logically (`Category` -> `Correspondent` -> `Document Type`) to prevent directory sprawl and label bloat.
* **Multi-Dimensional Entity Profiles:** Maps specific sending subdomains, addresses, and inferred purposes to specific vendors to create a deterministic knowledge graph.
* **Zero-Trust Security & Quarantine:** newly discovered vendors and document types are quarantined in a disabled state until manually approved by the user.
* **Google Contacts Bootstrapping:** Automatically transforms your personal Google Contacts (names, emails, physical addresses) into multi-dimensional entity profiles for deterministic AI routing.
* **Intelligent Quota Governor:** Defends your daily Google API limits by prioritizing real-time emails (last 72 hours) and throttling historical batch processing.
* **RAG Knowledge Retrieval:** Features a natural language AI Assistant that queries your extracted SQLite metadata to answer complex questions about your documents and spending.
* **Cross-Ecosystem Visual Branding:** Synchronizes WCAG-compliant brand colors across both Gmail nested labels and Google Drive folders.
* **Telemetry & Push Alerts:** Integrates with Pushover to instantly notify you of critical infrastructure failures, while emailing daily digests of quarantined items.

## Version History

- **v1.4.0:** Phase 29 - Integrated Google People API for autonomous Contact Bootstrapping and multi-dimensional profile mapping.
- **v1.3.0:** Phase 28 - Telemetry & Alerting Matrix with Pushover webhook notifications and Gmail Daily Digests.
- **v1.3.0:** Phase 28 - Telemetry & Alerting Matrix with Pushover webhook notifications and Gmail Daily Digests.
- **v1.2.0:** Phase 22-26 - Added Three-Tier Taxonomy Hierarchy, Zero-Trust UI Review Queues, RAG Query engine, and Quota Governor.
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
* [How It Works](HOW_IT_WORKS.md)

## License

Licensed under the **GNU General Public License, Version 3.0 (GPLv3)**. See the `LICENSE` file for details.
