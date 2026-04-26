"""
FastAPI Backend Application for Nexus Hub.
Handles incoming webhooks from Google Apps Script with cryptographic replay protection.
"""

import os
import hmac
import hashlib
import time
import json
from typing import Callable, Awaitable
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

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
async def update_data(request: Request):
    """
    Endpoint for handling data updates from Google Apps Script.
    """
    return {"status": "success", "message": "Webhook received securely."}

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
