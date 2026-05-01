"""
Module: retention_worker.py
Purpose: Contains logic for running scheduled retention sweeps, archiving or trashing old messages based on configured rules.
"""

import os
import sqlite3
import datetime
from googleapiclient.discovery import build
from auth import get_credentials
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("NEXUS_DB_PATH", "nexus.db")

def is_feature_enabled(cursor: sqlite3.Cursor, feature_key: str) -> bool:
    """
    Purpose: Checks if a specific feature is enabled in the system configuration table.
    Expected Inputs: 
        cursor (sqlite3.Cursor) - A database cursor.
        feature_key (str) - The key of the feature to check.
    Expected Outputs: bool - True if enabled, False otherwise.
    """
    cursor.execute("SELECT value FROM Config_System WHERE key = ?", (feature_key,))
    row = cursor.fetchone()
    # Return true if the row exists and the value signifies true.
    return row is not None and row['value'] in ('1', 'true', 'True')

def run_retention_sweep():
    """
    Purpose: Executes the retention sweep, processing active retention rules to archive or trash old messages.
    Expected Inputs: None. Reads from database and calls Gmail API.
    Expected Outputs: None.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Epic 5 Gatekeeper
    # Check if the retention sweeper feature is enabled before running.
    if not is_feature_enabled(cursor, 'feature_retention_sweeper'):
        print("Safe Mode Bypass: Retention Sweeper is disabled. Exiting.")
        conn.close()
        return

    cursor.execute("SELECT * FROM Config_Retention_Rules WHERE is_active = 1")
    rules = cursor.fetchall()

    # Verify if there are any active rules.
    if not rules:
        print("No active retention rules found.")
        return

    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)

    # Process each rule fetched from the database.
    for rule in rules:
        target_category = rule['target_category']
        action = rule['action']
        days_old = rule['days_old']

        # E.g., older_than:30d label:CATEGORY_PROMOTIONS
        query = f"older_than:{days_old}d"
        # Append specific labels to the query if applicable.
        if target_category and target_category != 'ALL':
             # We assume target_category is a valid label or search term like label:CATEGORY_PROMOTIONS
             query += f" label:{target_category}"
        elif target_category == 'ALL':
             pass # No specific label
        else:
             query += f" {target_category}"

        print(f"Executing rule ID {rule['id']} - Action: {action} Query: {query}")
        
        try:
            results = service.users().messages().list(userId='me', q=query, maxResults=500).execute()
            messages = results.get('messages', [])
            
            # Skip to the next rule if no messages match.
            if not messages:
                print("No messages matched the rule.")
                continue
                
            # Batch process messages
            ids = [msg['id'] for msg in messages]
            
            # Decide action based on rule type.
            if action.upper() == 'ARCHIVE':
                # Remove INBOX label
                batch_modify_body = {
                    "ids": ids,
                    "removeLabelIds": ["INBOX"]
                }
                service.users().messages().batchModify(userId='me', body=batch_modify_body).execute()
                print(f"Archived {len(ids)} messages.")
                
            elif action.upper() == 'TRASH':
                # Move to trash
                batch_modify_body = {
                    "ids": ids,
                    "addLabelIds": ["TRASH"],
                    "removeLabelIds": ["INBOX"]
                }
                service.users().messages().batchModify(userId='me', body=batch_modify_body).execute()
                print(f"Trashed {len(ids)} messages.")
                
        except Exception as e:
            print(f"Error executing rule {rule['id']}: {e}")

# Run the sweep if the script is invoked directly.
if __name__ == "__main__":
    run_retention_sweep()
