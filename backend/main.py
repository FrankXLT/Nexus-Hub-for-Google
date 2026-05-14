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
from llm_engine import generate_tuning_rule, run_sandbox_prompt, ask_rag, append_zero_shot_rule
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

@app.get("/api/dashboard/mission-control")
async def mission_control():
    """
    Returns High-Level KPI totals: Total Artifacts, Action Required, and Quarantine.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM Workspace_Artifacts")
        total_artifacts = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as action_req FROM Workspace_Artifacts WHERE json_extract(custom_data, '$.requires_action') = 1 OR json_extract(custom_data, '$.requires_action') = 'true'")
        action_required = cursor.fetchone()['action_req']
        
        cursor.execute("""
            SELECT COUNT(*) as quarantine
            FROM quarantine_queue
            WHERE status = 'pending'
        """)
        quarantine = cursor.fetchone()['quarantine']
        
        conn.close()
        
        return JSONResponse(content={
            "status": "success",
            "total_artifacts": total_artifacts,
            "action_required": action_required,
            "quarantine": quarantine
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/analytics/heatmap")
async def analytics_heatmap(tier: str = 'category', timeframe_months: int = 12, item_limit: int = 10):
    """
    Returns temporal activity grouped by tier.
    tier can be 'category', 'correspondent', or 'purpose'.
    """
    try:
        import datetime
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=timeframe_months * 30)).strftime('%Y-%m-01')
        
        if tier == 'category':
            name_col = "tcat.name"
        elif tier == 'correspondent':
            name_col = "e.name"
        else:
            name_col = "p.name"
            
        join_clause = """
            FROM Workspace_Artifacts w
            JOIN purposes p ON w.purpose_id = p.id
            JOIN categories tcat ON p.category_id = tcat.id
            LEFT JOIN entities e ON json_extract(w.custom_data, '$.entity_id') = e.id
        """
        
        top_query = f"""
            SELECT {name_col} as item_name, COUNT(*) as vol
            {join_clause}
            WHERE json_extract(w.custom_data, '$.document_date') >= ?
            GROUP BY {name_col}
            ORDER BY vol DESC
            LIMIT ?
        """
        cursor.execute(top_query, (cutoff_date, item_limit))
        top_items = [row['item_name'] for row in cursor.fetchall()]
        
        if not top_items:
            conn.close()
            return JSONResponse(content={"status": "success", "data": []})
            
        placeholders = ','.join(['?'] * len(top_items))
        
        data_query = f"""
            SELECT 
                strftime('%Y-%m', json_extract(w.custom_data, '$.document_date')) as month,
                {name_col} as item_name,
                COUNT(*) as volume
            {join_clause}
            WHERE json_extract(w.custom_data, '$.document_date') >= ?
              AND {name_col} IN ({placeholders})
            GROUP BY month, {name_col}
            ORDER BY month ASC
        """
        params = [cutoff_date] + top_items
        cursor.execute(data_query, params)
        rows = cursor.fetchall()
        
        matrix = {}
        for row in rows:
            month = row['month']
            item = row['item_name']
            if item not in matrix:
                matrix[item] = {}
            matrix[item][month] = row['volume']
            
        cursor.execute(f"""
            SELECT DISTINCT strftime('%Y-%m', json_extract(w.custom_data, '$.document_date')) as month
            FROM Workspace_Artifacts w
            WHERE json_extract(w.custom_data, '$.document_date') >= ?
            ORDER BY month ASC
        """, (cutoff_date,))
        all_months = [row['month'] for row in cursor.fetchall() if row['month']]
        
        results = []
        for item in top_items:
            series = [{"month": m, "volume": matrix.get(item, {}).get(m, 0)} for m in all_months]
            results.append({
                "item_name": item,
                "series": series
            })
            
        conn.close()
        return JSONResponse(content={"status": "success", "data": results})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/analytics/threads")
async def analytics_threads(q: str = "", node_limit: int = 15):
    """
    Threads analytics endpoint.
    By default, appends a SQL clause to exclude lifecycle_status = 'MATERIALIZED'
    """
    try:
        import calendar
        import datetime
        import re
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        conditions = ["w.status != 'MATERIALIZED' AND w.lifecycle_status != 'MATERIALIZED'"]
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
            LEFT JOIN categories tcat ON p.category_id = tcat.id
            LEFT JOIN entities e ON json_extract(w.custom_data, '$.entity_id') = e.id
        """
        
        query = f"""
            SELECT 
                CASE 
                    WHEN w.artifact_id LIKE 'mail_%' THEN 'gmail'
                    WHEN w.artifact_id LIKE 'drive_%' THEN 'drive'
                    ELSE 'other'
                END as source,
                tcat.name as entity,
                e.name as correspondent,
                '#9AA0A6' as brand_color,
                p.name as purpose,
                COUNT(*) as volume
            {join_clause}
            {where_clause}
            GROUP BY source, entity, correspondent, brand_color, purpose
            ORDER BY volume DESC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        top_nodes = rows[:node_limit]
        other_nodes = rows[node_limit:]
        
        results = [dict(row) for row in top_nodes]
        
        if other_nodes:
            other_volume = sum(row['volume'] for row in other_nodes)
            results.append({
                "source": "mixed",
                "entity": "Other",
                "correspondent": "Other",
                "brand_color": "#9AA0A6",
                "purpose": "Other",
                "volume": other_volume
            })
            
        conn.close()
        
        return JSONResponse(content={"status": "success", "data": results})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

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


@app.put("/api/entities/correspondents/{id}")
async def update_correspondent(id: int, request: Request):
    try:
        body = await request.json()
        rules = body.get("custom_extraction_rules", "")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute("UPDATE entities SET custom_extraction_rules = ? WHERE id = ?", (rules, id))
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
        cursor.execute("UPDATE purposes SET custom_extraction_rules = ?, auto_archive = ? WHERE id = ?", (rules, auto_archive_int, id))
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

@app.get("/api/analytics/heatmap")
def get_analytics_heatmap():
    from datetime import datetime, timedelta
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    now = int(time.time())
    twenty_days_ago = now - (20 * 86400)
    
    # 1. Top 30 correspondents over last 20 days
    cursor.execute("""
        SELECT e.id, e.name, COUNT(DISTINCT wa.artifact_id) as vol
        FROM Workspace_Artifacts wa
        JOIN Artifact_History ah ON wa.artifact_id = ah.artifact_id
        LEFT JOIN entities e ON json_extract(wa.custom_data, '$.entity_id') = e.id
        WHERE ah.timestamp >= ? AND e.id IS NOT NULL
        GROUP BY e.id, e.name
        ORDER BY vol DESC
        LIMIT 30
    """, (twenty_days_ago,))
    top_corrs = cursor.fetchall()
    
    heatmap_data = []
    
    # Generate dates list
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=19) # 20 days inclusive
    date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(20)]
    
    for corr in top_corrs:
        corr_id = corr['id']
        corr_name = corr['name']
        
        cursor.execute("""
            SELECT date(ah.timestamp, 'unixepoch') as dt, COUNT(DISTINCT wa.artifact_id) as count
            FROM Workspace_Artifacts wa
            JOIN Artifact_History ah ON wa.artifact_id = ah.artifact_id
            WHERE json_extract(wa.custom_data, '$.entity_id') = ? AND ah.timestamp >= ?
            GROUP BY dt
        """, (corr_id, twenty_days_ago))
        
        counts_by_date = {row['dt']: row['count'] for row in cursor.fetchall()}
        
        data_array = []
        for d in date_list:
            data_array.append({"date": d, "count": counts_by_date.get(d, 0)})
            
        heatmap_data.append({
            "sender": corr_name,
            "data": data_array
        })
        
    conn.close()
    return {"heatmap": heatmap_data}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
