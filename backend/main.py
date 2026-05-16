"""
FastAPI Backend Application for Nexus.
Handles incoming webhooks from Google Apps Script with cryptographic replay protection.
"""

import os
import hmac
import hashlib
import time
import json
import sqlite3
import asyncio
from typing import Callable, Awaitable, Optional
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

from db_init import DB_PATH
from llm_engine import run_sandbox_prompt, ask_rag, append_zero_shot_rule
from sync_engine import run_sync

# Load environment variables from .env file
load_dotenv()

NEXUS_HMAC_SECRET = os.getenv("NEXUS_HMAC_SECRET", "")

app = FastAPI(title="Nexus Webhook Receiver", description="Receives secure webhook events from Google Apps Script.")

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
    try:
        from auth import authenticate
        from googleapiclient.discovery import build
        from sync_engine import initialize_drive_structure
        
        creds = authenticate()
        if creds and creds.valid:
            drive_service = build('drive', 'v3', credentials=creds)
            await asyncio.to_thread(initialize_drive_structure, drive_service)
            print("Drive scaffolding initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Drive structure on startup: {e}")

    async def periodic_sync():
        while True:
            try:
                # Execute blocking sync function in a separate thread
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
                    SELECT q.source_id as artifact_id, json_extract(q.raw_metadata, '$.summary') as summary, p.name as purpose_name, e.name as correspondent_name
                    FROM quarantine_queue q
                    LEFT JOIN purposes p ON q.proposed_purpose_id = p.id
                    LEFT JOIN entities e ON q.proposed_entity_id = e.id
                    WHERE q.status = 'pending'
                """)
                quarantined = cursor.fetchall()
                conn.close()
                
                html_body = "<h2>Nexus Daily Digest</h2>"
                
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

async def process_historical_data(search_query: str):
    from googleapiclient.discovery import build
    from auth import authenticate
    import asyncio
    import sqlite3
    from db_init import DB_PATH
    try:
        creds = authenticate()
        service = build('gmail', 'v1', credentials=creds)
        
        message_ids = []
        page_token = None
        
        iteration = 0
        while True:
            results = await asyncio.to_thread(
                service.users().messages().list(userId='me', q=search_query, pageToken=page_token, fields='messages(id),nextPageToken').execute
            )
            messages = results.get('messages', [])
            for msg in messages:
                message_ids.append(msg['id'])
                iteration += 1
                if iteration % 50 == 0:
                    await asyncio.sleep(0.01)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        for i, msg_id in enumerate(message_ids):
            cursor.execute("INSERT INTO Ingestion_Queue (source, source_id, status) VALUES ('gmail', ?, 'PENDING')", (msg_id,))
            if i % 50 == 0:
                conn.commit()
                await asyncio.sleep(0.01)
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error processing historical data: {e}")

@app.post("/api/ingestion/queue-historical")
async def queue_historical(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        search_query = payload.get("search_query")
        if not search_query:
            return JSONResponse(status_code=400, content={"error": "Missing search_query"})
        
        background_tasks.add_task(process_historical_data, search_query)
        
        return JSONResponse(content={"status": "success", "message": "Historical sync queued in background."})
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

@app.post("/api/taxonomy/zero-shot-rule")
async def zero_shot_rule(request: Request):
    """
    Appends a user instruction as a new extraction rule to the purpose shared by provided artifacts.
    """
    try:
        body = await request.json()
        artifact_ids = body.get("artifact_ids", [])
        instruction = body.get("instruction", "")
        
        result = await append_zero_shot_rule(artifact_ids, instruction)
        if result.get("status") == "success":
            return JSONResponse(content=result)
        else:
            return JSONResponse(status_code=400, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/artifacts/search")
async def search_artifacts(q: str = "", limit: int = 50, offset: int = 0):
    """
    AST Parser search endpoint.
    By default, appends a SQL clause to exclude lifecycle_status = 'MATERIALIZED'
    """
    try:
        import calendar
        import datetime
        import re
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        conditions = ["w.status != 'MATERIALIZED'"]
        params = []
        
        if not q.strip():
            thirty_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            conditions.append("json_extract(w.custom_data, '$.document_date') >= ?")
            params.append(thirty_days_ago)
        else:
            parts = re.findall(r'(!?[a-zA-Z]+):(?:"([^"]+)"|([^\s]+))', q)
            clean_q = re.sub(r'!?[a-zA-Z]+:(?:"[^"]+"|[^\s]+)', '', q).strip()
            
            if clean_q:
                conditions.append("(w.summary LIKE ? OR w.raw_text LIKE ?)")
                params.append(f"%{clean_q}%")
                params.append(f"%{clean_q}%")
                
            for match in parts:
                key = match[0]
                val = match[1] or match[2]
                
                is_exclude = key.startswith('!')
                actual_key = key.lstrip('!')
                operator = "!=" if is_exclude else "="
                
                if actual_key.lower() == 'correspondent':
                    conditions.append(f"e.name {operator} ?")
                    params.append(val)
                elif actual_key.lower() == 'purpose':
                    conditions.append(f"p.name {operator} ?")
                    params.append(val)
                elif actual_key.lower() == 'date':
                    if len(val) == 7 and '-' in val:
                        y, m = map(int, val.split('-'))
                        last_day = calendar.monthrange(y, m)[1]
                        start_date = f"{y:04d}-{m:02d}-01"
                        end_date = f"{y:04d}-{m:02d}-{last_day:02d}"
                        if is_exclude:
                            conditions.append("json_extract(w.custom_data, '$.document_date') NOT BETWEEN ? AND ?")
                        else:
                            conditions.append("json_extract(w.custom_data, '$.document_date') BETWEEN ? AND ?")
                        params.extend([start_date, end_date])
                    elif len(val) == 10:
                        conditions.append(f"json_extract(w.custom_data, '$.document_date') {operator} ?")
                        params.append(val)
        
        where_clause = " WHERE " + " AND ".join(conditions)
        
        join_clause = """
            FROM Workspace_Artifacts w
            LEFT JOIN purposes p ON w.purpose_id = p.id
            LEFT JOIN entities e ON json_extract(w.custom_data, '$.entity_id') = e.id
        """
        
        count_query = f"SELECT COUNT(*) as total {join_clause} {where_clause}"
        cursor.execute(count_query, params)
        total_matches = cursor.fetchone()['total']
        
        data_query = f"""
            SELECT w.artifact_id, w.summary, w.custom_data, w.status,
                   p.name as purpose_name, e.name as correspondent_name
            {join_clause}
            {where_clause}
            ORDER BY json_extract(w.custom_data, '$.document_date') DESC
            LIMIT ? OFFSET ?
        """
        data_params = params + [limit, offset]
        
        cursor.execute(data_query, data_params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            import json
            r = dict(row)
            try:
                r['custom_data'] = json.loads(r['custom_data']) if r['custom_data'] else {}
            except json.JSONDecodeError:
                r['custom_data'] = {}
            results.append(r)
            
        conn.close()
        
        return JSONResponse(content={
            "status": "success",
            "total_matches": total_matches,
            "limit": limit,
            "offset": offset,
            "results": results
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

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

@app.get("/api/settings/pipeline")
async def get_pipeline_settings():
    """
    Retrieves the UI pipeline settings from Config_System.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        keys = (
            'ui_gmail_filters', 'ui_ai_config', 'ui_post_processing',
            'feature_retention_sweeper', 'feature_drive_relocator', 
            'feature_materialization', 'feature_google_tasks'
        )
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
        
        valid_keys = {
            'ui_gmail_filters', 'ui_ai_config', 'ui_post_processing', 'default_view',
            'feature_retention_sweeper', 'feature_drive_relocator', 
            'feature_materialization', 'feature_google_tasks'
        }
        for key, value in settings.items():
            if key in valid_keys:
                if key in ('default_view', 'feature_retention_sweeper', 'feature_drive_relocator', 'feature_materialization', 'feature_google_tasks'):
                    cursor.execute(
                        "UPDATE Config_System SET value = ? WHERE key = ?",
                        (str(value), key)
                    )
                else:
                    cursor.execute(
                        "UPDATE Config_System SET value = ? WHERE key = ?",
                        (json.dumps(value), key)
                    )
                
        conn.commit()
        conn.close()
        
        return JSONResponse(content={"status": "success", "message": "Pipeline settings updated."})
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

@app.get("/api/analytics/taxonomy")
def get_analytics_taxonomy():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    now = int(time.time())
    twenty_days_ago = now - (20 * 86400)
    
    # 1. Top 30 correspondents over last 20 days
    cursor.execute("""
        SELECT e.id
        FROM Workspace_Artifacts wa
        JOIN Artifact_History ah ON wa.artifact_id = ah.artifact_id
        LEFT JOIN entities e ON json_extract(wa.custom_data, '$.entity_id') = e.id
        WHERE ah.timestamp >= ? AND e.id IS NOT NULL
        GROUP BY e.id
        ORDER BY COUNT(DISTINCT wa.artifact_id) DESC
        LIMIT 30
    """, (twenty_days_ago,))
    top_corrs = [row['id'] for row in cursor.fetchall()]
    
    if not top_corrs:
        conn.close()
        return {"links": []}

    placeholders = ",".join(["?"] * len(top_corrs))
    query = f"""
        SELECT 
            CASE 
                WHEN wa.artifact_id LIKE 'mail_%' THEN 'Gmail'
                WHEN wa.artifact_id LIKE 'drive_%' THEN 'Drive'
                ELSE 'Other'
            END as source_app,
            tcat.name as category_name,
            e.name as corr_name,
            p.name as purpose_name,
            COUNT(DISTINCT wa.artifact_id) as vol
        FROM Workspace_Artifacts wa
        JOIN purposes p ON wa.purpose_id = p.id
        JOIN categories tcat ON p.category_id = tcat.id
        LEFT JOIN entities e ON json_extract(wa.custom_data, '$.entity_id') = e.id
        JOIN Artifact_History ah ON wa.artifact_id = ah.artifact_id
        WHERE ah.timestamp >= ? AND e.id IN ({placeholders})
        GROUP BY source_app, category_name, corr_name, purpose_name
    """
    params = [twenty_days_ago] + top_corrs
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    links_dict = {}
    
    def add_link(src, tgt, val):
        if not src or not tgt:
            return
        key = f"{src}|||{tgt}"
        if key not in links_dict:
            links_dict[key] = 0
        links_dict[key] += val

    for row in rows:
        app = row['source_app']
        cat = row['category_name']
        corr = row['corr_name']
        purp = row['purpose_name']
        vol = row['vol']
        
        add_link(app, cat, vol)
        add_link(cat, corr, vol)
        add_link(corr, purp, vol)

    links = [{"source": k.split('|||')[0], "target": k.split('|||')[1], "value": v} for k, v in links_dict.items()]
    
    conn.close()
    return {"links": links}

class DiscoverEntity(BaseModel):
    sender_name: str
    category_id: int
    is_sub_sender_of: Optional[int] = None

class BlacklistEntry(BaseModel):
    type: str # Must be 'domain' or 'purpose'
    pattern: str

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/taxonomy/flow")
def get_taxonomy_flow():
    conn = get_db()
    cursor = conn.cursor()
    
    flow_data = {"categories": [], "universal_purposes": []}
    
    cursor.execute("SELECT id, name FROM purposes WHERE scope = 'Universal'")
    flow_data["universal_purposes"] = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT id, name, description FROM categories")
    categories = cursor.fetchall()
    
    for cat in categories:
        cat_dict = dict(cat)
        
        cursor.execute("SELECT id, name FROM purposes WHERE category_id = ?", (cat["id"],))
        cat_dict["categorical_purposes"] = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT id, name, parent_entity_id FROM entities WHERE category_id = ?", (cat["id"],))
        entities = cursor.fetchall()
        
        cat_dict["entities"] = [dict(e) for e in entities if e["parent_entity_id"] is None]
        cat_dict["sub_entities"] = [dict(e) for e in entities if e["parent_entity_id"] is not None]
        
        flow_data["categories"].append(cat_dict)
        
    conn.close()
    return flow_data

@app.post("/api/taxonomy/discover")
def discover_entity(payload: DiscoverEntity):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO entities (name, category_id, parent_entity_id) VALUES (?, ?, ?)",
            (payload.sender_name, payload.category_id, payload.is_sub_sender_of)
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
    return {"message": "Entity discovered and injected", "id": new_id}

@app.get("/api/taxonomy/blacklist")
def get_blacklist():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, pattern FROM blacklist")
    results = cursor.fetchall()
    conn.close()
    
    blacklist_data = {"domains": [], "purposes": []}
    for row in results:
        if row["type"] == "domain":
            blacklist_data["domains"].append(dict(row))
        elif row["type"] == "purpose":
            blacklist_data["purposes"].append(dict(row))
            
    return blacklist_data

@app.post("/api/taxonomy/blacklist")
def add_blacklist(payload: BlacklistEntry):
    if payload.type not in ['domain', 'purpose']:
        raise HTTPException(status_code=400, detail="Type must be 'domain' or 'purpose'")
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO blacklist (type, pattern) VALUES (?, ?)", (payload.type, payload.pattern))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Pattern already exists for this type")
    finally:
        conn.close()
    return {"message": f"Added {payload.pattern} to {payload.type} blacklist"}

@app.get("/api/orchestrator/telemetry")
async def get_orchestrator_telemetry():
    """
    Returns telemetry data for the Frontend Orchestrator.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as quarantine_count FROM quarantine_queue WHERE status = 'pending'")
        row = cursor.fetchone()
        quarantine_count = row['quarantine_count'] if row else 0
        
        cursor.execute("SELECT COUNT(*) as processed_today FROM Artifact_History WHERE date(timestamp, 'unixepoch') = date('now')")
        row = cursor.fetchone()
        processed_today = row['processed_today'] if row else 0
        
        conn.close()
        
        return JSONResponse(content={
            "quarantine_count": quarantine_count,
            "processed_today": processed_today,
            "system_status": "Engine Online"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/quarantine/queue")
async def get_quarantine_queue():
    """
    Returns the quarantine queue formatted for the frontend carousel.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT q.id, q.source_app as source, e.name as entity, q.raw_metadata
            FROM quarantine_queue q
            LEFT JOIN entities e ON q.proposed_entity_id = e.id
            WHERE q.status = 'pending'
        """)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            badges = []
            if row['raw_metadata']:
                try:
                    metadata = json.loads(row['raw_metadata'])
                    if metadata.get('consolidated'):
                        badges.append('consolidated')
                    if metadata.get('web_search_used'):
                        badges.append('web_search_used')
                except json.JSONDecodeError:
                    pass
            
            results.append({
                "id": row['id'],
                "source": row['source'],
                "entity": row['entity'] or "Unknown",
                "badges": badges
            })
            
        conn.close()
        return JSONResponse(content=results)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/batch/preview")
async def batch_preview(request: Request):
    try:
        body = await request.json()
        source = body.get("source")
        query = body.get("query")
        
        if source == "gmail" and query:
            from sync_engine import preview_gmail_batch
            import asyncio
            data = await asyncio.to_thread(preview_gmail_batch, query)
            return JSONResponse(content=data)
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid source or query"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class BatchPayload(BaseModel):
    sender_string: str
    artifacts: list

@app.post("/api/batch/process")
async def batch_process(payload: BatchPayload):
    conn = get_db()
    cursor = conn.cursor()
    # Check aliases
    cursor.execute("SELECT e.id, e.name, e.parent_entity_id FROM aliases a JOIN entities e ON a.entity_id = e.id WHERE a.alias_string = ?", (payload.sender_string,))
    row = cursor.fetchone()
    
    entity_name = None
    if not row:
        from llm_engine import run_bulk_profiler
        bulk_context = json.dumps([a.get('snippet') for a in payload.artifacts])
        profile = run_bulk_profiler(payload.sender_string, bulk_context)
        
        if profile:
            entity_name = profile.get('entity_name', payload.sender_string)
            parent_org = profile.get('parent_organization')
            workspace_alias = profile.get('workspace_alias')
            
            parent_id = None
            if parent_org:
                cursor.execute("SELECT id FROM entities WHERE name = ?", (parent_org,))
                p_row = cursor.fetchone()
                if p_row:
                    parent_id = p_row['id']
                else:
                    cursor.execute("INSERT INTO entities (name, nexus_state) VALUES (?, 'active')", (parent_org,))
                    parent_id = cursor.lastrowid
            
            cursor.execute("INSERT INTO entities (name, parent_entity_id, workspace_alias, nexus_state) VALUES (?, ?, ?, 'active')", (entity_name, parent_id, workspace_alias))
            entity_id = cursor.lastrowid
            
            try:
                cursor.execute("INSERT INTO aliases (alias_string, entity_id) VALUES (?, ?)", (payload.sender_string, entity_id))
            except sqlite3.IntegrityError:
                pass # Alias already exists
            
            conn.commit()
        else:
            entity_name = payload.sender_string
    else:
        entity_name = row['name']
        
    from llm_engine import run_bulk_classifier
    classifier_results = run_bulk_classifier(entity_name, payload.artifacts)
    
    if classifier_results:
        for res in classifier_results:
            art_id = res.get('id')
            purp = res.get('purpose')
            if art_id and purp:
                # Ensure purpose exists
                cursor.execute("SELECT id FROM purposes WHERE name = ?", (purp,))
                p_row = cursor.fetchone()
                if p_row:
                    p_id = p_row['id']
                else:
                    cursor.execute("INSERT INTO purposes (name, scope) VALUES (?, 'Categorical')", (purp,))
                    p_id = cursor.lastrowid
                    
                # Update Workspace_Artifacts
                cursor.execute("""
                    UPDATE Workspace_Artifacts 
                    SET summary = ?, status = 'PROCESSED', taxonomy_id = ?
                    WHERE artifact_id = ?
                """, (f"Mapped to {purp}", p_id, art_id))
        conn.commit()
        conn.close()
        return {"status": "success", "mapped": len(classifier_results)}
    
    conn.close()
    return {"status": "error", "message": "Bulk classifier failed."}


class PipelineConfigPayload(BaseModel):
    pipeline: str
    settings_json: dict

@app.post("/api/orchestrator/config")
async def save_orchestrator_config(payload: PipelineConfigPayload):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pipeline_config (pipeline_name, settings_json) VALUES (?, ?) ON CONFLICT(pipeline_name) DO UPDATE SET settings_json = excluded.settings_json",
            (payload.pipeline, json.dumps(payload.settings_json))
        )
        conn.commit()
        conn.close()
        return JSONResponse(content={"status": "success", "message": "Config saved"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class SimulatePayload(BaseModel):
    artifact_id: str
    pipeline: str

@app.post("/api/orchestrator/simulate")
async def simulate_orchestrator(payload: SimulatePayload):
    import io
    import logging
    
    conn = get_db()
    conn.execute("BEGIN TRANSACTION")
    
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    
    logger = logging.getLogger('sync_engine')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    try:
        import sync_engine
        if payload.pipeline == "gmail":
            sync_engine.sync_gmail_pipeline(payload.artifact_id, {"sender": "Simulated", "subject": "Sim", "snippet": "Sim"}, conn)
        elif payload.pipeline == "drive":
            sync_engine.sync_drive_pipeline(payload.artifact_id, "Simulated OCR Text", conn)
        
        # Rollback to prevent actual changes
        conn.rollback()
    except Exception as e:
        conn.rollback()
        log_stream.write(f"\\nError: {e}")
    finally:
        logger.removeHandler(handler)
        conn.close()
    
    trace_output = log_stream.getvalue()
    
    # Save trace to Drive
    try:
        from auth import authenticate
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        creds = authenticate()
        drive_service = build('drive', 'v3', credentials=creds)
        
        conn2 = get_db()
        c2 = conn2.cursor()
        c2.execute("SELECT value FROM Config_System WHERE key = 'drive_diagnostics_id'")
        row = c2.fetchone()
        conn2.close()
        
        diag_folder_id = row['value'] if row else None
        
        file_metadata = {'name': f'{payload.pipeline}_{payload.artifact_id}.txt', 'mimeType': 'text/plain'}
        if diag_folder_id:
            file_metadata['parents'] = [diag_folder_id]
            
        media = MediaIoBaseUpload(io.BytesIO(trace_output.encode('utf-8')), mimetype='text/plain', resumable=True)
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    except Exception as e:
        print(f"Failed to upload simulate log to drive: {e}")
        pass
        
    return {"status": "success", "trace": trace_output}

@app.get("/api/analytics/heatmap")
async def get_analytics_heatmap(days: int = 30, source: str = "all", status: str = "all"):
    try:
        conn = get_db()
        cursor = conn.cursor()

        where_clauses = ["json_extract(custom_data, '$.document_date') IS NOT NULL"]
        params = []

        if source != 'all':
            where_clauses.append("(CASE WHEN artifact_id LIKE 'mail_%' THEN 'Gmail' WHEN artifact_id LIKE 'drive_%' THEN 'Drive' ELSE 'Other' END) = ?")
            params.append(source)
        if status != 'all':
            where_clauses.append("status = ?")
            params.append(status)

        # Date filter
        where_clauses.append(f"json_extract(custom_data, '$.document_date') >= date('now', '-{days} days')")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        cursor.execute(f"""
            SELECT 
                date(json_extract(custom_data, '$.document_date')) as ingested_at,
                CASE 
                    WHEN artifact_id LIKE 'mail_%' THEN 'Gmail'
                    WHEN artifact_id LIKE 'drive_%' THEN 'Drive'
                    ELSE 'Other'
                END as source_app,
                COUNT(artifact_id) as count
            FROM Workspace_Artifacts
            {where_sql}
            GROUP BY ingested_at, source_app
            ORDER BY ingested_at ASC
        """, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return JSONResponse(content=[])

        data = [{"date": row["ingested_at"], "count": row["count"], "source": row["source_app"]} for row in rows if row["ingested_at"]]

        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/analytics/sankey")
async def get_analytics_sankey(days: int = 30, source: str = "all", status: str = "all"):
    try:
        conn = get_db()
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if source != 'all':
            where_clauses.append("(CASE WHEN wa.artifact_id LIKE 'mail_%' THEN 'Gmail' WHEN wa.artifact_id LIKE 'drive_%' THEN 'Drive' ELSE 'Other' END) = ?")
            params.append(source)
        if status != 'all':
            where_clauses.append("wa.status = ?")
            params.append(status)

        where_clauses.append(f"json_extract(wa.custom_data, '$.document_date') >= date('now', '-{days} days')")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN wa.artifact_id LIKE 'mail_%' THEN 'Gmail'
                    WHEN wa.artifact_id LIKE 'drive_%' THEN 'Drive'
                    ELSE 'Other'
                END as source_app,
                c.name as category, 
                p.name as purpose, 
                COUNT(wa.artifact_id) as val
            FROM Workspace_Artifacts wa
            JOIN purposes p ON wa.purpose_id = p.id
            JOIN categories c ON p.category_id = c.id
            {where_sql}
            GROUP BY source_app, c.name, p.name
        """, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return JSONResponse(content={"nodes": [], "links": []})

        nodes_set = set()
        links = []

        for row in rows:
            src = row['source_app']
            cat = row['category']
            purp = row['purpose']
            val = row['val']

            if val <= 0: continue

            nodes_set.add(src)
            nodes_set.add(cat)
            nodes_set.add(purp)

            links.append({"source": src, "target": cat, "value": val})
            links.append({"source": cat, "target": purp, "value": val})

        consolidated_links = {}
        for link in links:
            key = (link["source"], link["target"])
            if key not in consolidated_links:
                consolidated_links[key] = 0
            consolidated_links[key] += link["value"]

        final_links = [{"source": k[0], "target": k[1], "value": v} for k, v in consolidated_links.items()]
        final_nodes = [{"id": n} for n in nodes_set]

        return JSONResponse(content={"nodes": final_nodes, "links": final_links})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
class LegacyLabelExecutionPayload(BaseModel):
    approved_labels: list

@app.post("/api/ingestion/legacy-labels/preview")
async def preview_legacy_labels():
    try:
        from sync_engine import fetch_legacy_gmail_labels
        from llm_engine import deduplicate_legacy_labels, profile_and_map_entities
        
        raw_labels = await asyncio.to_thread(fetch_legacy_gmail_labels)
        deduped_labels = await asyncio.to_thread(deduplicate_legacy_labels, raw_labels)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        current_categories = [row['name'] for row in cursor.fetchall()]
        conn.close()
        
        final_profiles = await asyncio.to_thread(profile_and_map_entities, deduped_labels, current_categories)
        
        return JSONResponse(content={"status": "success", "data": final_profiles})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/ingestion/legacy-labels/execute")
async def execute_legacy_labels(payload: LegacyLabelExecutionPayload):
    conn = get_db()
    try:
        cursor = conn.cursor()
        conn.execute("BEGIN TRANSACTION;")
        
        for item in payload.approved_labels:
            if isinstance(item, dict):
                original_label = item.get("original_label")
                canonical_entity_name = item.get("canonical_entity_name")
                workspace_alias = item.get("workspace_alias")
                proposed_category = item.get("proposed_category")
            else:
                continue
                
            if not all([original_label, canonical_entity_name, proposed_category]):
                continue
                
            # Insert or get category
            cursor.execute("SELECT id FROM categories WHERE name = ?", (proposed_category,))
            cat_row = cursor.fetchone()
            if cat_row:
                cat_id = cat_row['id']
            else:
                cursor.execute("INSERT INTO categories (name) VALUES (?)", (proposed_category,))
                cat_id = cursor.lastrowid
                
            # Insert entity
            cursor.execute("SELECT id FROM entities WHERE name = ?", (canonical_entity_name,))
            ent_row = cursor.fetchone()
            if ent_row:
                ent_id = ent_row['id']
            else:
                cursor.execute(
                    "INSERT INTO entities (category_id, name, workspace_alias, nexus_state) VALUES (?, ?, ?, 'active')", 
                    (cat_id, canonical_entity_name, workspace_alias)
                )
                ent_id = cursor.lastrowid
                
            # Insert alias
            cursor.execute("SELECT id FROM aliases WHERE alias_string = ?", (original_label,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO aliases (alias_string, entity_id) VALUES (?, ?)", (original_label, ent_id))
                
        conn.execute("COMMIT;")
        return JSONResponse(content={"status": "success", "message": "Legacy labels migrated successfully."})
    except Exception as e:
        conn.execute("ROLLBACK;")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        conn.close()

@app.get("/api/prompts")
async def get_prompts():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT target_app, prompt_text FROM Config_Prompts")
        rows = cursor.fetchall()
        conn.close()
        
        data = {row["target_app"]: row["prompt_text"] for row in rows}
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/orchestrator/run-now/{pipeline_name}")
async def run_pipeline_now(pipeline_name: str, background_tasks: BackgroundTasks):
    from sync_engine import run_single_pipeline
    
    valid_pipelines = ['gmail', 'drive', 'contacts']
    if pipeline_name not in valid_pipelines:
        return JSONResponse(status_code=400, content={"error": f"Unknown pipeline: {pipeline_name}"})
        
    background_tasks.add_task(run_single_pipeline, pipeline_name)
    return JSONResponse(content={"status": "success", "message": f"{pipeline_name} pipeline initiated in background."})

@app.get("/api/taxonomy/tree")
async def get_taxonomy_tree():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM categories")
        categories = cursor.fetchall()
        
        tree = []
        for cat in categories:
            cat_dict = dict(cat)
            cursor.execute("SELECT id, name FROM purposes WHERE category_id = ?", (cat["id"],))
            purposes = cursor.fetchall()
            
            purps_list = []
            for purp in purposes:
                p_dict = dict(purp)
                p_dict["entities"] = []
                purps_list.append(p_dict)
                
            cat_dict["purposes"] = purps_list
            tree.append(cat_dict)
            
        conn.close()
        return JSONResponse(content=tree)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
