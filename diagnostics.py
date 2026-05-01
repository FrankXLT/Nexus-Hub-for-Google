"""
Module: diagnostics.py
Purpose: Diagnostic suite for Nexus Hub. Performs read/write verification on the SQLite database, 
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

DB_PATH = 'nexus.db'

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
        folder_name = "Nexus Diagnostics"
        
        # 1. Search for existing diagnostics folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        # If the diagnostics folder is not found, create a new one.
        if not items:
            # Create folder if it doesn't exist
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
        # Otherwise, use the existing folder's ID.
        else:
            folder_id = items[0].get('id')
            
        # 2. Upload the JSON log
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
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
            "title": "Nexus Hub: Diagnostic Watchdog Failure",
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
