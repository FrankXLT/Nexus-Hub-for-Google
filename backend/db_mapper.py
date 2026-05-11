import sqlite3
import os

DB_PATH = "~/nexus/shared/data/nexus.db"
OUTPUT_FILE = "~/nexus/db_report.md"

def generate_report():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row['name'] for row in cursor.fetchall()]

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Nexus Database Architecture Report\n\n")
        
        # --- MERMAID ER DIAGRAM ---
        f.write("## Entity-Relationship Diagram\n")
        f.write("```mermaid\nerDiagram\n")

        # Map Foreign Keys for relationships
        for table in tables:
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            for fk in cursor.fetchall():
                f.write(f"    {fk['table']} ||--o{{ {table} : \"{fk['to']} -> {fk['from']}\"\n")

        # Map Table Schemas
        for table in tables:
            f.write(f"    {table} {{\n")
            cursor.execute(f"PRAGMA table_info({table})")
            for col in cursor.fetchall():
                pk_marker = " PK" if col['pk'] else ""
                # Sanitize types for Mermaid compatibility
                col_type = col['type'].split('(')[0] if col['type'] else "TEXT"
                f.write(f"        {col_type} {col['name']}{pk_marker}\n")
            f.write("    }\n")

        f.write("```\n\n")

        # --- SAMPLE DATA DUMP ---
        f.write("## Sample Records (Limit 3 per table)\n\n")
        for table in tables:
            f.write(f"### {table}\n")
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            rows = cursor.fetchall()
            
            if not rows:
                f.write("*No records found.*\n\n")
                continue

            cols = list(rows[0].keys())
            f.write("| " + " | ".join(cols) + " |\n")
            f.write("|" + "|".join(["---"] * len(cols)) + "|\n")
            
            for row in rows:
                # Truncate long text and remove newlines to protect markdown tables
                vals = [str(row[c]).replace('\n', ' ')[:60] + ('...' if len(str(row[c])) > 60 else '') if row[c] is not None else 'NULL' for c in cols]
                f.write("| " + " | ".join(vals) + " |\n")
            f.write("\n")

    conn.close()
    print(f"Success: Database architecture report generated at {OUTPUT_FILE}")

if __name__ == '__main__':
    generate_report()