"""
LLM Engine for Nexus Hub.
Handles batch processing and Gemini API interactions for automated metadata extraction.
Implements Two-Stage Triage for Drive documents and Single-Pass extraction for Gmail.
"""

import json
import os
import sqlite3
import time
from typing import Dict, Any, Optional

from google import genai
from google.genai import types
from tenacity import retry, wait_exponential, stop_after_attempt

from db_init import DB_PATH

# ---------------------------------------------------------------------------
# Master AI Prompts (Section 9.3)
# ---------------------------------------------------------------------------

PROMPT_GMAIL = """You are a strict data extraction system for a centralized knowledge hub. Review the provided email thread. 

**Tasks:**
1. **Taxonomy Mapping:** Map the email to ONE exact `Category \\ Correspondent \\ Purpose` from the provided whitelist. If it does not match perfectly, output the purpose as 'Purpose/Review'.
2. **Summary:** Generate a concise, 1-sentence summary of the thread's current state.
3. **Action State:** Determine if this email requires human action (true/false).
4. **Custom Fields:** Based on the mapped Purpose, extract the following fields: [DYNAMIC_ARRAY]. Return null if not found.

**Rules:** Hallucinating new categories is strictly forbidden. 
**Output:** ONLY valid JSON.
{
  "taxonomy_path": "string",
  "summary": "string",
  "requires_action": boolean,
  "custom_fields": { "Field1": "value" }
}"""

PROMPT_DRIVE_STAGE_1 = """You are an intelligent document routing engine. Review the following raw OCR text. It may contain scanning errors.

**Task:** Identify the primary organization, vendor, or sender of this document. Match it to ONE exact `Correspondent` string from the provided whitelist.

**Rules:**
- Ignore generic payment processors (e.g., PayPal, Stripe) if the actual vendor is mentioned.
- If the correspondent is completely unknown or the document is unreadable, output 'UNKNOWN'.
**Output:** ONLY valid JSON: { "correspondent": "string" }"""

PROMPT_DRIVE_STAGE_2 = """You are a precise metadata extraction agent. Review the OCR text for this document belonging to the correspondent: [CORRESPONDENT].

**Tasks:**
1. **Purpose Mapping:** Map the document's intent to ONE exact `Purpose` from the provided whitelist. Output 'Purpose/Review' if ambiguous.
2. **Document Title:** Generate a concise, highly descriptive title for this document (e.g., 'Q3 Auto Insurance Renewal Policy').
3. **Document Date:** Extract the primary creation or effective date of the document in YYYY-MM-DD format.
4. **Custom Fields:** Extract the following specific fields for this purpose: [DYNAMIC_ARRAY]. Return null if not found.

**Output:** ONLY valid JSON.
{
  "purpose": "string",
  "title": "string",
  "document_date": "YYYY-MM-DD",
  "custom_fields": { "Field1": "value" }
}"""

# ---------------------------------------------------------------------------
# API Interaction
# ---------------------------------------------------------------------------

def get_genai_client() -> genai.Client:
    """Initializes the Gemini client, expecting GEMINI_API_KEY in the environment."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client()

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def call_gemini(prompt: str, context: str) -> Optional[Dict[str, Any]]:
    """
    Calls the Gemini API with exponential backoff and forces JSON output.
    Safely handles parsing errors with a try/except block.
    """
    client = get_genai_client()
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, context],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error. Hallucinated format: {e}")
        if response and response.text:
            print(f"Raw Output: {response.text}")
        return None
    except Exception as e:
        print(f"Gemini API Error: {e}")
        raise # Raise to trigger tenacity retry

# ---------------------------------------------------------------------------
# Database Operations
# ---------------------------------------------------------------------------

def update_artifact_status(artifact_id: str, status: str) -> None:
    """Updates only the status of an artifact."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    cursor.execute("UPDATE Workspace_Artifacts SET status = ? WHERE artifact_id = ?", (status, artifact_id))
    conn.commit()
    conn.close()

def persist_llm_results(artifact_id: str, summary: str, custom_data: Dict[str, Any], status: str) -> None:
    """
    Writes the successful extraction to Workspace_Artifacts and logs the change to Artifact_History.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    
    # 1. Retrieve previous state for history logging
    cursor.execute("SELECT custom_data, status FROM Workspace_Artifacts WHERE artifact_id = ?", (artifact_id,))
    row = cursor.fetchone()
    previous_state = {}
    if row:
        try:
            previous_state = json.loads(row['custom_data']) if row['custom_data'] else {}
        except json.JSONDecodeError:
            pass
        previous_state["status"] = row['status']
        
    new_state_json = json.dumps(custom_data)
    previous_state_json = json.dumps(previous_state)
    
    # 2. Update Workspace_Artifacts
    cursor.execute("""
        UPDATE Workspace_Artifacts 
        SET summary = ?, custom_data = ?, status = ?
        WHERE artifact_id = ?
    """, (summary, new_state_json, status, artifact_id))
    
    # 3. Insert into Artifact_History
    now = int(time.time())
    cursor.execute("""
        INSERT INTO Artifact_History (artifact_id, timestamp, actor, action_type, previous_state, new_state)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (artifact_id, now, "LLM_ENGINE", "AI_EXTRACTION", previous_state_json, new_state_json))
    
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Processing Pipelines
# ---------------------------------------------------------------------------

def process_gmail_thread(artifact_id: str, email_context: Dict[str, Any], dynamic_array_str: str, whitelist_str: str) -> None:
    """
    Single-Pass processing for Gmail threads.
    """
    prompt = PROMPT_GMAIL.replace("[DYNAMIC_ARRAY]", dynamic_array_str)
    full_context = f"Whitelist:\n{whitelist_str}\n\nEmail Context:\n{json.dumps(email_context, indent=2)}"
    
    print(f"Processing Gmail thread {artifact_id}...")
    result = call_gemini(prompt, full_context)
    
    if result:
        persist_llm_results(
            artifact_id=artifact_id,
            summary=result.get("summary", ""),
            custom_data=result, # Storing the entire result including requires_action, taxonomy_path
            status="PROCESSED"
        )
        print(f"Successfully processed {artifact_id}")
    else:
        update_artifact_status(artifact_id, "ERROR_LLM_PARSE")
        print(f"Failed to parse LLM output for {artifact_id}")

def process_drive_document(artifact_id: str, ocr_text: str, correspondent_whitelist: str, purpose_whitelist: str, dynamic_array_str: str) -> None:
    """
    Two-Stage Triage processing for Drive documents.
    """
    print(f"Processing Drive document {artifact_id} (Stage 1)...")
    
    # Stage 1: Triage (Identify Correspondent)
    context_s1 = f"Whitelist:\n{correspondent_whitelist}\n\nOCR Text:\n{ocr_text}"
    result_s1 = call_gemini(PROMPT_DRIVE_STAGE_1, context_s1)
    
    if not result_s1 or not result_s1.get("correspondent"):
        update_artifact_status(artifact_id, "ERROR_STAGE_1_FAILED")
        print(f"Stage 1 failed for {artifact_id}")
        return
        
    correspondent = result_s1["correspondent"]
    
    if correspondent == "UNKNOWN":
        update_artifact_status(artifact_id, "UNKNOWN_CORRESPONDENT")
        print(f"Unknown correspondent for {artifact_id}")
        return
        
    print(f"Correspondent identified as '{correspondent}'. Proceeding to Stage 2...")
    
    # Stage 2: Enforce & Extract
    prompt_s2 = PROMPT_DRIVE_STAGE_2.replace("[CORRESPONDENT]", correspondent).replace("[DYNAMIC_ARRAY]", dynamic_array_str)
    context_s2 = f"Purpose Whitelist:\n{purpose_whitelist}\n\nOCR Text:\n{ocr_text}"
    result_s2 = call_gemini(prompt_s2, context_s2)
    
    if result_s2:
        # Merge correspondent into the final custom data payload
        custom_data = result_s2.get("custom_fields", {})
        if not isinstance(custom_data, dict):
            custom_data = {"raw_custom_fields": custom_data}
            
        custom_data["document_date"] = result_s2.get("document_date")
        custom_data["title"] = result_s2.get("title")
        custom_data["purpose"] = result_s2.get("purpose")
        custom_data["correspondent"] = correspondent
        
        persist_llm_results(
            artifact_id=artifact_id,
            summary=result_s2.get("title", ""),
            custom_data=custom_data,
            status="PROCESSED"
        )
        print(f"Successfully processed {artifact_id}")
    else:
        update_artifact_status(artifact_id, "ERROR_STAGE_2_FAILED")
        print(f"Stage 2 failed for {artifact_id}")

if __name__ == "__main__":
    print("Nexus Hub LLM Engine initialized.")
