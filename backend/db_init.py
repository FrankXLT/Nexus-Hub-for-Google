"""
Module: db_init.py
Purpose: Initializes the Nexus SQLite database (nexus.db).
Enforces STRICT tables, WAL journaling mode, and JSON data type validation.
"""
import sqlite3
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory where db_init.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Navigate up to the root to find the DEFAULTS folder
DEFAULTS_DIR = os.path.join(BASE_DIR, "..", "DEFAULTS")

def get_prompt_template(filename):
    path = os.path.join(DEFAULTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

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
    logger.info("Verified SQLite WAL mode is active.")
    # Enable foreign key constraint enforcement
    conn.execute("PRAGMA foreign_keys = ON;")
    
    cursor = conn.cursor()
    cursor.execute("BEGIN TRANSACTION;")
    
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
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        );
    """)

    # 4c. Taxonomy_Purposes
    # -- Tier 3 of the hierarchy determining the document's intent. 
    # -- operation_cost tracks execution impact for the Quota Governor.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purposes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scope TEXT NOT NULL, -- 'Universal' or 'Categorical'
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            parent_entity_id INTEGER,
            workspace_alias TEXT DEFAULT NULL,
            show_in_gmail_nav BOOLEAN DEFAULT 1,
            show_in_gmail_msg BOOLEAN DEFAULT 1,
            use_in_drive_structure BOOLEAN DEFAULT 1,
            nexus_state TEXT DEFAULT 'active',
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (parent_entity_id) REFERENCES entities (id)
        );
    """)
    # Idempotent column additions for entities
    cols_to_add = [
        ("nexus_state", "TEXT DEFAULT 'active'"),
        ("workspace_alias", "TEXT DEFAULT NULL"),
        ("show_in_gmail_nav", "BOOLEAN DEFAULT 1"),
        ("show_in_gmail_msg", "BOOLEAN DEFAULT 1"),
        ("use_in_drive_structure", "BOOLEAN DEFAULT 1")
    ]
    for col_name, col_def in cols_to_add:
        try:
            cursor.execute(f"ALTER TABLE entities ADD COLUMN {col_name} {col_def};")
        except sqlite3.OperationalError:
            pass # Column already exists


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_string TEXT UNIQUE NOT NULL,
            entity_id INTEGER NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_config (
            pipeline_name TEXT PRIMARY KEY,
            is_enabled BOOLEAN DEFAULT 0,
            settings_json TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL, -- 'domain' or 'purpose'
            pattern TEXT NOT NULL,
            UNIQUE(type, pattern)
        );
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
            custom_data TEXT CHECK(custom_data IS NULL OR json_valid(custom_data)),
            status TEXT,
            locked_by_system INTEGER DEFAULT 0,
            parent_artifact_id TEXT,
            lifecycle_status TEXT DEFAULT 'ACTIVE',
            google_task_id TEXT,
            FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE,
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
            previous_state TEXT CHECK(previous_state IS NULL OR json_valid(previous_state)),
            new_state TEXT CHECK(new_state IS NULL OR json_valid(new_state)),
            processing_time_ms INTEGER,
            api_tokens_used INTEGER,
            is_human_corrected INTEGER DEFAULT 0,
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
            stack_trace TEXT CHECK(stack_trace IS NULL OR json_valid(stack_trace)),
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
            added_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT;
    """)

    # 9. Quarantine_Queue
    # -- Holds items that lack trust validation pending manual approval
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarantine_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_app TEXT NOT NULL,
            source_id TEXT NOT NULL,
            raw_metadata TEXT,
            proposed_category_id INTEGER,
            proposed_purpose_id INTEGER,
            proposed_entity_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("Verified Zero Trust tables (quarantine_queue) are initialized.")
    cursor.execute("COMMIT;")
    
    # Bootstrap check
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        print("Bootstrapping Zero Trust Scaffolding...")
        # Since zero_trust_defaults.json is in the root directory
        json_path = os.path.join(DEFAULTS_DIR, "zero_trust_defaults.json")
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        for p in data.get("universal_purposes", []):
            cursor.execute("INSERT INTO purposes (name, scope) VALUES (?, 'Universal')", (p,))
            
        blacklist = data.get("blacklist", {})
        for d in blacklist.get("domains", []):
            cursor.execute("INSERT INTO blacklist (type, pattern) VALUES ('domain', ?)", (d,))
        for p in blacklist.get("purposes", []):
            cursor.execute("INSERT INTO blacklist (type, pattern) VALUES ('purpose', ?)", (p,))
            
        for cat in data.get("categories", []):
            cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (cat["name"], cat.get("description", "")))
            cat_id = cursor.lastrowid
            for cp in cat.get("categorical_purposes", []):
                cursor.execute("INSERT INTO purposes (name, scope, category_id) VALUES (?, 'Categorical', ?)", (cp, cat_id))

    seed_default_configs(conn)
    seed_default_prompts(conn)
    
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
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('ui_gmail_filters',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('ui_gmail_filters', '["CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"]', 'Ignored Gmail labels'))
    
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('ui_ai_config',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('ui_ai_config', '{"drive_model": "gemini-2.5-flash-lite", "gmail_model": "gemini-2.5-flash-lite"}', 'LLM model selection'))
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('ui_post_processing',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('ui_post_processing', '{"auto_archive_gmail": false, "quarantine_unconfident": true}', 'Post-processing actions'))
    
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('nexus_task_list_id',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('nexus_task_list_id', '""', 'Google Tasks List ID for actionable items'))
    
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('default_view',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('default_view', 'dashboard', 'UI Startup View'))
    
    # Epic 5 Safe Mode Gatekeepers
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('feature_retention_sweeper',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('feature_retention_sweeper', '0', 'Safe Mode: Retention Sweeper'))
    
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('feature_drive_relocator',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('feature_drive_relocator', '0', 'Safe Mode: Drive Relocator'))
    
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('feature_materialization',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('feature_materialization', '0', 'Safe Mode: Materialization Pipeline'))
    
    cursor.execute("SELECT key FROM Config_System WHERE key = ?", ('feature_google_tasks',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_System (key, value, description) VALUES (?, ?, ?)",
            ('feature_google_tasks', '0', 'Safe Mode: Autonomous Google Tasks'))


def seed_default_prompts(conn: sqlite3.Connection) -> None:
    """
    Purpose: Seeds the default master prompts into the Config_Prompts table if they do not already exist.
    Expected Inputs: conn (sqlite3.Connection) - An active database connection.
    Expected Outputs: None. Modifies Config_Prompts table.
    """
    cursor = conn.cursor()
    
    prompts_to_seed = {
        'GMAIL': 'gmail_extraction.tmpl',
        'DRIVE_STAGE_1': 'drive_extraction_stage1.tmpl',
        'DRIVE_STAGE_2': 'drive_extraction_stage2.tmpl',
        'agent_profiler_personal': 'agent_profiler_personal.tmpl',
        'agent_profiler_commercial': 'agent_profiler_commercial.tmpl',
        'agent_classifier': 'agent_classifier.tmpl',
        'QUARANTINE_CONSOLIDATION': 'quarantine_consolidation.tmpl'
    }
    
    for target_app, filename in prompts_to_seed.items():
        try:
            cursor.execute("SELECT target_app FROM Config_Prompts WHERE target_app = ?", (target_app,))
            if cursor.fetchone() is None:
                prompt_text = get_prompt_template(filename)
                cursor.execute("INSERT INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", (target_app, prompt_text))
        except Exception as e:
            print(f"Failed to seed {target_app} prompt: {e}")

# Execute the initialization if the script is run directly.
if __name__ == "__main__":
    init_db()
