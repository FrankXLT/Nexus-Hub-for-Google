"""
Module: db_init.py
Purpose: Initializes the Nexus Hub SQLite database (nexus.db).
Enforces STRICT tables, WAL journaling mode, and JSON data type validation.
"""
import sqlite3
import os

DB_PATH = 'nexus.db'

def init_db(db_path: str = DB_PATH) -> None:
    """
    Purpose: Connects to the SQLite database and executes the table creation schemas.
             Applies WAL mode and enables foreign key constraints.
    Expected Inputs:
        db_path (str): The path to the SQLite database file. Defaults to 'nexus.db'.
    Expected Outputs: None. Creates or updates the database schema on disk.
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
    # -- Core key-value store for global settings and Quota Governor API call tracking.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Config_System (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT
        ) STRICT;
    """)
    
    # 2. Sync_State
    # -- Maintains the Google API pagination/history tokens for delta-sync operations, 
    # -- preventing full data polling and preserving API quota.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Sync_State (
            app_name TEXT PRIMARY KEY,
            sync_token TEXT,
            last_updated INTEGER
        ) STRICT;
    """)

    # 3. Config_Prompts
    # -- Stores the active dynamic LLM prompts. Supports real-time prompt tuning
    # -- directly from the Apps Script UI.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Config_Prompts (
            target_app TEXT PRIMARY KEY,
            prompt_text TEXT
        ) STRICT;
    """)

    # 3b. Config_Retention_Rules
    # -- Stores advanced retention rules for inbox sweep/cleanup
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Config_Retention_Rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_category TEXT NOT NULL,
            action TEXT NOT NULL,
            days_old INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1
        ) STRICT;
    """)

    # 4. Taxonomy_Categories    # -- Tier 1 of the relational taxonomy hierarchy (e.g., 'Finance', 'Technology').
    # -- Uses Zero-Trust default toggles for ecosystem propagation.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Taxonomy_Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_gmail_enabled INTEGER DEFAULT 0,
            is_drive_enabled INTEGER DEFAULT 0
        ) STRICT;
    """)

    # 4b. Taxonomy_Correspondents
    # -- Tier 2 of the hierarchy representing vendors or senders. 
    # -- JSON tracking columns (sending_subdomains, physical_addresses, brand_colors) 
    # -- enrich the deterministic knowledge graph for LLM matching and UI branding.
    # -- operation_cost tracks historical LLM execution weight for Quota Governor throttling.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Taxonomy_Correspondents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            division TEXT,
            sending_subdomains TEXT CHECK(json_valid(sending_subdomains)),
            physical_addresses TEXT CHECK(json_valid(physical_addresses)),
            brand_colors TEXT CHECK(json_valid(brand_colors)),
            brand_color TEXT,
            custom_extraction_rules TEXT,
            operation_cost INTEGER DEFAULT 0,
            is_gmail_enabled INTEGER DEFAULT 0,
            is_drive_enabled INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES Taxonomy_Categories (id) ON DELETE CASCADE
        ) STRICT;
    """)

    # 4c. Taxonomy_Purposes
    # -- Tier 3 of the hierarchy determining the document's intent. 
    # -- operation_cost tracks execution impact for the Quota Governor.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Taxonomy_Purposes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correspondent_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            custom_field_schema TEXT NOT NULL CHECK(json_valid(custom_field_schema)),
            is_global INTEGER DEFAULT 0,
            auto_archive BOOLEAN DEFAULT 0,
            custom_extraction_rules TEXT,
            frequency_weight INTEGER DEFAULT 0,
            confidence_weight REAL DEFAULT 0.0,
            operation_cost INTEGER DEFAULT 0,
            is_gmail_enabled INTEGER DEFAULT 0,
            is_drive_enabled INTEGER DEFAULT 0,
            FOREIGN KEY (correspondent_id) REFERENCES Taxonomy_Correspondents (id) ON DELETE CASCADE
        ) STRICT;
    """)
    
    # 5. Workspace_Artifacts
    # -- The master index for all Google Workspace items. 
    # -- Uses `purpose_id` as the sole foreign key to maintain the cascading hierarchy,
    # -- as the Purpose node inherently belongs to a specific Correspondent and Category.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Workspace_Artifacts (
            artifact_id TEXT PRIMARY KEY,
            purpose_id INTEGER,
            raw_text TEXT,
            summary TEXT,
            custom_data TEXT CHECK(json_valid(custom_data)),
            status TEXT,
            locked_by_system INTEGER DEFAULT 0,
            parent_artifact_id TEXT,
            lifecycle_status TEXT DEFAULT 'ACTIVE',
            google_task_id TEXT,
            FOREIGN KEY (purpose_id) REFERENCES Taxonomy_Purposes (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_artifact_id) REFERENCES Workspace_Artifacts (artifact_id) ON DELETE SET NULL
        ) STRICT;
    """)
    
    # 6. Artifact_History
    # -- Immutable audit log tracking state changes from LLMs or manual UI overrides.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Artifact_History (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            actor TEXT NOT NULL,
            action_type TEXT NOT NULL,
            previous_state TEXT CHECK(json_valid(previous_state)),
            new_state TEXT CHECK(json_valid(new_state)),
            processing_time_ms INTEGER,
            api_tokens_used INTEGER,
            is_human_corrected BOOLEAN DEFAULT 0,
            FOREIGN KEY (artifact_id) REFERENCES Workspace_Artifacts (artifact_id) ON DELETE CASCADE
        ) STRICT;
    """)

    # 7. Error_Logs
    # -- The Dead-Letter Queue (DLQ) persisting stack traces and failures for later 
    # -- automated retries and Telemetry alerting.
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

    # 8. Ingestion_Queue
    # -- Asynchronous buffering system to handle massive historical data ingestion
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Ingestion_Queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            added_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        ) STRICT;
    """)
    
    seed_default_configs(conn)
    seed_default_prompts(conn)
    seed_default_taxonomy(conn)
    
    conn.commit()
    conn.close()
    print(f"Database initialization complete: {db_path} with STRICT tables and WAL mode enabled.")

def seed_default_configs(conn: sqlite3.Connection) -> None:
    """
    Purpose: Seeds default JSON settings into Config_System for UI Pipeline Orchestrator.
    Expected Inputs: conn (sqlite3.Connection) - An active connection to the SQLite database.
    Expected Outputs: None. Populates the Config_System table with initial values.
    """
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('ui_gmail_filters', '["CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"]', 'Ignored Gmail labels'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('ui_ai_config', '{"drive_model": "gemini-1.5-pro", "gmail_model": "gemini-1.5-flash"}', 'LLM model selection'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('ui_post_processing', '{"auto_archive_gmail": false, "quarantine_unconfident": true}', 'Post-processing actions'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('drive_permanent_archive_id', '""', 'Permanent Archive Folder ID'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('nexus_task_list_id', '""', 'Google Tasks List ID for actionable items'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('default_view', 'dashboard', 'UI Startup View'))
    
    # Epic 5 Safe Mode Gatekeepers
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('feature_retention_sweeper', '0', 'Safe Mode: Retention Sweeper'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('feature_drive_relocator', '0', 'Safe Mode: Drive Relocator'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('feature_materialization', '0', 'Safe Mode: Materialization Pipeline'))
    cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)",
        ('feature_google_tasks', '0', 'Safe Mode: Autonomous Google Tasks'))


def seed_default_taxonomy(conn):
    """
    Purpose: Seeds default categories and global purposes into the taxonomy tables.
    Expected Inputs: conn (sqlite3.Connection) - An active database connection.
    Expected Outputs: None. Populates the Taxonomy categories, correspondents, and purposes tables.
    """
    cursor = conn.cursor()
    # Create a dummy category and correspondent for global purposes if they don't exist
    cursor.execute("INSERT OR IGNORE INTO Taxonomy_Categories (name, is_gmail_enabled, is_drive_enabled) VALUES ('System', 1, 1)")
    cursor.execute("SELECT id FROM Taxonomy_Categories WHERE name = 'System'")
    cat_id = cursor.fetchone()['id']
    
    cursor.execute("INSERT OR IGNORE INTO Taxonomy_Correspondents (category_id, name, brand_color, is_gmail_enabled, is_drive_enabled) VALUES (?, 'Global', '#4285F4', 1, 1)", (cat_id,))
    cursor.execute("SELECT id FROM Taxonomy_Correspondents WHERE name = 'Global'")
    corr_id = cursor.fetchone()['id']
    
    global_purposes = ['Receipt / Invoice', 'Bill / Statement', 'Policy / Terms Update']
    # Loop over the list of default purposes to insert them into the database.
    for p in global_purposes:
        cursor.execute("""
            INSERT OR IGNORE INTO Taxonomy_Purposes (correspondent_id, name, custom_field_schema, is_global, is_gmail_enabled, is_drive_enabled)
            VALUES (?, ?, '{}', 1, 1, 1)
        """, (corr_id, p))

def seed_default_prompts(conn: sqlite3.Connection) -> None:
    """
    Purpose: Seeds the default master prompts into the Config_Prompts table if they do not already exist.
    Expected Inputs: conn (sqlite3.Connection) - An active database connection.
    Expected Outputs: None. Modifies Config_Prompts table.
    """
    PROMPT_GMAIL = """You are a strict data extraction system for a centralized knowledge hub. Review the provided email thread. 

**Tasks:**
1. **Taxonomy Mapping:** Map the email to ONE exact `Category \\ Correspondent \\ Purpose` from the provided [ENTITY_PROFILES]. Cross-reference the document's sender email, sending domain, or physical address against the provided entity profiles to increase routing accuracy. If it does not match perfectly, output the purpose as 'Purpose/Review'.
2. **Summary:** Generate a concise, 1-sentence summary of the thread's current state.
3. **Action State:** Determine if this email requires human action (true/false).
4. **Custom Fields:** Based on the mapped Purpose, extract the following fields: [DYNAMIC_ARRAY]. Return null if not found.
5. **Discovery:** If the LLM cannot match a whitelist, suggest a `discovered_purpose`.

**Rules:** Hallucinating new categories is strictly forbidden. 
**Output:** ONLY valid JSON.
{
  "taxonomy_path": "string",
  "summary": "string",
  "requires_action": boolean,
  "custom_fields": { "Field1": "value" },
  "discovered_purpose": "string"
}"""

    PROMPT_DRIVE_STAGE_1 = """You are an intelligent document routing engine. Review the following raw OCR text. It may contain scanning errors.

**Task:** Identify the primary organization, vendor, or sender of this document. Match it to ONE exact `Correspondent` string from the provided [ENTITY_PROFILES]. Cross-reference the document's sender email, sending domain, or physical address against the provided entity profiles to increase routing accuracy.

**Rules:**
- Ignore generic payment processors (e.g., PayPal, Stripe) if the actual vendor is mentioned.
- If the correspondent is completely unknown or the document is unreadable, output 'UNKNOWN'.
- If the LLM cannot match a whitelist, suggest a `discovered_correspondent`.
**Output:** ONLY valid JSON: { "correspondent": "string", "discovered_correspondent": "string" }"""

    PROMPT_DRIVE_STAGE_2 = """You are a precise metadata extraction agent. Review the OCR text for this document belonging to the correspondent: [CORRESPONDENT].

**Tasks:**
1. **Purpose Mapping:** Map the document's intent to ONE exact `Purpose` from the provided whitelist. Output 'Purpose/Review' if ambiguous.
2. **Document Title:** Generate a concise, highly descriptive title for this document (e.g., 'Q3 Auto Insurance Renewal Policy').
3. **Document Date:** Extract the primary creation or effective date of the document in YYYY-MM-DD format.
4. **Custom Fields:** Extract the following specific fields for this purpose: [DYNAMIC_ARRAY]. Return null if not found.
5. **Discovery:** If the LLM cannot match a whitelist, suggest a `discovered_purpose`.

**Output:** ONLY valid JSON.
{
  "purpose": "string",
  "title": "string",
  "document_date": "YYYY-MM-DD",
  "custom_fields": { "Field1": "value" },
  "discovered_purpose": "string"
}"""

    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('GMAIL', PROMPT_GMAIL))
    cursor.execute("INSERT OR IGNORE INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('DRIVE_STAGE_1', PROMPT_DRIVE_STAGE_1))
    cursor.execute("INSERT OR IGNORE INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('DRIVE_STAGE_2', PROMPT_DRIVE_STAGE_2))

# Execute the initialization if the script is run directly.
if __name__ == "__main__":
    init_db()
