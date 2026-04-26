"""
Initializes the Nexus Hub SQLite database (nexus.db).
Enforces STRICT tables, WAL journaling mode, and JSON data type validation.
"""
import sqlite3
import os

DB_PATH = 'nexus.db'

def init_db(db_path: str = DB_PATH) -> None:
    """
    Connects to the SQLite database and executes the table creation schemas.
    Applies WAL mode and enables foreign key constraints.
    
    Args:
        db_path (str): The path to the SQLite database file. Defaults to 'nexus.db'.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Enable Write-Ahead Logging for concurrent reading/writing
    conn.execute("PRAGMA journal_mode=WAL;")
    # Enable foreign key constraint enforcement
    conn.execute("PRAGMA foreign_keys = ON;")
    
    cursor = conn.cursor()
    
    # 1. Config_System
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Config_System (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT
        ) STRICT;
    """)
    
    # 2. Sync_State
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Sync_State (
            app_name TEXT PRIMARY KEY,
            sync_token TEXT,
            last_updated INTEGER
        ) STRICT;
    """)

    # 3. Config_Prompts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Config_Prompts (
            target_app TEXT PRIMARY KEY,
            prompt_text TEXT
        ) STRICT;
    """)
    
    # 4. Taxonomy_Entities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Taxonomy_Entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            correspondent TEXT NOT NULL,
            purpose TEXT NOT NULL,
            custom_field_schema TEXT NOT NULL CHECK(json_valid(custom_field_schema))
        ) STRICT;
    """)
    
    # 5. Workspace_Artifacts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Workspace_Artifacts (
            artifact_id TEXT PRIMARY KEY,
            taxonomy_id INTEGER,
            raw_text TEXT,
            summary TEXT,
            custom_data TEXT CHECK(json_valid(custom_data)),
            status TEXT,
            locked_by_system INTEGER DEFAULT 0,
            FOREIGN KEY (taxonomy_id) REFERENCES Taxonomy_Entities (id) ON DELETE CASCADE
        ) STRICT;
    """)
    
    # 6. Artifact_History
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Artifact_History (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            actor TEXT NOT NULL,
            action_type TEXT NOT NULL,
            previous_state TEXT CHECK(json_valid(previous_state)),
            new_state TEXT CHECK(json_valid(new_state)),
            FOREIGN KEY (artifact_id) REFERENCES Workspace_Artifacts (artifact_id) ON DELETE CASCADE
        ) STRICT;
    """)

    # 7. Error_Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Error_Logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            module_name TEXT NOT NULL,
            artifact_id TEXT,
            error_message TEXT NOT NULL,
            stack_trace TEXT CHECK(json_valid(stack_trace)),
            FOREIGN KEY (artifact_id) REFERENCES Workspace_Artifacts (artifact_id) ON DELETE CASCADE
        ) STRICT;
    """)
    
    seed_default_prompts(conn)
    
    conn.commit()
    conn.close()
    print(f"Database initialization complete: {db_path} with STRICT tables and WAL mode enabled.")

def seed_default_prompts(conn: sqlite3.Connection) -> None:
    """
    Seeds the default master prompts into the Config_Prompts table
    if they do not already exist.
    """
    PROMPT_GMAIL = """You are a strict data extraction system for a centralized knowledge hub. Review the provided email thread. 

**Tasks:**
1. **Taxonomy Mapping:** Map the email to ONE exact `Category \\ Correspondent \\ Purpose` from the provided whitelist. If it does not match perfectly, output the purpose as 'Purpose/Review'.
2. **Summary:** Generate a concise, 1-sentence summary of the thread's current state.
3. **Action State:** Determine if this email requires human action (true/false).
4. **Custom Fields:** Based on the mapped Purpose, extract the following fields: [DYNAMIC_ARRAY]. Return null if not found.

**Rules:** Hallucinating new categories is strictly forbidden. 
**Output:** ONLY valid JSON.
{
  "taxonomy_path": "string",
  "summary": "string",
  "requires_action": boolean,
  "custom_fields": { "Field1": "value" }
}"""

    PROMPT_DRIVE_STAGE_1 = """You are an intelligent document routing engine. Review the following raw OCR text. It may contain scanning errors.

**Task:** Identify the primary organization, vendor, or sender of this document. Match it to ONE exact `Correspondent` string from the provided whitelist.

**Rules:**
- Ignore generic payment processors (e.g., PayPal, Stripe) if the actual vendor is mentioned.
- If the correspondent is completely unknown or the document is unreadable, output 'UNKNOWN'.
**Output:** ONLY valid JSON: { "correspondent": "string" }"""

    PROMPT_DRIVE_STAGE_2 = """You are a precise metadata extraction agent. Review the OCR text for this document belonging to the correspondent: [CORRESPONDENT].

**Tasks:**
1. **Purpose Mapping:** Map the document's intent to ONE exact `Purpose` from the provided whitelist. Output 'Purpose/Review' if ambiguous.
2. **Document Title:** Generate a concise, highly descriptive title for this document (e.g., 'Q3 Auto Insurance Renewal Policy').
3. **Document Date:** Extract the primary creation or effective date of the document in YYYY-MM-DD format.
4. **Custom Fields:** Extract the following specific fields for this purpose: [DYNAMIC_ARRAY]. Return null if not found.

**Output:** ONLY valid JSON.
{
  "purpose": "string",
  "title": "string",
  "document_date": "YYYY-MM-DD",
  "custom_fields": { "Field1": "value" }
}"""

    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('GMAIL', PROMPT_GMAIL))
    cursor.execute("INSERT OR IGNORE INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('DRIVE_STAGE_1', PROMPT_DRIVE_STAGE_1))
    cursor.execute("INSERT OR IGNORE INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('DRIVE_STAGE_2', PROMPT_DRIVE_STAGE_2))

if __name__ == "__main__":
    init_db()
