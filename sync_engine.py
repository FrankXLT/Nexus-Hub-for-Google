"""
Sync Engine for Nexus Hub.
Fetches delta changes from Google Drive and Gmail to strictly avoid full polling.
Includes Quota Governor and Seed Ingestion logic.
"""

import sqlite3
import time
import json
import io
import datetime
from typing import Optional, Dict, Any, Tuple

from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from tenacity import retry, wait_exponential, stop_after_attempt

# Local imports
from auth import authenticate
from db_init import DB_PATH
from notifier import NexusNotifier

DAILY_QUOTA_LIMIT = 10000
PRIORITY_RESERVE_RATIO = 0.30

class QuotaGovernor:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = conn.cursor()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_quota_tracker()

    def _init_quota_tracker(self):
        self.cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES ('api_quota', '{\"date\": \"\", \"calls\": 0}', 'Daily API call tracking')")
        self.conn.commit()

    def record_api_call(self, cost: int = 1, entity_id: Optional[int] = None, entity_type: str = 'purpose'):
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT value FROM Config_System WHERE key = 'api_quota'")
        row = self.cursor.fetchone()
        quota_data = json.loads(row['value'])
        
        if quota_data.get('date') != today:
            quota_data = {'date': today, 'calls': 0}
            
        quota_data['calls'] += cost
        self.cursor.execute("UPDATE Config_System SET value = ? WHERE key = 'api_quota'", (json.dumps(quota_data),))
        
        # Track cost per entity
        if entity_id:
            if entity_type == 'purpose':
                self.cursor.execute("UPDATE Taxonomy_Purposes SET operation_cost = operation_cost + ? WHERE id = ?", (cost, entity_id))
            elif entity_type == 'correspondent':
                self.cursor.execute("UPDATE Taxonomy_Correspondents SET operation_cost = operation_cost + ? WHERE id = ?", (cost, entity_id))
                
        self.conn.commit()

    def can_process_historical(self) -> bool:
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT value FROM Config_System WHERE key = 'api_quota'")
        row = self.cursor.fetchone()
        quota_data = json.loads(row['value'])
        if quota_data.get('date') != today:
            return True
        
        calls = quota_data.get('calls', 0)
        return calls < (DAILY_QUOTA_LIMIT * (1.0 - PRIORITY_RESERVE_RATIO))

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def fetch_drive_changes(service: Resource, page_token: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Fetches Drive changes using a pageToken. Returns the changes and the new start page token.
    """
    results = service.changes().list(pageToken=page_token, spaces='drive').execute()
    new_page_token = results.get('newStartPageToken')
    return results, new_page_token

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def fetch_gmail_history(service: Resource, history_id: str) -> Tuple[Dict[str, Any], str]:
    """
    Fetches Gmail history using a historyId. Returns the history records and the new historyId.
    """
    results = service.users().history().list(userId='me', startHistoryId=history_id).execute()
    new_history_id = results.get('historyId', history_id)
    return results, str(new_history_id)

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def init_drive_page_token(service: Resource) -> str:
    """
    Fetches the initial start page token for Drive.
    """
    response = service.changes().getStartPageToken().execute()
    return response.get('startPageToken')

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def init_gmail_history_id(service: Resource) -> str:
    """
    Fetches the initial history ID for Gmail by getting the user profile.
    """
    profile = service.users().getProfile(userId='me').execute()
    return str(profile.get('historyId'))

def get_sync_state(cursor: sqlite3.Cursor, app_name: str) -> Optional[str]:
    """
    Reads the last known token from the Sync_State table.
    """
    cursor.execute("SELECT sync_token FROM Sync_State WHERE app_name = ?", (app_name,))
    row = cursor.fetchone()
    return row['sync_token'] if row else None

def update_sync_state(cursor: sqlite3.Cursor, app_name: str, sync_token: str) -> None:
    """
    Updates the Sync_State table with the new token.
    """
    now = int(time.time())
    cursor.execute("""
        INSERT INTO Sync_State (app_name, sync_token, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(app_name) DO UPDATE SET
            sync_token = excluded.sync_token,
            last_updated = excluded.last_updated
    """, (app_name, sync_token, now))

def ingest_taxonomy_seed(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Checks Google Drive for taxonomy_seed.json. If found, parses and updates the schema.
    """
    service = build('drive', 'v3', credentials=creds)
    governor.record_api_call()
    
    results = service.files().list(q="name='taxonomy_seed.json' and trashed=false", spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if not items:
        return
        
    print("Found taxonomy_seed.json in Drive. Ingesting...")
    file_id = items[0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        governor.record_api_call()
        
    seed_data = json.loads(fh.getvalue().decode('utf-8'))
    
    cursor = conn.cursor()
    
    categories = seed_data.get('categories', [])
    for cat in categories:
        cat_name = cat.get('name')
        cursor.execute("INSERT OR IGNORE INTO Taxonomy_Categories (name, is_gmail_enabled, is_drive_enabled) VALUES (?, 0, 0)", (cat_name,))
        cursor.execute("SELECT id FROM Taxonomy_Categories WHERE name = ?", (cat_name,))
        cat_id = cursor.fetchone()['id']
        
        for corr in cat.get('correspondents', []):
            corr_name = corr.get('name')
            division = corr.get('division', '')
            sending_subdomains = json.dumps(corr.get('sending_subdomains', []))
            physical_addresses = json.dumps(corr.get('physical_addresses', []))
            brand_colors = json.dumps(corr.get('brand_colors', []))
            
            cursor.execute("""
                INSERT OR IGNORE INTO Taxonomy_Correspondents (category_id, name, division, sending_subdomains, physical_addresses, brand_colors, is_gmail_enabled, is_drive_enabled)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            """, (cat_id, corr_name, division, sending_subdomains, physical_addresses, brand_colors))
            
            cursor.execute("SELECT id FROM Taxonomy_Correspondents WHERE category_id = ? AND name = ? AND division = ?", (cat_id, corr_name, division))
            corr_id_row = cursor.fetchone()
            if not corr_id_row: continue
            corr_id = corr_id_row['id']
            
            for purp in corr.get('purposes', []):
                purp_name = purp.get('name')
                schema = json.dumps(purp.get('custom_field_schema', {}))
                freq = purp.get('frequency_weight', 0)
                conf = purp.get('confidence_weight', 0.0)
                
                cursor.execute("""
                    INSERT OR IGNORE INTO Taxonomy_Purposes (correspondent_id, name, custom_field_schema, frequency_weight, confidence_weight, is_gmail_enabled, is_drive_enabled)
                    VALUES (?, ?, ?, ?, ?, 0, 0)
                """, (corr_id, purp_name, schema, freq, conf))
                
    conn.commit()
    print("Ingestion of taxonomy_seed.json complete.")

def process_file_with_governor(file_time: float, governor: QuotaGovernor) -> bool:
    """
    72-Hour Priority Lane check. Returns True if the file can be processed.
    """
    now = time.time()
    age_hours = (now - file_time) / 3600
    if age_hours < 72:
        return True # Priority Lane
    else:
        # Historical Backlog
        if not governor.can_process_historical():
            print("Governor: Historical quota limit reached. Throttling.")
            return False
        return True

def sync_drive(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Synchronizes Google Drive changes via delta fetching.
    """
    service = build('drive', 'v3', credentials=creds)
    cursor = conn.cursor()
    
    page_token = get_sync_state(cursor, 'drive')
    if not page_token:
        print("No Drive pageToken found in DB. Initializing new token...")
        governor.record_api_call()
        page_token = init_drive_page_token(service)
        update_sync_state(cursor, 'drive', page_token)
        conn.commit()
        print(f"Initialized Drive token to: {page_token}")
        return

    print(f"Fetching Drive changes since token: {page_token}")
    governor.record_api_call()
    changes, new_page_token = fetch_drive_changes(service, page_token)
    
    if 'changes' in changes:
        print(f"Found {len(changes['changes'])} Drive changes.")
        for change in changes['changes']:
            # Example timestamp extraction if available, defaulting to now for simplicity
            file_time = time.time() 
            if not process_file_with_governor(file_time, governor):
                continue
            
            print(f" - Drive Change: File ID {change.get('fileId')}")
            governor.record_api_call(cost=1)
    else:
        print("No new Drive changes.")
    
    if new_page_token and new_page_token != page_token:
        update_sync_state(cursor, 'drive', new_page_token)
        conn.commit()
        print(f"Updated Drive token to: {new_page_token}")

def sync_gmail(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Synchronizes Gmail changes via history delta fetching.
    """
    service = build('gmail', 'v1', credentials=creds)
    cursor = conn.cursor()
    
    history_id = get_sync_state(cursor, 'gmail')
    if not history_id:
        print("No Gmail historyId found in DB. Initializing new historyId...")
        governor.record_api_call()
        history_id = init_gmail_history_id(service)
        update_sync_state(cursor, 'gmail', history_id)
        conn.commit()
        print(f"Initialized Gmail historyId to: {history_id}")
        return

    print(f"Fetching Gmail history since ID: {history_id}")
    governor.record_api_call()
    history, new_history_id = fetch_gmail_history(service, history_id)
    
    if 'history' in history:
        print(f"Found {len(history['history'])} Gmail history records.")
        for record in history['history']:
            file_time = time.time()
            if not process_file_with_governor(file_time, governor):
                continue
                
            print(f" - Gmail History Record: {record.get('id')}")
            governor.record_api_call(cost=1)
    else:
        print("No new Gmail history.")
            
    if new_history_id and new_history_id != history_id:
        update_sync_state(cursor, 'gmail', new_history_id)
        conn.commit()
        print(f"Updated Gmail historyId to: {new_history_id}")

def run_sync() -> None:
    """
    Main entry point for the Delta Synchronization Engine.
    """
    print("Starting synchronization engine...")
    creds = authenticate()
    if not creds or not creds.valid:
        print("Authentication failed. Ensure token is valid.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    
    governor = QuotaGovernor(conn)
    
    try:
        ingest_taxonomy_seed(creds, conn, governor)
        sync_drive(creds, conn, governor)
        sync_gmail(creds, conn, governor)
    except Exception as e:
        print(f"Synchronization error occurred: {e}")
    finally:
        conn.close()
        print("Synchronization engine completed.")

if __name__ == "__main__":
    run_sync()
te3.OperationalError as e:
        error_msg = f"Database Lock or Operational Error: {e}"
        print(error_msg)
        notifier.send_urgent_webhook({"title": "Nexus Hub: Database Lock", "message": error_msg, "priority": 1})
    except Exception as e:
        error_msg = f"Synchronization error occurred: {e}"
        print(error_msg)
        notifier.send_urgent_webhook({"title": "Nexus Hub: Sync Error", "message": error_msg, "priority": 0})
    finally:
        if 'conn' in locals():
            conn.close()
        print("Synchronization engine completed.")

if __name__ == "__main__":
    run_sync()
