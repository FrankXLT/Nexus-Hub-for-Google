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
from typing import Callable, Awaitable
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from db_init import DB_PATH
from llm_engine import generate_tuning_rule, run_sandbox_prompt

# Load environment variables from .env file
load_dotenv()

NEXUS_HMAC_SECRET = os.getenv("NEXUS_HMAC_SECRET", "")

app = FastAPI(title="Nexus Hub Webhook Receiver", description="Receives secure webhook events from Google Apps Script.")

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
