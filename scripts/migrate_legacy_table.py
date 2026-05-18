import sqlite3
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from db_init import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_legacy_label_migration():
    """
    Migrates the Legacy_Label_Migration table to add classification and extracted_entity_name columns.
    Follows Unbending Database Mutation Laws.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()
    
    logger.info("Starting Legacy_Label_Migration migration...")
    
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Create temporary staging table with new schema
        cursor.execute("""
            CREATE TABLE Legacy_Label_Migration_new (
                label_id TEXT PRIMARY KEY,
                label_name TEXT NOT NULL,
                mapped_category_id INTEGER,
                mapped_purpose_id INTEGER,
                ai_confidence REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',
                last_evaluated TEXT DEFAULT CURRENT_TIMESTAMP,
                classification TEXT DEFAULT 'noise',
                extracted_entity_name TEXT DEFAULT NULL,
                FOREIGN KEY(mapped_category_id) REFERENCES categories(id),
                FOREIGN KEY(mapped_purpose_id) REFERENCES purposes(id)
            ) STRICT;
        """)
        
        # 2. Copy data
        cursor.execute("""
            INSERT INTO Legacy_Label_Migration_new 
            (label_id, label_name, mapped_category_id, mapped_purpose_id, ai_confidence, status, last_evaluated)
            SELECT label_id, label_name, mapped_category_id, mapped_purpose_id, ai_confidence, status, last_evaluated
            FROM Legacy_Label_Migration;
        """)
        
        # 3. Drop old table
        cursor.execute("DROP TABLE Legacy_Label_Migration;")
        
        # 4. Rename staging to final
        cursor.execute("ALTER TABLE Legacy_Label_Migration_new RENAME TO Legacy_Label_Migration;")
        
        cursor.execute("COMMIT;")
        logger.info("Migration successful.")
        
    except Exception as e:
        cursor.execute("ROLLBACK;")
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_legacy_label_migration()
