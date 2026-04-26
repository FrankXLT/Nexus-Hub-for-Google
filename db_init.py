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
    
    conn.commit()
    conn.close()
    print(f"Database initialization complete: {db_path} with STRICT tables and WAL mode enabled.")

if __name__ == "__main__":
    init_db()
