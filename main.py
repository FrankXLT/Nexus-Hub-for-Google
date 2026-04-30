"""
FastAPI Backend Application for Nexus Hub.
Handles incoming webhooks from Google Apps Script with cryptographic replay protection.
"""

import os
import hmac
import hashlib
import time
import json
import sqlite3
import asyncio
from typing import Callable, Awaitable
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db_init import DB_PATH
from llm_engine import generate_tuning_rule, run_sandbox_prompt, ask_rag
from sync_engine import run_sync

# Load environment variables from .env file
load_dotenv()

NEXUS_HMAC_SECRET = os.getenv("NEXUS_HMAC_SECRET", "")

app = FastAPI(title="Nexus Hub Webhook Receiver", description="Receives secure webhook events from Google Apps Script.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def start_cron_jobs():
    """
    Initializes background cron tasks upon server startup.
    """
    async def periodic_sync():
        while True:
            try:
                # Run sync in a separate thread to avoid blocking the event loop
                await asyncio.to_thread(run_sync)
            except Exception as e:
                print(f"Background sync error: {e}")
            await asyncio.sleep(3600)  # Run every hour

    async def daily_digest():
        while True:
            try:
                await asyncio.sleep(86400)  # Run every 24 hours
                notifier = NexusNotifier()
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Query DLQ
                cursor.execute("SELECT module_name, error_message FROM Error_Logs ORDER BY timestamp DESC LIMIT 50")
                errors = cursor.fetchall()
                
                # Query Zero-Trust Quarantine
                # Items where purpose or correspondent is disabled. Since Workspace_Artifacts points to purpose_id
                cursor.execute("""
                    SELECT w.artifact_id, w.summary, tp.name as purpose_name, tc.name as correspondent_name
                    FROM Workspace_Artifacts w
                    JOIN Taxonomy_Purposes tp ON w.purpose_id = tp.id
                    JOIN Taxonomy_Correspondents tc ON tp.correspondent_id = tc.id
                    WHERE tp.is_gmail_enabled = 0 AND tp.is_drive_enabled = 0
                """)
                quarantined = cursor.fetchall()
                conn.close()
                
                html_body = "<h2>Nexus Hub Daily Digest</h2>"
                
                html_body += "<h3>Zero-Trust Quarantine Queue</h3>"
                if quarantined:
                    html_body += "<ul>"
                    for q in quarantined:
                        html_body += f"<li><strong>{q['correspondent_name']} / {q['purpose_name']}</strong>: {q['summary']} (Artifact: {q['artifact_id']})</li>"
                    html_body += "</ul>"
                else:
                    html_body += "<p>No items in quarantine.</p>"
                
                html_body += "<h3>Dead-Letter Queue (Recent Errors)</h3>"
                if errors:
                    html_body += "<ul>"
                    for err in errors:
                        html_body += f"<li><strong>{err['module_name']}</strong>: {err['error_message']}</li>"
                    html_body += "</ul>"
                else:
                    html_body += "<p>No recent errors.</p>"
                
                # Run the digest sending in a thread
                await asyncio.to_thread(notifier.send_daily_digest, html_body)
                
            except Exception as e:
                print(f"Daily digest error: {e}")

    asyncio.create_task(periodic_sync())
    asyncio.create_task(daily_digest())

@app.middleware("http")
async def verify_nexus_signature(request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]) -> JSONResponse:
    """
    Middleware to intercept incoming requests and verify the X-Nexus-Signature header.
    
    It validates that the signature is a valid HMAC-SHA256 hash of the request body
    using the shared NEXUS_HMAC_SECRET. It also implements replay protection by 
    extracting a 'timestamp' field from the JSON payload and verifying it is within 
    5 minutes of the server's current time.
    
    Args:
        request (Request): The incoming FastAPI request.
        call_next (Callable): The next middleware or route handler.
        
    Returns:
        JSONResponse: A 401 Unauthorized response if verification fails, 
                      or 500 if server misconfigured,
                      otherwise passes the request to the next handler.
    """
    # Only protect specific API routes that require validation, or all routes.
    # Assuming all POST requests to /api/ require this protection.
    if request.url.path.startswith("/api/") and request.method == "POST":
        signature = request.headers.get("X-Nexus-Signature")
        if not signature:
            return JSONResponse(status_code=401, content={"detail": "Missing X-Nexus-Signature header"})
        
        if not NEXUS_HMAC_SECRET:
            return JSONResponse(status_code=500, content={"detail": "Server misconfiguration: HMAC secret not set"})

        # Read body for hash calculation
        body = await request.body()

        # Validate HMAC signature
        expected_signature = hmac.new(
            NEXUS_HMAC_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return JSONResponse(status_code=401, content={"detail": "Invalid signature"})
        
        # Replay protection: extract timestamp from JSON payload
        try:
            payload = json.loads(body)
            timestamp = payload.get("timestamp")
            if not timestamp:
                return JSONResponse(status_code=401, content={"detail": "Missing timestamp in payload"})
            
            current_time = time.time()
            
            # Check if timestamp is older than 5 minutes (300 seconds)
            # Also gracefully handle requests from slightly in the future (clock drift)
            time_difference = abs(current_time - float(timestamp))
            if time_difference > 300:
                return JSONResponse(status_code=401, content={"detail": "Timestamp expired or invalid (Replay Protection)"})
                
        except json.JSONDecodeError:
            return JSONResponse(status_code=401, content={"detail": "Invalid JSON payload"})
        except (ValueError, TypeError):
            return JSONResponse(status_code=401, content={"detail": "Invalid timestamp format"})
            
    response = await call_next(request)
    return response

@app.post("/api/ingestion/queue-historical")
async def queue_historical(request: Request):
    from googleapiclient.discovery import build
    from auth import authenticate
    try:
        payload = await request.json()
        search_query = payload.get("search_query")
        if not search_query:
            return JSONResponse(status_code=400, content={"error": "Missing search_query"})
        
        creds = authenticate()
        service = build('gmail', 'v1', credentials=creds)
        
        message_ids = []
        page_token = None
        while True:
            results = service.users().messages().list(userId='me', q=search_query, pageToken=page_token, fields='messages(id),nextPageToken').execute()
            messages = results.get('messages', [])
            for msg in messages:
                message_ids.append(msg['id'])
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        for msg_id in message_ids:
            cursor.execute("INSERT INTO Ingestion_Queue (source, source_id, status) VALUES ('gmail', ?, 'PENDING')", (msg_id,))
            
        conn.commit()
        conn.close()
        
        return JSONResponse(content={"status": "success", "queued": len(message_ids)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/workflows/materialize")
async def materialize_items(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        artifact_ids = body.get("artifact_ids", [])
        from sync_engine import materialize_artifact
        for a_id in artifact_ids:
            background_tasks.add_task(materialize_artifact, a_id)
        return JSONResponse(content={"status": "success", "message": f"Queued {len(artifact_ids)} items for materialization."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/artifacts/search")
async def search_artifacts(request: Request):
    """
    AST Parser search endpoint.
    By default, appends a SQL clause to exclude lifecycle_status = 'MATERIALIZED'
    """
    return JSONResponse(content={"status": "not_implemented", "message": "Epic 2 endpoint stubbed."})

@app.get("/api/analytics/threads")
async def analytics_threads(request: Request):
    """
    Threads analytics endpoint.
    By default, appends a SQL clause to exclude lifecycle_status = 'MATERIALIZED'
    """
    return JSONResponse(content={"status": "not_implemented", "message": "Epic 2 endpoint stubbed."})

@app.get("/api/analytics/roi-dashboard")
async def roi_dashboard():
    """
    Returns ROI analytics: first-pass accuracy, exception rate, avg ms/tokens, and 30-day throughput.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Effectiveness: First-Pass Accuracy & Exception Rate
        cursor.execute("SELECT COUNT(*) as total FROM Artifact_History WHERE is_human_corrected = 0")
        uncorrected_items = cursor.fetchone()['total'] or 0
        
        cursor.execute("SELECT COUNT(*) as total FROM Artifact_History")
        total_items = cursor.fetchone()['total'] or 0
        
        first_pass_accuracy = (uncorrected_items / total_items * 100) if total_items > 0 else 0.0
        
        cursor.execute("SELECT COUNT(*) as errors FROM Error_Logs")
        exception_count = cursor.fetchone()['errors'] or 0
        exception_rate = (exception_count / total_items * 100) if total_items > 0 else 0.0

        # 2. Telemetry: Average processing time and tokens over last 1000 records
        cursor.execute("SELECT AVG(processing_time_ms) as avg_ms, AVG(api_tokens_used) as avg_tokens FROM (SELECT processing_time_ms, api_tokens_used FROM Artifact_History ORDER BY timestamp DESC LIMIT 1000)")
        telemetry = cursor.fetchone()
        avg_ms = telemetry['avg_ms'] or 0.0
        avg_tokens = telemetry['avg_tokens'] or 0.0

        # 3. Throughput: Total artifacts processed in 30 days, grouped by source
        import time
        thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN artifact_id LIKE 'mail_%' THEN 1 ELSE 0 END) as gmail_count,
                SUM(CASE WHEN artifact_id LIKE 'drive_%' THEN 1 ELSE 0 END) as drive_count
            FROM Artifact_History
            WHERE timestamp >= ?
        """, (thirty_days_ago,))
        throughput = cursor.fetchone()
        gmail_count = throughput['gmail_count'] or 0
        drive_count = throughput['drive_count'] or 0

        conn.close()

        return JSONResponse(content={
            "first_pass_accuracy_percent": round(first_pass_accuracy, 2),
            "exception_rate_percent": round(exception_rate, 2),
            "average_processing_ms": round(avg_ms, 2),
            "average_api_tokens": round(avg_tokens, 2),
            "throughput_30_days": {
                "gmail": gmail_count,
                "drive": drive_count,
                "total": gmail_count + drive_count
            }
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/update")
async def update_data(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint for handling data updates from Google Apps Script.
    """
    try:
        body = await request.json()
        artifact_id = body.get("artifact_id")
        original_json = body.get("original_json", {})
        corrected_json = body.get("corrected_json", {})
        
        if artifact_id and corrected_json:
            background_tasks.add_task(generate_tuning_rule, artifact_id, original_json, corrected_json)
            
    except Exception as e:
        print(f"Error processing update: {e}")
        
    return {"status": "success", "message": "Webhook received securely."}

@app.post("/api/sandbox")
async def sandbox_endpoint(request: Request):
    """
    Endpoint for testing prompts against raw text without modifying database.
    """
    try:
        body = await request.json()
        artifact_id = body.get("artifact_id")
        prompt_string = body.get("prompt_string")
        
        if not artifact_id or not prompt_string:
            return JSONResponse(status_code=400, content={"detail": "Missing artifact_id or prompt_string"})
            
        result = run_sandbox_prompt(artifact_id, prompt_string)
        return JSONResponse(content={"status": "success", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/ask")
async def ask_endpoint(request: Request):
    """
    Endpoint for asking questions using RAG over the database.
    """
    try:
        body = await request.json()
        question = body.get("question")
        if not question:
            return JSONResponse(status_code=400, content={"detail": "Missing question"})
            
        answer = ask_rag(question)
        return JSONResponse(content={"status": "success", "answer": answer})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/bulk-update")
async def bulk_update_endpoint(request: Request):
    """
    Endpoint for handling bulk updates to metadata for multiple artifacts simultaneously.
    """
    try:
        body = await request.json()
        artifact_ids = body.get("artifact_ids", [])
        metadata = body.get("metadata", {})
        
        if not artifact_ids or not isinstance(artifact_ids, list):
            return JSONResponse(status_code=400, content={"detail": "Invalid or missing artifact_ids"})
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        now = int(time.time())
        for a_id in artifact_ids:
            cursor.execute("SELECT custom_data, status FROM Workspace_Artifacts WHERE artifact_id = ?", (a_id,))
            row = cursor.fetchone()
            if row:
                previous_state = {}
                try:
                    previous_state = json.loads(row['custom_data']) if row['custom_data'] else {}
                except json.JSONDecodeError:
                    pass
                previous_state["status"] = row['status']
                
                # Merge metadata
                new_state = previous_state.copy()
                new_state.update(metadata)
                
                # Assume status or taxonomy might be updated
                new_status = metadata.get("status", row['status'])
                
                new_state_json = json.dumps(new_state)
                previous_state_json = json.dumps(previous_state)
                
                cursor.execute("""
                    UPDATE Workspace_Artifacts 
                    SET custom_data = ?, status = ?
                    WHERE artifact_id = ?
                """, (new_state_json, new_status, a_id))
                
                cursor.execute("""
                    INSERT INTO Artifact_History (artifact_id, timestamp, actor, action_type, previous_state, new_state)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (a_id, now, "USER", "BULK_UPDATE", previous_state_json, new_state_json))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={"status": "success", "message": f"Updated {len(artifact_ids)} artifacts."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/prompts")
async def get_prompts():
    """
    Retrieves the active master prompts from the database.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT target_app, prompt_text FROM Config_Prompts")
        rows = cursor.fetchall()
        conn.close()
        
        prompts = {row["target_app"]: row["prompt_text"] for row in rows}
        return JSONResponse(content={"status": "success", "prompts": prompts})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/prompts")
async def update_prompts(request: Request):
    """
    Updates a master prompt in the database.
    Expected JSON payload: {"target_app": "...", "prompt_text": "...", "timestamp": "..."}
    """
    try:
        body = await request.json()
        target_app = body.get("target_app")
        prompt_text = body.get("prompt_text")
        
        if not target_app or not prompt_text:
            return JSONResponse(status_code=400, content={"detail": "Missing target_app or prompt_text"})
            
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Config_Prompts SET prompt_text = ? WHERE target_app = ?",
            (prompt_text, target_app)
        )
        conn.commit()
        conn.close()
        
        return JSONResponse(content={"status": "success", "message": f"Prompt {target_app} updated successfully."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/settings/pipeline")
async def get_pipeline_settings():
    """
    Retrieves the UI pipeline settings from Config_System.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        keys = ('ui_gmail_filters', 'ui_ai_config', 'ui_post_processing')
        placeholders = ','.join(['?'] * len(keys))
        cursor.execute(f"SELECT key, value FROM Config_System WHERE key IN ({placeholders})", keys)
        rows = cursor.fetchall()
        conn.close()
        
        settings = {}
        for row in rows:
            try:
                settings[row["key"]] = json.loads(row["value"])
            except json.JSONDecodeError:
                settings[row["key"]] = row["value"]
                
        return JSONResponse(content={"status": "success", "settings": settings})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/settings/pipeline")
async def update_pipeline_settings(request: Request):
    """
    Updates the UI pipeline settings in Config_System.
    """
    try:
        body = await request.json()
        settings = body.get("settings", {})
        
        if not settings:
            return JSONResponse(status_code=400, content={"detail": "Missing settings"})
            
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        valid_keys = {'ui_gmail_filters', 'ui_ai_config', 'ui_post_processing'}
        for key, value in settings.items():
            if key in valid_keys:
                cursor.execute(
                    "UPDATE Config_System SET value = ? WHERE key = ?",
                    (json.dumps(value), key)
                )
                
        conn.commit()
        conn.close()
        
        return JSONResponse(content={"status": "success", "message": "Pipeline settings updated."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.put("/api/entities/correspondents/{id}")
async def update_correspondent(id: int, request: Request):
    try:
        body = await request.json()
        rules = body.get("custom_extraction_rules", "")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute("UPDATE Taxonomy_Correspondents SET custom_extraction_rules = ? WHERE id = ?", (rules, id))
        conn.commit()
        conn.close()
        return JSONResponse(content={"status": "success", "message": "Correspondent rules updated."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.put("/api/entities/purposes/{id}")
async def update_purpose(id: int, request: Request):
    try:
        body = await request.json()
        rules = body.get("custom_extraction_rules", "")
        auto_archive = body.get("auto_archive", False)
        auto_archive_int = 1 if auto_archive else 0
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute("UPDATE Taxonomy_Purposes SET custom_extraction_rules = ?, auto_archive = ? WHERE id = ?", (rules, auto_archive_int, id))
        conn.commit()
        conn.close()
        return JSONResponse(content={"status": "success", "message": "Purpose rules and settings updated."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/health/quota")
async def get_health_quota():
    try:
        from sync_engine import DAILY_QUOTA_LIMIT
        import datetime
        import json
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        cursor.execute("SELECT value FROM Config_System WHERE key = 'api_quota'")
        row = cursor.fetchone()
        conn.close()
        
        calls = 0
        if row and row['value']:
            quota_data = json.loads(row['value'])
            if quota_data.get('date') == today:
                calls = quota_data.get('calls', 0)
                
        return JSONResponse(content={"status": "success", "quota": {"used": calls, "limit": DAILY_QUOTA_LIMIT}})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/api/retention/rules")
async def get_retention_rules():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Config_Retention_Rules ORDER BY id DESC")
        rules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return JSONResponse(content={"status": "success", "rules": rules})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/retention/rules")
async def add_retention_rule(request: Request):
    try:
        body = await request.json()
        target_category = body.get('target_category', '')
        action = body.get('action', 'ARCHIVE')
        days_old = int(body.get('days_old', 30))
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Config_Retention_Rules (target_category, action, days_old) VALUES (?, ?, ?)", (target_category, action, days_old))
        conn.commit()
        conn.close()
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.delete("/api/retention/rules/{rule_id}")
async def delete_retention_rule(rule_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Config_Retention_Rules WHERE id = ?", (rule_id,))
        conn.commit()
        conn.close()
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/retention/sweep")
async def trigger_retention_sweep():
    try:
        import subprocess
        subprocess.Popen(["python", "retention_worker.py"])
        return JSONResponse(content={"status": "success", "message": "Sweep started in background."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/health")
async def health_check_post(request: Request):
    """
    Diagnostic health check route (POST to test signature).
    Executes the comprehensive suite of tests and uploads the report.
    """
    from diagnostics import run_all_diagnostics
    report = run_all_diagnostics()
    return {"status": "healthy", "report": report}

@app.get("/api/health")
async def health_check_get():
    """
    Simple health check without payload requirements.
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
