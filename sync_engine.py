"""
Sync Engine for Nexus Hub.
Fetches delta changes from Google Drive and Gmail to strictly avoid full polling.
"""

import sqlite3
import time
from typing import Optional, Dict, Any, Tuple

from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials
from tenacity import retry, wait_exponential, stop_after_attempt

# Local imports
from auth import authenticate
from db_init import DB_PATH

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

def sync_drive(creds: Credentials, conn: sqlite3.Connection) -> None:
    """
    Synchronizes Google Drive changes via delta fetching.
    """
    service = build('drive', 'v3', credentials=creds)
    cursor = conn.cursor()
    
    page_token = get_sync_state(cursor, 'drive')
    if not page_token:
        print("No Drive pageToken found in DB. Initializing new token...")
        page_token = init_drive_page_token(service)
        update_sync_state(cursor, 'drive', page_token)
        conn.commit()
        print(f"Initialized Drive token to: {page_token}")
        return

    print(f"Fetching Drive changes since token: {page_token}")
    changes, new_page_token = fetch_drive_changes(service, page_token)
    
    if 'changes' in changes:
        print(f"Found {len(changes['changes'])} Drive changes.")
        # Logging changes (processing logic will go here in future phases)
        for change in changes['changes']:
            print(f" - Drive Change: File ID {change.get('fileId')}")
    else:
        print("No new Drive changes.")
    
    if new_page_token and new_page_token != page_token:
        update_sync_state(cursor, 'drive', new_page_token)
        conn.commit()
        print(f"Updated Drive token to: {new_page_token}")

def sync_gmail(creds: Credentials, conn: sqlite3.Connection) -> None:
    """
    Synchronizes Gmail changes via history delta fetching.
    """
    service = build('gmail', 'v1', credentials=creds)
    cursor = conn.cursor()
    
    history_id = get_sync_state(cursor, 'gmail')
    if not history_id:
        print("No Gmail historyId found in DB. Initializing new historyId...")
        history_id = init_gmail_history_id(service)
        update_sync_state(cursor, 'gmail', history_id)
        conn.commit()
        print(f"Initialized Gmail historyId to: {history_id}")
        return

    print(f"Fetching Gmail history since ID: {history_id}")
    history, new_history_id = fetch_gmail_history(service, history_id)
    
    if 'history' in history:
        print(f"Found {len(history['history'])} Gmail history records.")
        # Logging history records (processing logic will go here in future phases)
        for record in history['history']:
            print(f" - Gmail History Record: {record.get('id')}")
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
    
    try:
        sync_drive(creds, conn)
        sync_gmail(creds, conn)
    except Exception as e:
        print(f"Synchronization error occurred: {e}")
    finally:
        conn.close()
        print("Synchronization engine completed.")

if __name__ == "__main__":
    run_sync()
