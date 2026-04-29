import os
import sqlite3
import datetime
from googleapiclient.discovery import build
from auth import get_credentials
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("NEXUS_DB_PATH", "nexus.db")

def run_retention_sweep():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Config_Retention_Rules WHERE is_active = 1")
    rules = cursor.fetchall()

    if not rules:
        print("No active retention rules found.")
        return

    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)

    for rule in rules:
        target_category = rule['target_category']
        action = rule['action']
        days_old = rule['days_old']

        # E.g., older_than:30d label:CATEGORY_PROMOTIONS
        query = f"older_than:{days_old}d"
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
            
            if not messages:
                print("No messages matched the rule.")
                continue
                
            # Batch process messages
            ids = [msg['id'] for msg in messages]
            
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

if __name__ == "__main__":
    run_retention_sweep()