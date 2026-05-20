import sqlite3
import os
import json

# Setup
DB_PATH = os.getenv("NEXUS_DB_PATH", "nexus-live.db")

def sample_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("# Database Row Sampling Report\n")
        
        for table in tables:
            print(f"## Table: {table}\n")
            
            # Get first 3
            cursor.execute(f"SELECT * FROM {table} ORDER BY rowid ASC LIMIT 3")
            first_3 = [dict(r) for r in cursor.fetchall()]
            
            # Get last 3
            cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 3")
            last_3 = [dict(r) for r in cursor.fetchall()]
            last_3.reverse()
            
            rows = first_3 + last_3
            
            if not rows:
                print("Table is empty.\n")
                continue
                
            # Headers
            headers = list(rows[0].keys())
            print("| " + " | ".join(headers) + " |")
            print("| " + " | ".join(["---"] * len(headers)) + " |")
            
            for row in rows:
                print("| " + " | ".join([str(row.get(h, "")) for h in headers]) + " |")
            print("\n")
            
        conn.close()
    except Exception as e:
        print(f"Error sampling DB: {e}")

if __name__ == "__main__":
    sample_db()
