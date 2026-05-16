# Project Roadmap & Backlog

## Epic: DX & Telemetry (Epic 5)
- [ ] **Automated DX Debug Panel & GitHub Issue Generator**
  - *Concept:* A dedicated UI tab for administrators to view system, API, and LLM errors. Users can select specific error logs and trigger an AI-assisted action to generate a sanitized, GitHub-ready bug report.

## Epic: Ingestion Expansion
- [ ] **The Edge Node SMS/RCS Forwarder**
  - *Core Objective:* Bypass the lack of a public Google Messages REST API by utilizing the user's Android device as a secure, automated edge node. Treats mobile text messages with the same ingestion and classification rigor as emails or Drive documents.
- [ ] **Universal IMAP Ingestion (Provider-Agnostic Sync)**
  - *Core Objective:* Break the hard dependency on the Google Workspace API by implementing a standard IMAP client within the Python backend, allowing Nexus to ingest unstructured communications from any standard email provider.

## Epic: Data Migration & Archival
- [ ] **Hierarchical Archive Ingestion**
  - *Concept:* Securely ingest and process deeply nested archive structures (e.g., historical local backups, nested Drive folders) while preserving parent-child context and entity relationships.

## Bugs & Hotfixes
- [ ] *All active bugs and required hotfixes will be tracked here via checklist items.*
