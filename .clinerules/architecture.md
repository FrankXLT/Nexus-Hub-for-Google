---
# ALWAYS ACTIVE
---
# Nexus for Google - Architecture & Governance

## The Seven-Layer Description Model
Evaluate every code alteration against this model. Never allow a task to cross-contaminate logic layers.
- **Layer 7:** Presentation & Visualization (VQB UI Surfaces)
- **Layer 6:** Automation & Workflow Materialization (Downstream Actions)
- **Layer 5:** Taxonomy Classification (Contextual Array Purpose Assignment)
- **Layer 4:** Entity & Sub-Entity Profiling (Global Domain & Sender Identification)
- **Layer 3:** Ephemeral Staging & Quarantine Queue (Human-In-The-Loop Buffers)
- **Layer 2:** Ingestion, Token Economy & Array Batching (O(1) Payload Workers)
- **Layer 1:** Core Storage & Schema Integrity (SQLite STRICT & WAL Mode Engine)

**Task-to-Layer Constraint:** When modifying a file, explicitly declare the target Layer. 
**Logic Isolation:** Do NOT write database access strings in Layer 7, and do NOT include UI layout constraints inside Layer 2.

## Prompt Template Decoupling
All master system prompts must be strictly maintained as decoupled text templates inside the `DEFAULTS/` directory using the `.tmpl` notation. Never hardcode LLM prompts directly into Python logic blocks.