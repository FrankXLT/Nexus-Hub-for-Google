"""
Module: diagnostics.py
Purpose: Diagnostic suite for Nexus. Performs read/write verification on the SQLite database, 
checks OAuth token validity, and uploads diagnostic reports securely to Google Drive.
"""

import sqlite3
import os
import json
import io
import time
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from auth import authenticate
import urllib.request
from notifier import NexusNotifier
import zlib
import sqlite3

DB_PATH = os.getenv("NEXUS_DB_PATH", "nexus-live.db")

def write_migration_trace(step_name: str, payload) -> None:
    """
    Purpose: Appends a timestamped JSON payload to a physical log file for the Legacy Label Migration Engine.
    """
    trace_path = os.path.join(os.path.dirname(__file__), "gmail_migration_trace.log")
    with open(trace_path, "a", encoding="utf-8") as f:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "payload": payload
        }
        f.write(json.dumps(log_entry) + "\n")

def log_activity_event(activity_id: str, artifact_id: Optional[str], pipeline_source: str, step_name: str, status: str, execution_time_ms: int = 0, tokens_used: int = 0, event_payload: Optional[Dict[str, Any]] = None) -> None:
    """
    Fire-and-forget logging mechanism for the Activity_Ledger.
    Compresses payload with zlib before BLOB insertion.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    compressed_payload = None
    if event_payload:
        compressed_payload = zlib.compress(json.dumps(event_payload).encode('utf-8'))
        
    cursor.execute("""
        INSERT INTO Activity_Ledger (activity_id, artifact_id, pipeline_source, event_timestamp, step_name, status, execution_time_ms, tokens_used, event_payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (activity_id, artifact_id, pipeline_source, time.time(), step_name, status, execution_time_ms, tokens_used, compressed_payload))
    
    conn.commit()
    conn.close()

def check_database() -> dict:
    """
    Purpose: Verifies SQLite database read/write access.
    Expected Inputs: None. Uses DB_PATH.
    Expected Outputs: dict - A dictionary containing the status, message, and details of the operation.
    """
    try:
        # If the database file does not exist on disk, return an error.
        if not os.path.exists(DB_PATH):
            return {"status": "error", "message": "Database file not found"}
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Apply strict pragma to catch issues early
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        # Test write
        cursor.execute("CREATE TABLE IF NOT EXISTS _Diagnostic_Test (id INTEGER PRIMARY KEY, ts INTEGER)")
        cursor.execute("INSERT INTO _Diagnostic_Test (ts) VALUES (?)", (int(time.time()),))
        
        # Test read
        cursor.execute("SELECT COUNT(*) AS count FROM _Diagnostic_Test")
        count = cursor.fetchone()['count']
        
        # Cleanup
        cursor.execute("DROP TABLE _Diagnostic_Test")
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Database read/write verified", "details": {"rows_read": count}}
        
    except sqlite3.OperationalError as e:
        # If a locking error occurs (WAL mode), report it specifically.
        if "locked" in str(e).lower():
            return {"status": "error", "message": "Database is locked (WAL lock error)"}
        return {"status": "error", "message": f"SQLite Operational Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Database Error: {str(e)}"}


def check_oauth_token() -> dict:
    """
    Purpose: Verifies the Google Workspace OAuth token by performing a lightweight API call.
    Expected Inputs: None. Uses configured credentials.
    Expected Outputs: dict - A status dictionary with success/failure info and basic user details.
    """
    try:
        creds = authenticate()
        # If credentials are missing or invalid, report an error.
        if not creds or not creds.valid:
            return {"status": "error", "message": "Credentials invalid or missing"}
            
        # Lightweight check: Fetch Drive user quota
        drive_service = build('drive', 'v3', credentials=creds)
        about = drive_service.about().get(fields="user").execute()
        
        return {
            "status": "success", 
            "message": "OAuth token valid and Drive API accessible",
            "details": {"user": about.get('user', {}).get('emailAddress', 'Unknown')}
        }
    except Exception as e:
        return {"status": "error", "message": f"OAuth Token Check Failed: {str(e)}"}


def check_api_health() -> dict:
    """
    Purpose: Verifies the FastAPI web server is responsive.
    Expected Inputs: None. Assumes server runs on localhost:8000.
    Expected Outputs: dict - A status indicating success or HTTP error code.
    """
    try:
        req = urllib.request.Request("http://nexus-api:8000/api/health")
        with urllib.request.urlopen(req, timeout=10) as response:
            # If the HTTP status is 200 (OK), parse the health data.
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                return {"status": "success", "message": "API is healthy", "details": data}
            # Otherwise, report the error code.
            else:
                return {"status": "error", "message": f"API returned HTTP {response.getcode()}"}
    except Exception as e:
        return {"status": "error", "message": f"API Health Check Failed: {str(e)}"}

def upload_diagnostic_log(report_data: dict) -> dict:
    """
    Purpose: Compiles the diagnostic report and uploads it to a specific Google Drive folder.
    Expected Inputs: report_data (dict) - The compiled test results to upload.
    Expected Outputs: dict - A status containing the uploaded file ID, or error message.
    """
    try:
        creds = authenticate()
        # Ensure credentials are valid before trying to use the Drive API.
        if not creds or not creds.valid:
             return {"status": "error", "message": "Cannot upload log: credentials invalid"}
             
        drive_service = build('drive', 'v3', credentials=creds)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM Config_System WHERE key = 'drive_diagnostics_id'")
        diag_row = cursor.fetchone()
        conn.close()

        folder_id = diag_row['value'].strip('"') if diag_row and diag_row['value'] and diag_row['value'] != '""' else None

        if not folder_id:
             return {"status": "error", "message": "Cannot upload log: drive_diagnostics_id not found in configuration."}

        # 2. Upload the JSON log        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_metadata = {
            'name': f'nexus_diagnostic_{timestamp_str}.json',
            'parents': [folder_id]
        }
        
        json_content = json.dumps(report_data, indent=2)
        media = MediaIoBaseUpload(io.BytesIO(json_content.encode('utf-8')), mimetype='application/json')
        
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        return {"status": "success", "message": "Log uploaded successfully", "file_id": file.get('id')}
        
    except Exception as e:
         return {"status": "error", "message": f"Log Upload Failed: {str(e)}"}


def run_all_diagnostics() -> dict:
    """
    Purpose: Executes the full suite of diagnostic tests and securely uploads the result.
    Expected Inputs: None.
    Expected Outputs: dict - The master diagnostic report containing nested component reports.
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "database": check_database(),
        "oauth": check_oauth_token(),
        "api": check_api_health()
    }
    
    notifier = NexusNotifier()
    errors = []
    
    # If the database check failed, append the error to the notification list.
    if report['database']['status'] == 'error':
        errors.append(f"Database Error: {report['database']['message']}")
    # If the OAuth check failed, append the error.
    if report['oauth']['status'] == 'error':
        errors.append(f"OAuth Error: {report['oauth']['message']}")
    # If the API check failed, append the error.
    if report['api']['status'] == 'error':
        errors.append(f"API Error: {report['api']['message']}")
        
    # If there are any collected errors, send an urgent webhook notification.
    if errors:
        notifier.send_urgent_webhook({
            "title": "Nexus: Diagnostic Watchdog Failure",
            "message": "\n".join(errors),
            "priority": 1
        })
    
    # If OAuth passed, try to upload the log
    if report['oauth']['status'] == 'success':
        upload_result = upload_diagnostic_log(report)
        report['log_upload'] = upload_result
    # Otherwise, skip the upload because we don't have authorization.
    else:
        report['log_upload'] = {"status": "skipped", "message": "Skipped due to OAuth failure"}
        
    return report

# When run as a script, execute the test suite and output JSON.
if __name__ == "__main__":
    # Local CLI testing
    print("Running Nexus Diagnostics...")
    result = run_all_diagnostics()
    print(json.dumps(result, indent=2))
