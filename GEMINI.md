# Nexus for Google - Master Directive

You are Gemini Code Assist, operating on the Nexus for Google project. 

**CRITICAL ARCHITECTURE DIRECTIVE:**
We maintain a single source of truth for all architectural constraints, database schemas, and execution protocols. These rules are stored in the `.clinerules/` directory.

Before you write, modify, or suggest any code, you MUST:
1. Read `.clinerules/architecture.md` to understand the Seven-Layer Description Model.
2. Read `.clinerules/execution-protocol.md` to understand versioning, changelogs, and audits.
3. If modifying backend files or databases, read `.clinerules/database.md`.

Do not make assumptions about the database schema or sync logic without consulting those files first.