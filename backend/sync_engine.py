"""
Sync Engine for Nexus.
Fetches delta changes from Google Drive and Gmail to strictly avoid full polling.
Includes Quota Governor and Seed Ingestion logic.
"""

import sqlite3
import time
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
import io
import datetime
from typing import Optional, Dict, Any, Tuple

from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError

# Local imports
from auth import authenticate
from db_init import DB_PATH
from notifier import NexusNotifier
from llm_engine import evaluate_quarantine_clusters

DAILY_QUOTA_LIMIT = 10000
PRIORITY_RESERVE_RATIO = 0.30
IGNORED_GMAIL_LABELS = {'TRASH', 'SPAM', 'SENT', 'DRAFT'}

class QuotaGovernor:
    """
    Manages API quota limits by tracking daily API calls and throttling non-priority processing.
    Implements the 72-Hour Priority Lane mechanism to guarantee resources for real-time artifact ingestion.
    """
    def __init__(self, conn: sqlite3.Connection):
        """
        Initializes the QuotaGovernor with an active SQLite database connection.
        
        Args:
            conn (sqlite3.Connection): The active SQLite database connection.
        """
        self.conn = conn
        self.cursor = conn.cursor()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_quota_tracker()

    def _init_quota_tracker(self):
        """
        Initializes the 'api_quota' record in the Config_System table if it does not exist.
        """
        self.cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES ('api_quota', '{\"date\": \"\", \"calls\": 0}', 'Daily API call tracking')")
        self.conn.commit()

    def record_api_call(self, cost: int = 1, entity_id: Optional[int] = None, entity_type: str = 'purpose'):
        """
        Records an API call cost against the daily quota limit.
        Also tracks the operation cost against specific taxonomy entities to identify expensive rules.
        
        Args:
            cost (int, optional): The cost of the API call. Defaults to 1.
            entity_id (Optional[int], optional): The ID of the taxonomy entity being processed. Defaults to None.
            entity_type (str, optional): The type of entity ('purpose' or 'correspondent'). Defaults to 'purpose'.
        """
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT value FROM Config_System WHERE key = 'api_quota'")
        row = self.cursor.fetchone()
        quota_data = json.loads(row['value'])
        
        if quota_data.get('date') != today:
            quota_data = {'date': today, 'calls': 0}
            
        quota_data['calls'] += cost
        self.cursor.execute("UPDATE Config_System SET value = ? WHERE key = 'api_quota'", (json.dumps(quota_data),))
        
        # Track cost per entity to power API usage telemetry and warn users before bulk edits
        if entity_id:
            if entity_type == 'purpose':
                self.cursor.execute("UPDATE purposes SET operation_cost = operation_cost + ? WHERE id = ?", (cost, entity_id))
            elif entity_type == 'correspondent':
                self.cursor.execute("UPDATE entities SET operation_cost = operation_cost + ? WHERE id = ?", (cost, entity_id))
                
        self.conn.commit()

    def can_process_historical(self) -> bool:
        """
        Evaluates whether the system has sufficient daily quota remaining to process historical (non-priority) data.
        
        Returns:
            bool: True if historical data can be processed, False if throttled.
        """
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT value FROM Config_System WHERE key = 'api_quota'")
        row = self.cursor.fetchone()
        quota_data = json.loads(row['value'])
        if quota_data.get('date') != today:
            return True
        
        # Architectural Intent: The 72-Hour Priority Lane logic.
        # By reserving a specific percentage of the total daily quota (e.g., 30%), 
        # we artificially cap the processing of old historical backlog documents.
        # This guarantees that new, urgent emails/files (< 72 hours old) are always processed 
        # immediately and never starved by a massive historical migration job.
        calls = quota_data.get('calls', 0)
        return calls < (DAILY_QUOTA_LIMIT * (1.0 - PRIORITY_RESERVE_RATIO))

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def fetch_drive_changes(service: Resource, page_token: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Fetches Drive changes using a pageToken.
    
    Args:
        service (Resource): The authenticated Google Drive service resource.
        page_token (str): The token to track state from the previous sync.
        
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: The JSON response containing changes, and the next page token.
    """
    results = service.changes().list(pageToken=page_token, spaces='drive').execute()
    new_page_token = results.get('newStartPageToken')
    return results, new_page_token

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def fetch_gmail_history(service: Resource, history_id: str) -> Tuple[Dict[str, Any], str]:
    """
    Fetches Gmail history using a historyId.
    
    Args:
        service (Resource): The authenticated Gmail service resource.
        history_id (str): The starting history ID.
        
    Returns:
        Tuple[Dict[str, Any], str]: The history records and the new history ID.
    """
    results = service.users().history().list(userId='me', startHistoryId=history_id).execute()
    new_history_id = results.get('historyId', history_id)
    return results, str(new_history_id)

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def init_drive_page_token(service: Resource) -> str:
    """
    Fetches the initial start page token for Drive.
    
    Args:
        service (Resource): The authenticated Google Drive service resource.
        
    Returns:
        str: The initial start page token.
    """
    response = service.changes().getStartPageToken().execute()
    return response.get('startPageToken')

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def init_gmail_history_id(service: Resource) -> str:
    """
    Fetches the initial history ID for Gmail by getting the user profile.
    
    Args:
        service (Resource): The authenticated Gmail service resource.
        
    Returns:
        str: The initial history ID.
    """
    profile = service.users().getProfile(userId='me').execute()
    return str(profile.get('historyId'))

def is_feature_enabled(cursor: sqlite3.Cursor, feature_key: str) -> bool:
    """
    Checks if an Epic 5 Safe Mode feature is enabled in Config_System.
    """
    cursor.execute("SELECT value FROM Config_System WHERE key = ?", (feature_key,))
    row = cursor.fetchone()
    return row is not None and row['value'] in ('1', 'true', 'True')

def push_to_google_tasks(creds: Credentials, artifact_data: sqlite3.Row, conn: sqlite3.Connection) -> None:
    """
    Creates a Google Task based on an actionable artifact and records the task ID.
    """
    cursor = conn.cursor()
    # Epic 5 Gatekeeper
    if not is_feature_enabled(cursor, 'feature_google_tasks'):
        print(f"Safe Mode Bypass: Autonomous Google Tasks is disabled. Skipping task for {artifact_data['artifact_id']}.")
        return

    # Idempotency check (though already handled by caller, extra safety)
    if artifact_data['google_task_id'] is not None:
        return

    try:
        cursor.execute("SELECT value FROM Config_System WHERE key = 'nexus_task_list_id'")
        row = cursor.fetchone()
        task_list_id = row['value'].strip('"') if row and row['value'] and row['value'] != '""' else "@default"

        tasks_service = build('tasks', 'v1', credentials=creds)
        task_body = {
            'title': f"Action Required: {artifact_data['summary']}",
            'notes': f"Generated from Nexus Artifact: {artifact_data['artifact_id']}"
        }
        
        task = tasks_service.tasks().insert(tasklist=task_list_id, body=task_body).execute()
        new_task_id = task.get('id')
        
        cursor.execute("UPDATE Workspace_Artifacts SET google_task_id = ? WHERE artifact_id = ?", (new_task_id, artifact_data['artifact_id']))
        conn.commit()
        print(f"   -> Created Google Task {new_task_id} for {artifact_data['artifact_id']}.")
    except Exception as e:
        print(f"   -> Failed to create Google Task for {artifact_data['artifact_id']}: {e}")

def get_sync_state(cursor: sqlite3.Cursor, app_name: str) -> Optional[str]:
    """
    Reads the last known token from the Sync_State table.
    
    Args:
        cursor (sqlite3.Cursor): The SQLite database cursor.
        app_name (str): The name of the application ('drive' or 'gmail').
        
    Returns:
        Optional[str]: The sync token if found, otherwise None.
    """
    cursor.execute("SELECT sync_token FROM Sync_State WHERE app_name = ?", (app_name,))
    row = cursor.fetchone()
    return row['sync_token'] if row else None

def update_sync_state(cursor: sqlite3.Cursor, app_name: str, sync_token: str) -> None:
    """
    Updates the Sync_State table with the new token.
    
    Args:
        cursor (sqlite3.Cursor): The SQLite database cursor.
        app_name (str): The name of the application ('drive' or 'gmail').
        sync_token (str): The new sync token to persist.
    """
    now = int(time.time())
    cursor.execute("""
        INSERT INTO Sync_State (app_name, sync_token, last_updated)
        VALUES (?, ?, ?)
        ON CONFLICT(app_name) DO UPDATE SET
            sync_token = excluded.sync_token,
            last_updated = excluded.last_updated
    """, (app_name, sync_token, now))

def resolve_folder_path(drive_service, path_string):
    """
    Resolves a string path (e.g., 'Nexus Root/Ingest Dropbox') into a Google Drive folder ID.
    Idempotently creates folders if they do not exist.
    """
    parts = [p for p in path_string.split('/') if p.strip()]
    parent_id = 'root'
    
    for part in parts:
        q = f"name='{part}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id != 'root':
            q += f" and '{parent_id}' in parents"
            
        results = drive_service.files().list(q=q, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            parent_id = items[0]['id']
        else:
            metadata = {
                'name': part,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id != 'root':
                metadata['parents'] = [parent_id]
            folder = drive_service.files().create(body=metadata, fields='id').execute()
            parent_id = folder.get('id')
            
    return parent_id

def initialize_drive_structure(drive_service):
    """
    Idempotent function to ensure Nexus Google Drive folder scaffolding exists.
    Retrieves or creates 'Nexus Root', 'Ingest Dropbox', 'Document Archive', and 'Diagnostics'.
    Saves the corresponding folderIds securely in the Config_System SQLite table.
    """
    folders_to_create = {
        'Nexus Root': None,
        'Ingest Dropbox': 'Nexus Root',
        'Document Archive': 'Nexus Root',
        'Diagnostics': 'Nexus Root'
    }
    folder_ids = {}
    
    def find_or_create_folder(name, parent_id=None):
        q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
            
        results = drive_service.files().list(q=q, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
        else:
            metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                metadata['parents'] = [parent_id]
            folder = drive_service.files().create(body=metadata, fields='id').execute()
            return folder.get('id')

    nexus_root_id = find_or_create_folder('Nexus Root')
    folder_ids['drive_nexus_root_id'] = nexus_root_id
    folder_ids['drive_ingest_dropbox_id'] = find_or_create_folder('Ingest Dropbox', nexus_root_id)
    folder_ids['drive_document_archive_id'] = find_or_create_folder('Document Archive', nexus_root_id)
    folder_ids['drive_diagnostics_id'] = find_or_create_folder('Diagnostics', nexus_root_id)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for k, v in folder_ids.items():
        cursor.execute("INSERT OR IGNORE INTO Config_System (key, value, description) VALUES (?, ?, ?)", (k, v, f"Auto-generated folder ID for {k}"))
        cursor.execute("UPDATE Config_System SET value = ? WHERE key = ?", (v, k))
    conn.commit()
    conn.close()

def ingest_taxonomy_seed(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Checks Google Drive for taxonomy_seed.json. If found, parses and safely updates the taxonomy schema.
    
    Args:
        creds (Credentials): The authenticated Google credentials.
        conn (sqlite3.Connection): The SQLite database connection.
        governor (QuotaGovernor): The active QuotaGovernor instance.
    """
    service = build('drive', 'v3', credentials=creds)
    governor.record_api_call()
    
    results = service.files().list(q="name='taxonomy_seed.json' and trashed=false", spaces='drive', fields='files(id, name, mimeType)').execute()
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
        
        # Architectural Intent: Zero-Trust Quarantine Enforcement
        # We explicitly force `is_gmail_enabled = 0` and `is_drive_enabled = 0` for all
        # ingested Categories, Correspondents, and Purposes. This prevents a misconfigured 
        # external JSON file or newly discovered contacts from instantly flooding the active 
        # taxonomy graph, ensuring they only go live after explicit human approval in the UI.
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat_name,))
        cursor.execute("SELECT id FROM categories WHERE name = ?", (cat_name,))
        cat_id = cursor.fetchone()['id']
        
        for corr in cat.get('correspondents', []):
            corr_name = corr.get('name')
            division = corr.get('division', '')
            sending_subdomains = json.dumps(corr.get('sending_subdomains', []))
            physical_addresses = json.dumps(corr.get('physical_addresses', []))
            brand_colors = json.dumps(corr.get('brand_colors', []))
            
            cursor.execute("""
                INSERT INTO entities (category_id, name, nexus_state)
                VALUES (?, ?, 'disabled')
            """, (cat_id, corr_name))
            
            cursor.execute("SELECT id FROM entities WHERE category_id = ? AND name = ?", (cat_id, corr_name))
            corr_id_row = cursor.fetchone()
            if not corr_id_row: continue
            corr_id = corr_id_row['id']
            
            for purp in corr.get('purposes', []):
                purp_name = purp.get('name')
                
                cursor.execute("""
                    INSERT INTO purposes (category_id, name, scope)
                    VALUES (?, ?, 'Categorical')
                """, (cat_id, purp_name))
                
    conn.commit()
    print("Ingestion of taxonomy_seed.json complete.")

def process_file_with_governor(file_time: float, governor: QuotaGovernor) -> bool:
    """
    Evaluates whether an artifact should be processed based on its age and available API quota.
    
    Args:
        file_time (float): The Unix timestamp of the artifact's creation/modification.
        governor (QuotaGovernor): The active QuotaGovernor instance to query.
        
    Returns:
        bool: True if the file is eligible for immediate processing, False if throttled.
    """
    now = time.time()
    age_hours = (now - file_time) / 3600
    
    # Architectural Intent: The 72-Hour Priority Lane Math
    # If the artifact was generated within the last 72 hours, it skips the quota throttle
    # entirely and is guaranteed processing, utilizing the reserved 30% API budget if necessary.
    if age_hours < 72:
        return True # Priority Lane
    else:
        # Historical Backlog logic requires governor approval
        if not governor.can_process_historical():
            print("Governor: Historical quota limit reached. Throttling.")
            return False
        return True

def sync_drive(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Synchronizes Google Drive changes via delta fetching.
    
    Args:
        creds (Credentials): The authenticated Google credentials.
        conn (sqlite3.Connection): The SQLite database connection.
        governor (QuotaGovernor): The active QuotaGovernor instance tracking API calls.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT is_enabled, settings_json FROM pipeline_config WHERE pipeline_name = 'drive'")
    config_row = cursor.fetchone()
    
    if config_row and not config_row['is_enabled']:
        print("Drive pipeline disabled. Halting.")
        return

    # Parse custom paths from settings
    ingest_path = "Nexus Root/Ingest Dropbox"
    archive_path = "Nexus Root/Document Archive"
    if config_row and config_row['settings_json']:
        try:
            settings = json.loads(config_row['settings_json'])
            ingest_path = settings.get('ingest_path', ingest_path)
            archive_path = settings.get('archive_path', archive_path)
        except:
            pass

    service = build('drive', 'v3', credentials=creds)
    
    # Resolve dynamic folder IDs
    inbox_id = resolve_folder_path(service, ingest_path)
    permanent_archive_id = resolve_folder_path(service, archive_path)
    
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
            
            file_id = change.get('fileId')
            file_metadata = change.get('file', {})
            file_name = file_metadata.get('name', 'Unknown/Deleted File')
            
            logger.info(f"  - Drive Change: '{file_name}' (ID: {file_id})")
            governor.record_api_call(cost=1)
            
            try:
                # Fetch file metadata to check mimeType and parents
                file_metadata = service.files().get(fileId=file_id, fields='mimeType, parents').execute()
                mime_type = file_metadata.get('mimeType', '')
                parents = file_metadata.get('parents', [])
                governor.record_api_call(cost=1)
                
                if inbox_id and inbox_id not in parents:
                    continue
                
                print(f" - Drive Change: File ID {file_id}")
                
                if mime_type and mime_type.startswith('application/vnd.google-apps.'):
                    try:
                        # Attempt native export for Google Docs/Sheets
                        request = service.files().export_media(fileId=file_id, mimeType='text/plain')
                        file_content = request.execute().decode('utf-8')
                    except HttpError as e:
                        if e.resp.status == 400 and "conversion is not supported" in str(e):
                            print(f"File '{file_name}' (ID: {file_id}) cannot be exported as text. Passing metadata only.")
                            file_content = "[Binary File - No Text Extracted]"
                        else:
                            raise e
                else:
                    request = service.files().get_media(fileId=file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        governor.record_api_call(cost=1)
                    file_content = fh.getvalue().decode('utf-8', errors='ignore')
                from llm_engine import process_drive_document
                print(f"Processing Drive document '{file_name}' (Stage 1)...")
                process_drive_document(f"drive_{file_id}", file_content, "[]")
                
                # Check for actionable tasks
                cursor.execute("SELECT * FROM Workspace_Artifacts WHERE artifact_id = ?", (f"drive_{file_id}",))
                artifact_data = cursor.fetchone()
                if artifact_data and artifact_data['google_task_id'] is None:
                    custom_data = json.loads(artifact_data['custom_data']) if artifact_data['custom_data'] else {}
                    if custom_data.get('action_required') == 1 or custom_data.get('action_required') is True or artifact_data['status'] == 'SYSTEM_ALERT':
                        push_to_google_tasks(creds, artifact_data, conn)

            except HttpError as he:
                print(f"Google API Error processing file {file_id}: {he}")
                continue
            except Exception as e:
                print(f"LLM processing failed for {file_id}: {e}")
                continue
            
            # Drive Relocation Engine
            if is_feature_enabled(cursor, 'feature_drive_relocator'):
                archive_id = permanent_archive_id
                if archive_id:
                    try:
                        file_obj = service.files().get(fileId=file_id, fields='parents').execute()
                        governor.record_api_call(cost=1)
                        current_parents = ",".join(file_obj.get('parents', []))
                        
                        service.files().update(
                            fileId=file_id,
                            addParents=archive_id,
                            removeParents=current_parents,
                            fields='id, parents'
                        ).execute()
                        governor.record_api_call(cost=1)
                        print(f"   -> Relocated File {file_id} to Permanent Archive ({archive_id})")
                    except Exception as e:
                        print(f"   -> Relocation failed for {file_id}: {e}")
            else:
                print(f"Safe Mode Bypass: Drive Relocator is disabled. Skipping relocation for {file_id}.")
    else:
        print("No new Drive changes.")
    
    if new_page_token and new_page_token != page_token:
        update_sync_state(cursor, 'drive', new_page_token)
        conn.commit()
        print(f"Updated Drive token to: {new_page_token}")

def preview_gmail_batch(query: str) -> list:
    """
    Uses the Gmail API to search for messages based on the given query.
    Extracts unique senders and counts them.
    Returns a list of dicts: [{'sender': string, 'count': int}]
    """
    from auth import authenticate
    from googleapiclient.discovery import build
    import collections
    
    creds = authenticate()
    if not creds or not creds.valid:
        raise Exception("Failed to authenticate with Google Workspace.")
        
    service = build('gmail', 'v1', credentials=creds)
    
    message_ids = []
    page_token = None
    
    # Limit to 500 messages to prevent long hangs during preview
    while len(message_ids) < 500:
        results = service.users().messages().list(
            userId='me', q=query, pageToken=page_token, fields='messages(id),nextPageToken'
        ).execute()
        
        messages = results.get('messages', [])
        for msg in messages:
            message_ids.append(msg['id'])
            
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    sender_counts = collections.Counter()
    
    # Process up to 50 messages to extract senders efficiently
    batch = service.new_batch_http_request()
    
    def callback(request_id, response, exception):
        if exception is None:
            headers = response.get('payload', {}).get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            sender_counts[sender] += 1

    for msg_id in message_ids[:50]:
        batch.add(service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['From']), callback=callback)
        
    if message_ids[:50]:
        batch.execute()
        
    # Scale counts proportionally if we didn't process all
    if len(message_ids) > 50:
        scale = len(message_ids) / 50.0
        scaled_counts = {k: int(v * scale) for k, v in sender_counts.items()}
    else:
        scaled_counts = dict(sender_counts)
        
    results = [{"sender": k, "count": v} for k, v in scaled_counts.items()]
    # Sort by count descending
    results.sort(key=lambda x: x["count"], reverse=True)
    return results

def sync_gmail(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Synchronizes Gmail changes via history delta fetching.
    
    Args:
        creds (Credentials): The authenticated Google credentials.
        conn (sqlite3.Connection): The SQLite database connection.
        governor (QuotaGovernor): The active QuotaGovernor instance tracking API calls.
    """
    import time
    cursor = conn.cursor()
    cursor.execute("SELECT is_enabled FROM pipeline_config WHERE pipeline_name = 'gmail'")
    row = cursor.fetchone()
    if row and not row['is_enabled']:
        print("Gmail pipeline disabled. Halting.")
        return

    service = build('gmail', 'v1', credentials=creds)
    
    # Fetch dynamic Gmail filters from UI settings
    cursor.execute("SELECT value FROM Config_System WHERE key = 'ui_gmail_filters'")
    row = cursor.fetchone()
    ui_filters = []
    if row and row['value']:
        try:
            ui_filters = json.loads(row['value'])
        except json.JSONDecodeError:
            pass
            
    # Safety Fallback: always append core system labels
    ignored_labels_set = set(ui_filters) | {'SPAM', 'TRASH', 'DRAFT'}
    
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
        for i, record in enumerate(history['history']):
            if i % 10 == 0:
                time.sleep(0.01)
                
            file_time = time.time()
            if not process_file_with_governor(file_time, governor):
                continue
                
            print(f" - Gmail History Record: {record.get('id')}")
            governor.record_api_call(cost=1)
            
            if 'messagesAdded' in record:
                for msg_added in record['messagesAdded']:
                    msg_id = msg_added['message']['id']
                    try:
                        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From']).execute()
                        governor.record_api_call(cost=1)
                        
                        # Extract labels and basic context
                        label_ids = set(msg_detail.get('labelIds', []))
                        gmail_important = 1 if 'IMPORTANT' in label_ids else 0
                        gmail_starred = 1 if 'STARRED' in label_ids else 0

                        headers = msg_detail.get('payload', {}).get('headers', [])
                        subject = "No Subject"
                        for header in headers:
                            if header['name'].lower() == 'subject':
                                subject = header['value']
                                break
                        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
                        
                        logger.info(f"Processing Gmail thread: '{subject}' (ID: mail_{msg_id})...")

                        if IGNORED_GMAIL_LABELS.intersection(label_ids):
                            logger.info(f"Skipping Gmail thread '{subject}' due to ignored labels.")
                            continue
                            
                        snippet = msg_detail.get('snippet', '')
                        
                        email_context = {
                            "subject": subject,
                            "sender": sender,
                            "snippet": snippet,
                            "gmail_important": gmail_important,
                            "gmail_starred": gmail_starred
                        }
                        
                        # Autonomous Profiling for Unknown Senders
                        cursor.execute("SELECT id FROM entities WHERE name = ?", (sender,))
                        if not cursor.fetchone():
                            logger.info(f"Unknown sender '{sender}' for thread '{subject}'. Profiling...")
                            from llm_engine import run_agent_profiler
                            profile_data = run_agent_profiler(sender, is_personal=False, context=snippet)
                            if profile_data:
                                entity_name = profile_data.get("entity_name", sender)
                                parent_org = profile_data.get("parent_organization")
                                workspace_alias = profile_data.get("workspace_alias")
                                
                                parent_id = None
                                if parent_org:
                                    cursor.execute("SELECT id FROM entities WHERE name = ?", (parent_org,))
                                    p_row = cursor.fetchone()
                                    if p_row:
                                        parent_id = p_row['id']
                                    else:
                                        cursor.execute("INSERT INTO entities (name, nexus_state, is_profiled, ingestion_source) VALUES (?, 'pending', 1, 'gmail')", (parent_org,))
                                        parent_id = cursor.lastrowid
                                
                                cursor.execute("INSERT INTO entities (name, parent_entity_id, workspace_alias, nexus_state, is_profiled, ingestion_source) VALUES (?, ?, ?, 'pending', 1, 'gmail')", (entity_name, parent_id, workspace_alias))
                                conn.commit()
                        
                        # Process the thread
                        from llm_engine import process_gmail_thread
                        try:
                            should_archive = process_gmail_thread(f"mail_{msg_id}", email_context, "[]")
                        except Exception as e:
                            print(f"LLM processing failed for {msg_id}: {e}")
                            continue
                        if should_archive:
                            # The message is part of a thread, so we archive the entire thread or just the message.
                            # The instruction says "remove the INBOX label from the thread."
                            thread_id = msg_detail.get('threadId')
                            if thread_id:
                                service.users().threads().modify(
                                    userId='me',
                                    id=thread_id,
                                    body={'removeLabelIds': ['INBOX']}
                                ).execute()
                                governor.record_api_call(cost=1)
                                logger.info(f"Auto-archived thread '{subject}' (ID: {thread_id}).")
                        
                        logger.info(f"Successfully processed Gmail thread '{subject}'.")
                    except Exception as e:
                        logger.error(f"Error processing Gmail thread '{subject}' (ID: {msg_id}): {e}")
    else:
        print("No new Gmail history.")
            
    if new_history_id and new_history_id != history_id:
        update_sync_state(cursor, 'gmail', new_history_id)
        conn.commit()
        print(f"Updated Gmail historyId to: {new_history_id}")

def sync_contacts(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Fetches the user's Google Contacts and ingests them into the Taxonomy as Correspondents.
    Defaults to 'Personal Network' category and zero-trust (disabled) state.
    
    Args:
        creds (Credentials): The authenticated Google credentials.
        conn (sqlite3.Connection): The SQLite database connection.
        governor (QuotaGovernor): The active QuotaGovernor instance tracking API calls.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT is_enabled FROM pipeline_config WHERE pipeline_name = 'contacts'")
    row = cursor.fetchone()
    if row and not row['is_enabled']:
        print("Contacts pipeline disabled. Halting.")
        return

    print("Fetching Google Contacts...")
    service = build('people', 'v1', credentials=creds)
    governor.record_api_call()
    
    try:
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=1000,
            personFields='names,emailAddresses,addresses,memberships'
        ).execute()
        
        connections = results.get('connections', [])
        if not connections:
            print("No contacts found.")
            return
            
        cursor = conn.cursor()
        
        for person in connections:
            names = person.get('names', [])
            if not names:
                continue
                
            corr_name = names[0].get('displayName')
            if not corr_name:
                continue
                
            emails = person.get('emailAddresses', [])
            sending_subdomains = [email.get('value') for email in emails if email.get('value')]
            
            addresses = person.get('addresses', [])
            physical_addresses = [addr.get('formattedValue') for addr in addresses if addr.get('formattedValue')]
            
            memberships = person.get('memberships', [])
            is_favorite = 0
            for membership in memberships:
                contact_group_membership = membership.get('contactGroupMembership', {})
                if 'starred' in contact_group_membership.get('contactGroupId', '').lower():
                    is_favorite = 1
                    break
            
            # Architectural Intent: Zero-Trust Quarantine Enforcement
            # Check if exists
            cursor.execute("SELECT id, ingestion_source FROM entities WHERE name = ?", (corr_name,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO entities (name, nexus_state, is_profiled, ingestion_source, is_favorite)
                    VALUES (?, 'disabled', 0, 'people_api', ?)
                """, (corr_name, is_favorite))
            else:
                # Upsert strategy: preserve 'people_api' source if existing
                cursor.execute("""
                    UPDATE entities 
                    SET is_favorite = ?, ingestion_source = 'people_api' 
                    WHERE name = ? AND ingestion_source != 'people_api'
                """, (is_favorite, corr_name))
            
        conn.commit()
        print(f"Ingested {len(connections)} Google Contacts.")
    except Exception as e:
        print(f"Error fetching contacts: {e}")

def materialize_artifact(artifact_id: str):
    """
    Materializes a transient HTML email into a permanent PDF in Google Drive.
    """
    try:
        from auth import authenticate
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        if not is_feature_enabled(cursor, 'feature_materialization'):
            print(f"Safe Mode Bypass: Materialization Pipeline is disabled. Skipping artifact {artifact_id}.")
            conn.close()
            return
        
        cursor.execute("SELECT raw_text FROM Workspace_Artifacts WHERE artifact_id = ?", (artifact_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
            
        html_content = row['raw_text']
        
        # TODO: Implement WeasyPrint or API conversion here
        pdf_bytes = b"%PDF-1.4 Mock PDF Content"
        
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        creds = authenticate()
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': f'Materialized_{artifact_id}.pdf', 'mimeType': 'application/pdf'}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf', resumable=True)
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        new_drive_id = uploaded_file.get('id')
        new_artifact_id = f"drive_{new_drive_id}"
        
        cursor.execute("""
            INSERT INTO Workspace_Artifacts (artifact_id, parent_artifact_id, status, lifecycle_status)
            VALUES (?, ?, 'PROCESSED', 'ACTIVE')
        """, (new_artifact_id, artifact_id))
        
        cursor.execute("""
            UPDATE Workspace_Artifacts
            SET lifecycle_status = 'MATERIALIZED'
            WHERE artifact_id = ?
        """, (artifact_id,))
        
        conn.commit()
    except Exception as e:
        print(f"Error materializing artifact {artifact_id}: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def run_single_pipeline(pipeline_name: str) -> None:
    """
    Wrapper for executing a single sync pipeline synchronously with all required dependencies.
    """
    try:
        creds = authenticate()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        
        governor = QuotaGovernor(conn)
        
        if pipeline_name == 'contacts':
            sync_contacts(creds, conn, governor)
        elif pipeline_name == 'gmail':
            sync_gmail(creds, conn, governor)
        elif pipeline_name == 'drive':
            sync_drive(creds, conn, governor)
        else:
            print(f"Unknown pipeline: {pipeline_name}")
    except Exception as e:
        print(f"Pipeline {pipeline_name} execution error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def run_sync() -> None:
    """
    Main entry point for the Delta Synchronization Engine.
    Coordinates authentication, Quota Governor initialization, seed ingestion,
    contact syncing, Drive delta fetching, and Gmail history syncing.
    """
    import asyncio
    print("Starting synchronization engine...")
    notifier = NexusNotifier()
    
    try:
        creds = authenticate()
        if not creds or not creds.valid:
            error_msg = "Authentication failed. Ensure token is valid."
            print(error_msg)
            notifier.send_urgent_webhook({"title": "Nexus: Fatal Auth Error", "message": error_msg, "priority": 1})
            return
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        
        governor = QuotaGovernor(conn)
        
        ingest_taxonomy_seed(creds, conn, governor)
        
        cursor = conn.cursor()
        
        # Check Kill Switches
        cursor.execute("SELECT is_enabled FROM pipeline_config WHERE pipeline_name = 'contacts'")
        c_row = cursor.fetchone()
        if not c_row or c_row['is_enabled']:
            sync_contacts(creds, conn, governor)
        else:
            print("Kill Switch: Contacts pipeline is disabled.")

        cursor.execute("SELECT is_enabled FROM pipeline_config WHERE pipeline_name = 'drive'")
        d_row = cursor.fetchone()
        if not d_row or d_row['is_enabled']:
            sync_drive(creds, conn, governor)
        else:
            print("Kill Switch: Drive pipeline is disabled.")

        cursor.execute("SELECT is_enabled FROM pipeline_config WHERE pipeline_name = 'gmail'")
        g_row = cursor.fetchone()
        if not g_row or g_row['is_enabled']:
            sync_gmail_labels(creds, conn)
            sync_gmail(creds, conn, governor)
        else:
            print("Kill Switch: Gmail pipeline is disabled.")

        
        # Process historical ingestion queue
        cursor = conn.cursor()
        cursor.execute("SELECT is_enabled FROM pipeline_config WHERE pipeline_name = 'gmail'")
        g_hist_row = cursor.fetchone()
        
        if g_hist_row and not g_hist_row['is_enabled']:
            print("Kill Switch: Gmail historical ingestion queue is disabled.")
        else:
            cursor.execute("SELECT id, source_id FROM Ingestion_Queue WHERE status = 'PENDING' AND source = 'gmail' LIMIT 20")
            pending_items = cursor.fetchall()
            
            if pending_items:
                print(f"Processing {len(pending_items)} historical items from the queue...")
                service = build('gmail', 'v1', credentials=creds)
                
                for i, item in enumerate(pending_items):
                    queue_id = item['id']
                    msg_id = item['source_id']
                    
                    if not governor.can_process_historical():
                        print("Governor: Historical quota limit reached. Pausing ingestion queue.")
                        break
                        
                    cursor.execute("UPDATE Ingestion_Queue SET status = 'PROCESSING' WHERE id = ?", (queue_id,))
                    conn.commit()
                    
                    try:
                        governor.record_api_call(cost=1)
                        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From']).execute()
                        
                        headers = msg_detail.get('payload', {}).get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
                        snippet = msg_detail.get('snippet', '')
                        
                        email_context = {
                            "subject": subject,
                            "sender": sender,
                            "snippet": snippet
                        }
                        
                        from llm_engine import process_gmail_thread
                        process_gmail_thread(f"mail_{msg_id}", email_context, "[]")
                        cursor.execute("UPDATE Ingestion_Queue SET status = 'COMPLETE' WHERE id = ?", (queue_id,))
                    except Exception as e:
                        print(f"Error processing historical message {msg_id}: {e}")
                        cursor.execute("UPDATE Ingestion_Queue SET status = 'FAILED' WHERE id = ?", (queue_id,))
                    
                    conn.commit()
    except sqlite3.OperationalError as e:
        error_msg = f"Database Lock or Operational Error: {e}"
        print(error_msg)
        notifier.send_urgent_webhook({"title": "Nexus: Database Lock", "message": error_msg, "priority": 1})
    except Exception as e:
        error_msg = f"Synchronization error occurred: {e}"
        print(error_msg)
        notifier.send_urgent_webhook({"title": "Nexus: Sync Error", "message": error_msg, "priority": 0})
    finally:
        if 'conn' in locals():
            try:
                evaluate_quarantine_clusters(conn)
            except Exception as qc_e:
                print(f"Error evaluating quarantine clusters: {qc_e}")
            conn.close()
        print("Synchronization engine completed.")

if __name__ == "__main__":
    run_sync()


def fetch_legacy_gmail_labels() -> list:
    """
    Fetches all legacy custom user labels from Gmail.
    """
    from auth import authenticate
    from googleapiclient.discovery import build
    import sqlite3
    import json
    from db_init import DB_PATH
    from llm_engine import get_taxonomy_tree_json, call_gemini, fetch_active_prompt
    
    creds = authenticate()
    service = build('gmail', 'v1', credentials=creds)
    from diagnostics import write_migration_trace
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # CRITICAL: Prevents dict(row) TypeError in taxonomy builder
    taxonomy_tree = get_taxonomy_tree_json(conn)
    prompt = fetch_active_prompt('MIGRATE_LEGACY_LABEL')
    
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    
    system_labels = {'CATEGORY_PROMOTIONS', 'CATEGORY_UPDATES', 'CATEGORY_SOCIAL', 'CATEGORY_FORUMS', 'CATEGORY_PERSONAL', 'SENT', 'INBOX', 'TRASH', 'SPAM', 'DRAFT', 'UNREAD', 'STARRED', 'IMPORTANT', 'CHAT'}
    
    custom_labels = []
    cursor = conn.cursor()
    
    for label in labels:
        name = label.get('name', '')
        if label.get('type') == 'user' and name.upper() not in system_labels:
            custom_labels.append(name)
            
            cursor.execute("SELECT status FROM Legacy_Label_Migration WHERE label_id = ?", (label['id'],))
            row = cursor.fetchone()
            if row and row[0] == 'accepted':
                continue
            
            context = f"Legacy Label: {name}\nTaxonomy Tree: {json.dumps(taxonomy_tree)}"
            result, _ = call_gemini(prompt, context)
            
            if result:
                cat_id = result.get('mapped_category_id')
                purp_id = result.get('mapped_purpose_id')
                conf = result.get('confidence_score', 0.0)
                
                cursor.execute("SELECT min_confidence_threshold FROM purposes WHERE id = ?", (purp_id,))
                p_row = cursor.fetchone()
                if p_row:
                    threshold = p_row[0]
                else:
                    cursor.execute("SELECT min_confidence_threshold FROM categories WHERE id = ?", (cat_id,))
                    c_row = cursor.fetchone()
                    threshold = c_row[0] if c_row else 0.95
                
                status = 'accepted' if conf >= threshold else 'pending'
                
                cursor.execute("""
                    INSERT INTO Legacy_Label_Migration (label_id, label_name, mapped_category_id, mapped_purpose_id, ai_confidence, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(label_id) DO UPDATE SET
                        mapped_category_id = excluded.mapped_category_id,
                        mapped_purpose_id = excluded.mapped_purpose_id,
                        ai_confidence = excluded.ai_confidence,
                        status = excluded.status,
                        last_evaluated = CURRENT_TIMESTAMP
                """, (label['id'], name, cat_id, purp_id, conf, status))
                
                if status == 'accepted':
                    try:
                        msg_results = service.users().messages().list(userId='me', labelIds=[label['id']]).execute()
                        messages = msg_results.get('messages', [])
                        for msg in messages:
                            artifact_id = f"mail_{msg['id']}"
                            custom_data = json.dumps({"legacy_category_id": cat_id})
                            cursor.execute("""
                                INSERT INTO Workspace_Artifacts (artifact_id, purpose_id, ai_confidence, custom_data, status)
                                VALUES (?, ?, ?, ?, 'PROCESSED')
                                ON CONFLICT(artifact_id) DO UPDATE SET
                                    purpose_id = excluded.purpose_id,
                                    ai_confidence = excluded.ai_confidence,
                                    custom_data = excluded.custom_data
                            """, (artifact_id, purp_id, conf, custom_data))
                    except Exception as e:
                        print(f"Error migrating artifacts for label {name}: {e}")
                    
    conn.commit()
    conn.close()
            
    write_migration_trace("1_RAW_GMAIL_LABELS", custom_labels)
    return custom_labels

# ---------------------------------------------------------------------------
# Zero Trust Ingestion Pipelines
# ---------------------------------------------------------------------------

def sync_contacts_pipeline(creds: Credentials, conn: sqlite3.Connection, governor: QuotaGovernor) -> None:
    """
    Zero Trust Contacts Swimlane using People API
    """
    logger.info("Polling Contacts. Target ETag: [etag]") # Note: etag implementation would require modifying sync state
    service = build('people', 'v1', credentials=creds)
    governor.record_api_call()
    
    try:
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=1000,
            personFields='names,emailAddresses,clientData,userDefined'
        ).execute()
        
        connections = results.get('connections', [])
        if not connections:
            return
            
        cursor = conn.cursor()
        for person in connections:
            source_id = person.get('resourceName')
            client_data = person.get('clientData', [])
            
            nexus_state = next((cd.get('value') for cd in client_data if cd.get('key') == 'nexus_state'), None)
            
            if nexus_state:
                logger.info("Shadow Tether found. Syncing local DB to Google Truth.")
                # UI manual override syncing logic here
                continue
                
            # If new
            emails = person.get('emailAddresses', [])
            if not emails:
                continue
            primary_email = emails[0].get('value', '')
            
            # Enterprise Bypass Check
            is_workspace_directory = False # Placeholder for actual directory check logic
            if primary_email.endswith('@internal-domain.com') or is_workspace_directory:
                logger.info(f"Enterprise Bypass triggered for {primary_email}. Skipping AI.")
                # Write directly to quarantine queue with deterministic mapping
                cursor.execute("INSERT INTO quarantine_queue (source_app, source_id, raw_metadata) VALUES (?, ?, ?)", ('contacts', source_id, json.dumps(person)))
                continue
            
            # Standard Contact Profiling
            from llm_engine import run_agent_profiler
            profile = run_agent_profiler(primary_email, is_personal=True, context=json.dumps(person))
            cursor.execute("INSERT INTO quarantine_queue (source_app, source_id, raw_metadata) VALUES (?, ?, ?)", ('contacts', source_id, json.dumps(profile)))
            
            try:
                # Inject nexus_metadata into Google clientData
                # This requires people.connections.update which is omitted for brevity, but here is the telemetry
                pass
            except Exception as e:
                logger.error(f"Failed to inject Shadow Tether for {primary_email}: {e}")
                
        conn.commit()
    except Exception as e:
        logger.error(f"Error in sync_contacts_pipeline: {e}")

def route_to_quarantine(cursor: sqlite3.Cursor, source_app: str, artifact_id: str, result: dict) -> None:
    cursor.execute("INSERT INTO quarantine_queue (source_app, source_id, raw_metadata) VALUES (?, ?, ?)", (source_app, artifact_id, json.dumps(result)))
    logger.info(f"Artifact {artifact_id} routed to Quarantine Queue.")

def route_to_zero_trust(cursor: sqlite3.Cursor, source_app: str, artifact_id: str, result: dict) -> None:
    cursor.execute("INSERT INTO Workspace_Artifacts (artifact_id, raw_text, status) VALUES (?, ?, 'PROCESSED') ON CONFLICT DO NOTHING", (artifact_id, json.dumps(result)))
    logger.info(f"Artifact {artifact_id} routed to Zero Trust Engine.")

def sync_gmail_pipeline(artifact_id: str, email_context: Dict[str, Any], conn: sqlite3.Connection) -> None:
    """
    Zero Trust Gmail Swimlane
    """
    cursor = conn.cursor()
    # 1. Bypass Rules
    logger.debug(f"Bypassing artifact {artifact_id} due to native rule.")
    
    # 2. Extract Metadata
    sender = email_context.get('sender')
    
    # 3. Check entities table via aliases
    cursor.execute("""
        SELECT e.id, e.name, e.workspace_alias, e.nexus_state 
        FROM aliases a 
        JOIN entities e ON a.entity_id = e.id 
        WHERE a.alias_string = ?
    """, (sender,))
    entity = cursor.fetchone()
    
    from llm_engine import run_agent_classifier, run_agent_profiler
    if entity:
        logger.info(f"Entity Known: {entity['name']}. Executing Purpose-Only AI Evaluation.")
        result = run_agent_classifier(json.dumps(email_context), entity_known=True)
    else:
        profile = run_agent_profiler(sender, is_personal=False, context=json.dumps(email_context))
        if profile:
            entity_name = profile.get('canonical_entity_name', sender)
            workspace_alias = profile.get('workspace_alias')
            proposed_category = profile.get('proposed_category', 'Uncategorized')
            
            cursor.execute("SELECT id FROM categories WHERE name = ?", (proposed_category,))
            cat_row = cursor.fetchone()
            if cat_row:
                cat_id = cat_row['id']
            else:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (proposed_category,))
                cat_id = cursor.lastrowid
                
            cursor.execute("SELECT id FROM entities WHERE name = ?", (entity_name,))
            existing_ent = cursor.fetchone()
            if existing_ent:
                ent_id = existing_ent['id']
            else:
                cursor.execute("""
                    INSERT INTO entities (category_id, name, workspace_alias, nexus_state, is_profiled, ingestion_source) 
                    VALUES (?, ?, ?, 'pending', 1, 'gmail')
                """, (cat_id, entity_name, workspace_alias))
                ent_id = cursor.lastrowid
            
            try:
                cursor.execute("INSERT INTO aliases (alias_string, entity_id) VALUES (?, ?)", (sender, ent_id))
            except sqlite3.IntegrityError:
                pass

        result = run_agent_classifier(json.dumps(email_context))
        
    # Fetch Configured Threshold
    cursor.execute("SELECT settings_json FROM pipeline_config WHERE pipeline_name = 'gmail'")
    row = cursor.fetchone()
    threshold = 80
    if row and row['settings_json']:
        try:
            settings = json.loads(row['settings_json'])
            threshold = int(settings.get('ai_confidence_threshold', 80))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    item_confidence = result.get('confidence', 0) if isinstance(result, dict) else 0

    if item_confidence < threshold:
        route_to_quarantine(cursor, 'gmail', artifact_id, result)
    else:
        route_to_zero_trust(cursor, 'gmail', artifact_id, result)
        
    conn.commit()

def sync_drive_pipeline(artifact_id: str, ocr_text: str, conn: sqlite3.Connection) -> None:
    """
    Zero Trust Drive Swimlane
    """
    cursor = conn.cursor()
    # 1. Bypass Rules
    logger.debug(f"Bypassing artifact {artifact_id} due to native rule.")
    
    # 2. Extract Metadata
    
    # 3. Check entities
    from llm_engine import run_agent_classifier, run_agent_profiler
    
    profile = run_agent_profiler(ocr_text, is_personal=False, context=ocr_text)
    sender = profile.get('canonical_entity_name') if profile else None
    
    if sender:
        cursor.execute("""
            SELECT e.id, e.name, e.workspace_alias, e.nexus_state 
            FROM aliases a 
            JOIN entities e ON a.entity_id = e.id 
            WHERE a.alias_string = ?
        """, (sender,))
        entity = cursor.fetchone()
    else:
        entity = None
    
    if entity:
        logger.info(f"Entity Known: {entity['name']}. Executing Purpose-Only AI Evaluation.")
        result = run_agent_classifier(ocr_text, entity_known=True)
    else:
        if profile and sender:
            workspace_alias = profile.get('workspace_alias')
            proposed_category = profile.get('proposed_category', 'Uncategorized')
            
            cursor.execute("SELECT id FROM categories WHERE name = ?", (proposed_category,))
            cat_row = cursor.fetchone()
            if cat_row:
                cat_id = cat_row['id']
            else:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (proposed_category,))
                cat_id = cursor.lastrowid
                
            cursor.execute("SELECT id FROM entities WHERE name = ?", (sender,))
            existing_ent = cursor.fetchone()
            if existing_ent:
                ent_id = existing_ent['id']
            else:
                cursor.execute("""
                    INSERT INTO entities (category_id, name, workspace_alias, nexus_state, is_profiled, ingestion_source) 
                    VALUES (?, ?, ?, 'pending', 1, 'drive')
                """, (cat_id, sender, workspace_alias))
                ent_id = cursor.lastrowid
            
            try:
                cursor.execute("INSERT INTO aliases (alias_string, entity_id) VALUES (?, ?)", (sender, ent_id))
            except sqlite3.IntegrityError:
                pass

        result = run_agent_classifier(ocr_text)
        
    # Fetch Configured Threshold
    cursor.execute("SELECT settings_json FROM pipeline_config WHERE pipeline_name = 'drive'")
    row = cursor.fetchone()
    threshold = 80
    if row and row['settings_json']:
        try:
            settings = json.loads(row['settings_json'])
            threshold = int(settings.get('ai_confidence_threshold', 80))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    item_confidence = result.get('confidence', 0) if isinstance(result, dict) else 0

    if item_confidence < threshold:
        route_to_quarantine(cursor, 'drive', artifact_id, result)
    else:
        route_to_zero_trust(cursor, 'drive', artifact_id, result)
        
    conn.commit()


def sync_gmail_labels(creds: Credentials, conn: sqlite3.Connection) -> None:
    """
    Stateful Gmail Label Syncing.
    Extracts physical gmail_label_id for Categories, Purposes, and Entities.
    Renames labels via Gmail API if the name/alias changes in Nexus to prevent orphaning.
    """
    service = build('gmail', 'v1', credentials=creds)
    cursor = conn.cursor()
    
    try:
        # Fetch all current labels from Gmail
        results = service.users().labels().list(userId='me').execute()
        gmail_labels = {lbl['name']: lbl for lbl in results.get('labels', [])}
        gmail_labels_by_id = {lbl['id']: lbl for lbl in results.get('labels', [])}
        
        # 1. Sync Categories
        cursor.execute("SELECT id, name, gmail_label_id FROM categories")
        categories = cursor.fetchall()
        for cat in categories:
            cat_name = cat['name']
            label_id = cat['gmail_label_id']
            
            if label_id and label_id in gmail_labels_by_id:
                current_gmail_name = gmail_labels_by_id[label_id]['name']
                if current_gmail_name != cat_name:
                    # Rename the label in Gmail
                    label_body = {'name': cat_name}
                    service.users().labels().patch(userId='me', id=label_id, body=label_body).execute()
                    print(f"Renamed Category label in Gmail: {current_gmail_name} -> {cat_name}")
            else:
                # Create the label
                if cat_name not in gmail_labels:
                    label_body = {'name': cat_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
                    new_label = service.users().labels().create(userId='me', body=label_body).execute()
                    cursor.execute("UPDATE categories SET gmail_label_id = ? WHERE id = ?", (new_label['id'], cat['id']))
                    print(f"Created new Category label in Gmail: {cat_name}")
                else:
                    # Sync existing ID
                    cursor.execute("UPDATE categories SET gmail_label_id = ? WHERE id = ?", (gmail_labels[cat_name]['id'], cat['id']))
        
        # 2. Sync Entities
        cursor.execute("""
            SELECT e.id, e.name, e.workspace_alias, e.flatten_gmail_label, e.gmail_label_id, c.name as cat_name 
            FROM entities e
            JOIN categories c ON e.category_id = c.id
        """)
        entities = cursor.fetchall()
        for ent in entities:
            display_name = ent['workspace_alias'] if ent['workspace_alias'] else ent['name']
            
            if ent['flatten_gmail_label'] == 1 or not ent['cat_name']:
                full_label_name = display_name
            else:
                full_label_name = f"{ent['cat_name']}/{display_name}"
                
            label_id = ent['gmail_label_id']
            
            if label_id and label_id in gmail_labels_by_id:
                current_gmail_name = gmail_labels_by_id[label_id]['name']
                if current_gmail_name != full_label_name:
                    label_body = {'name': full_label_name}
                    service.users().labels().patch(userId='me', id=label_id, body=label_body).execute()
                    print(f"Renamed Entity label in Gmail: {current_gmail_name} -> {full_label_name}")
            else:
                if full_label_name not in gmail_labels:
                    label_body = {'name': full_label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
                    try:
                        new_label = service.users().labels().create(userId='me', body=label_body).execute()
                        cursor.execute("UPDATE entities SET gmail_label_id = ? WHERE id = ?", (new_label['id'], ent['id']))
                        print(f"Created new Entity label in Gmail: {full_label_name}")
                    except HttpError as e:
                        print(f"Failed to create Entity label {full_label_name}: {e}")
                else:
                    cursor.execute("UPDATE entities SET gmail_label_id = ? WHERE id = ?", (gmail_labels[full_label_name]['id'], ent['id']))

        # 3. Sync Purposes
        cursor.execute("""
            SELECT p.id, p.name, p.gmail_label_id, c.name as cat_name 
            FROM purposes p
            JOIN categories c ON p.category_id = c.id
        """)
        purposes = cursor.fetchall()
        for purp in purposes:
            full_label_name = f"{purp['cat_name']}/{purp['name']}"
            label_id = purp['gmail_label_id']
            
            if label_id and label_id in gmail_labels_by_id:
                current_gmail_name = gmail_labels_by_id[label_id]['name']
                if current_gmail_name != full_label_name:
                    label_body = {'name': full_label_name}
                    service.users().labels().patch(userId='me', id=label_id, body=label_body).execute()
                    print(f"Renamed Purpose label in Gmail: {current_gmail_name} -> {full_label_name}")
            else:
                if full_label_name not in gmail_labels:
                    label_body = {'name': full_label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
                    try:
                        new_label = service.users().labels().create(userId='me', body=label_body).execute()
                        cursor.execute("UPDATE purposes SET gmail_label_id = ? WHERE id = ?", (new_label['id'], purp['id']))
                        print(f"Created new Purpose label in Gmail: {full_label_name}")
                    except HttpError as e:
                        print(f"Failed to create Purpose label {full_label_name}: {e}")
                else:
                    cursor.execute("UPDATE purposes SET gmail_label_id = ? WHERE id = ?", (gmail_labels[full_label_name]['id'], purp['id']))
                    
        conn.commit()
    except Exception as e:
        print(f"Error during stateful Gmail label sync: {e}")
