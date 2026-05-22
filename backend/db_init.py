"""
Module: db_init.py
Purpose: Initializes the Nexus SQLite database.
Enforces STRICT tables, WAL journaling mode, and JSON data type validation.
"""
import sqlite3
import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the directory where db_init.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Navigate up to the root to find the DEFAULTS folder
DEFAULTS_DIR = os.path.join(BASE_DIR, "..", "DEFAULTS")

def get_prompt_template(filename):
    """
    [Layer 1: Core Storage & Schema Integrity]
    Reads a prompt template from the DEFAULTS directory.

    Args:
        filename (str): Name of the template file.

    Returns:
        str: Content of the prompt template.
    """
    path = os.path.join(DEFAULTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# Read DB path from environment variable, default to 'nexus.db' if not set
DB_PATH = os.getenv("NEXUS_DB_PATH", "nexus.db")

def column_exists(cursor, table_name, column_name):
    """
    [Layer 1: Core Storage & Schema Integrity]
    Checks if a column exists in a specific table.

    Args:
        cursor (sqlite3.Cursor): Database cursor.
        table_name (str): Target table.
        column_name (str): Target column.

    Returns:
        bool: True if column exists, False otherwise.
    """
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def add_column_if_not_exists(cursor, table_name, column_name, column_def):
    """
    [Layer 1: Core Storage & Schema Integrity]
    Idempotently adds a column to a table if it does not already exist.

    Args:
        cursor (sqlite3.Cursor): Database cursor.
        table_name (str): Target table.
        column_name (str): Target column.
        column_def (str): Column definition (type, defaults, etc.).

    Returns:
        None.
    """
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};")
        logger.info(f"Added column {column_name} to {table_name}.")
def init_db(db_path: str = DB_PATH) -> None:
    """
    Purpose: Connects to the SQLite database and executes the table creation schemas.
             Applies WAL mode and enables foreign key constraints.
    Expected Inputs:
        db_path (str): The path to the SQLite database file.
    Expected Outputs: None. Creates or updates the database schema on disk.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    conn = sqlite3.connect(db_path, timeout=20)
    conn.row_factory = sqlite3.Row
    
    # Enable Write-Ahead Logging and synchronous=NORMAL for concurrent reading/writing
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    logger.info("Verified SQLite WAL mode and synchronous=NORMAL active.")
    # Enable foreign key constraint enforcement
    conn.execute("PRAGMA foreign_keys = ON;")
    
    cursor = conn.cursor()
    cursor.execute("BEGIN TRANSACTION;")
    
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

    # 3b. Config_Retention_Rules
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Config_Retention_Rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_category TEXT NOT NULL,
            action TEXT NOT NULL,
            days_old INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1
        ) STRICT;
    """)

    # 4. Taxonomy_Categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            show_in_nav INTEGER DEFAULT 1,
            show_in_msglist INTEGER DEFAULT 1,
            nav_condition TEXT DEFAULT 'always',
            top_entities_limit INTEGER DEFAULT 5,
            top_entities_sort TEXT DEFAULT 'received',
            top_entities_importance_filter TEXT DEFAULT 'nexus',
            min_confidence_threshold REAL DEFAULT 0.95,
            gmail_label_id TEXT DEFAULT NULL
        ) STRICT;
    """)

    # 4c. Taxonomy_Purposes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purposes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            scope TEXT NOT NULL,
            show_in_nav INTEGER DEFAULT 1,
            show_in_msglist INTEGER DEFAULT 1,
            nexus_importance_rule TEXT DEFAULT 'inherit_gmail',
            default_action TEXT DEFAULT 'none',
            default_star_color TEXT DEFAULT NULL,
            min_confidence_threshold REAL DEFAULT 0.95,
            risk_level TEXT DEFAULT 'Medium',
            retention_days INTEGER DEFAULT 365,
            category_id INTEGER,
            gmail_label_id TEXT DEFAULT NULL,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        ) STRICT;
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
            is_profiled INTEGER DEFAULT 0,
            ingestion_source TEXT DEFAULT 'unknown',
            is_favorite INTEGER DEFAULT 0,
            gmail_label_id TEXT DEFAULT NULL,
            flatten_gmail_label BOOLEAN DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (parent_entity_id) REFERENCES entities (id)
        );
    """)

    # Idempotent column additions using the helper
    add_column_if_not_exists(cursor, "entities", "nexus_state", "TEXT DEFAULT 'active'")
    add_column_if_not_exists(cursor, "entities", "workspace_alias", "TEXT DEFAULT NULL")
    add_column_if_not_exists(cursor, "entities", "show_in_gmail_nav", "BOOLEAN DEFAULT 1")
    add_column_if_not_exists(cursor, "entities", "show_in_gmail_msg", "BOOLEAN DEFAULT 1")
    add_column_if_not_exists(cursor, "entities", "use_in_drive_structure", "BOOLEAN DEFAULT 1")
    add_column_if_not_exists(cursor, "entities", "is_profiled", "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, "entities", "ingestion_source", "TEXT DEFAULT 'unknown'")
    add_column_if_not_exists(cursor, "entities", "is_favorite", "INTEGER DEFAULT 0")
    add_column_if_not_exists(cursor, "entities", "gmail_label_id", "TEXT DEFAULT NULL")
    add_column_if_not_exists(cursor, "entities", "flatten_gmail_label", "BOOLEAN DEFAULT 0")
    add_column_if_not_exists(cursor, "categories", "gmail_label_id", "TEXT DEFAULT NULL")
    add_column_if_not_exists(cursor, "purposes", "gmail_label_id", "TEXT DEFAULT NULL")

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

    core_pipelines = ['gmail', 'drive', 'materialization', 'retention_sweeper', 'google_tasks']
    for pipeline in core_pipelines:
        cursor.execute("""
            INSERT OR IGNORE INTO pipeline_config (pipeline_name, is_enabled, settings_json)
            VALUES (?, 0, '{}')
        """, (pipeline,))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            UNIQUE(type, pattern)
        );
    """)
    
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
            gmail_important INTEGER DEFAULT 0,
            nexus_important INTEGER DEFAULT 0,
            gmail_starred INTEGER DEFAULT 0,
            nexus_action_state TEXT DEFAULT 'none',
            nexus_star_color TEXT DEFAULT NULL,
            ai_confidence REAL DEFAULT 0.0,
            is_quarantined INTEGER DEFAULT 0,
            needs_reprocessing INTEGER DEFAULT 0,
            FOREIGN KEY (purpose_id) REFERENCES purposes (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_artifact_id) REFERENCES Workspace_Artifacts (artifact_id) ON DELETE SET NULL
        ) STRICT;
    """)
    
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Ingestion_Queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            added_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pipeline_Locks (
            artifact_id TEXT PRIMARY KEY,
            locked_by_activity TEXT,
            locked_at REAL
        ) STRICT;
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Legacy_Label_Migration (
            label_id TEXT PRIMARY KEY,
            label_name TEXT NOT NULL,
            mapped_category_id INTEGER,
            mapped_purpose_id INTEGER,
            ai_confidence REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            last_evaluated TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(mapped_category_id) REFERENCES categories(id),
            FOREIGN KEY(mapped_purpose_id) REFERENCES purposes(id)
        ) STRICT;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Activity_Ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT NOT NULL,
            artifact_id TEXT,
            pipeline_source TEXT,
            event_timestamp REAL,
            step_name TEXT,
            status TEXT,
            execution_time_ms INTEGER,
            tokens_used INTEGER,
            event_payload BLOB
        ) STRICT;
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_ledger_activity_id ON Activity_Ledger(activity_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_ledger_artifact_id ON Activity_Ledger(artifact_id);")
    
    cursor.execute("COMMIT;")
    
    seed_default_configs(conn)
    seed_default_prompts(conn)
    seed_taxonomy(conn)
    
    conn.commit()
    conn.close()
    print(f"Database initialization complete: {db_path} with STRICT tables and WAL mode enabled.")

def seed_default_configs(conn: sqlite3.Connection) -> None:
    """
    [Layer 1: Core Storage & Schema Integrity]
    Seeds the Config_System table with default UI configurations if not already present.

    Args:
        conn (sqlite3.Connection): Database connection.

    Returns:
        None.
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
    [Layer 1: Core Storage & Schema Integrity]
    Seeds the Config_Prompts table with default LLM system prompts from templates.

    Args:
        conn (sqlite3.Connection): Database connection.

    Returns:
        None.
    """
    cursor = conn.cursor()
    
    prompts_to_seed = {
        'GMAIL': 'gmail_extraction.tmpl',
        'DRIVE_STAGE_1': 'drive_extraction_stage1.tmpl',
        'DRIVE_STAGE_2': 'drive_extraction_stage2.tmpl',
        'agent_profiler_personal': 'agent_profiler_personal.tmpl',
        'agent_profiler_commercial': 'agent_profiler_commercial.tmpl',
        'agent_classifier': 'agent_classifier.tmpl',
        'QUARANTINE_CONSOLIDATION': 'quarantine_consolidation.tmpl',
        'DEDUPLICATE_LEGACY': 'deduplicate_legacy.tmpl',
        'PROFILE_AND_MAP': 'profile_and_map_entities.tmpl',
        'MIGRATE_LEGACY_LABEL': 'migrate_legacy_label.tmpl'
    }
    
    for target_app, filename in prompts_to_seed.items():
        cursor.execute("SELECT target_app FROM Config_Prompts WHERE target_app = ?", (target_app,))
        if cursor.fetchone() is None:
            prompt_text = get_prompt_template(filename)
            cursor.execute("INSERT INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", (target_app, prompt_text))

def seed_taxonomy(conn: sqlite3.Connection) -> None:
    """
    [Layer 1: Core Storage & Schema Integrity]
    Idempotent seeding of taxonomy categories and purposes from zero_trust_defaults.json.

    Args:
        conn (sqlite3.Connection): Database connection.

    Returns:
        None.
    """
    cursor = conn.cursor()
    
    # Idempotent check
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] > 0:
        logger.info("Taxonomy already seeded. Skipping.")
        return

    json_path = os.path.join(DEFAULTS_DIR, "zero_trust_defaults.json")
    if not os.path.exists(json_path):
        logger.warning(f"{json_path} not found. Skipping taxonomy seeding.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        defaults = json.load(f)

    universal_purposes = defaults.get("universal_purposes", [])
    
    blacklist = defaults.get("blacklist", {})
    for d in blacklist.get("domains", []):
        cursor.execute("INSERT OR IGNORE INTO blacklist (type, pattern) VALUES ('domain', ?)", (d,))
    for p in blacklist.get("purposes", []):
        cursor.execute("INSERT OR IGNORE INTO blacklist (type, pattern) VALUES ('purpose', ?)", (p,))

    for cat in defaults.get("categories", []):
        cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)", 
                       (cat["name"], cat.get("description", "")))
        cat_id = cursor.lastrowid
        
        all_purposes = set(universal_purposes + cat.get("categorical_purposes", []))
        
        for purp_name in all_purposes:
            scope = 'Universal' if purp_name in universal_purposes else 'Categorical'
            cursor.execute("""
                INSERT INTO purposes (category_id, name, description, scope, risk_level, retention_days)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cat_id, purp_name, f"Standard {purp_name} documents", scope, "Medium", 365))
    
    conn.commit()
    logger.info("Zero Trust Taxonomy seeded successfully.")

if __name__ == "__main__":
    init_db()
