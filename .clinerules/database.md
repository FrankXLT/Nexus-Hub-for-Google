---
paths:
  - "backend/**/*.py"
  - "backend/**/*.sql"
  - "*.db"
---
# Unbending Database Mutation Laws
To prevent database corruption across rapid AI development cycles, modifications to the Layer 1 Database MUST follow these rules:

1. **Idempotency Over All:** Every schema manipulation statement must be safe to execute infinitely (e.g., `CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE`).
2. **Catch-All Exception Ban:** You are strictly forbidden from placing broad `try...except` passes over raw SQL execution strings to hide schema mismatches. If a query fails, halt execution immediately and trace the schema source in `db_init.py`.
3. **Re-Creation & Transactional Migration:** Because SQLite does not support adding `FOREIGN KEY` constraints via simple `ALTER TABLE` statements, any table manipulation affecting relations must use a multi-stage transaction script:
   - `BEGIN TRANSACTION;`
   - Create a temporary staging table with the modified schema, explicit data types, and `FOREIGN KEY` definitions.
   - Copy records: `INSERT INTO temporary_table SELECT ... FROM old_table;`
   - Drop the old table completely.
   - Rename the temporary staging table to the final production table name.
   - `COMMIT;`