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

def fetch_active_prompt(prompt_key: str) -> str:
    """Fetches the active prompt from the Config_Prompts table in the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT prompt_text FROM Config_Prompts WHERE target_app = ?", (prompt_key,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Prompt {prompt_key} not found in database.")
    return row['prompt_text']

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

def run_sandbox_prompt(artifact_id: str, prompt_string: str) -> Optional[Dict[str, Any]]:
    """
    Executes a temporary prompt against an artifact's raw text without saving state.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT raw_text FROM Workspace_Artifacts WHERE artifact_id = ?", (artifact_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row['raw_text']:
        raise ValueError(f"Artifact {artifact_id} not found or has no raw text.")
        
    raw_text = row['raw_text']
    context = f"Raw Text:\n{raw_text}"
    return call_gemini(prompt_string, context)

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

async def generate_tuning_rule(artifact_id: str, original_json: Dict[str, Any], corrected_json: Dict[str, Any]) -> None:
    """
    Asynchronously generates a tuning rule based on a user's manual override
    and appends it to the correspondent's active prompt.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT raw_text FROM Workspace_Artifacts WHERE artifact_id = ?", (artifact_id,))
    row = cursor.fetchone()
    if not row or not row['raw_text']:
        conn.close()
        return
        
    raw_text = row['raw_text']
    
    # Extract correspondent from corrected JSON or default to UNKNOWN
    correspondent = corrected_json.get("correspondent")
    if not correspondent:
        taxonomy = corrected_json.get("taxonomy_path", "")
        parts = taxonomy.split('\\')
        if len(parts) >= 2:
            correspondent = parts[1].strip()
        else:
            correspondent = "UNKNOWN"

    prompt = f"""You are an AI Systems Engineer optimizing a routing ruleset. In a previous execution, the model miscategorized a document.

**Original Text:** {raw_text}
**Model Output:** {json.dumps(original_json)}
**User Correction:** {json.dumps(corrected_json)}

**Task:** Analyze why the model failed. Generate a concise, 1-sentence strict routing rule that will prevent this specific error in the future. This rule will be appended to the system prompt for this Correspondent.
**Output:** ONLY valid JSON: {{ "error_analysis": "string", "new_routing_rule": "string" }}"""

    # We call the synchronous call_gemini. In a fully async system, we'd use run_in_threadpool.
    result = call_gemini(prompt, "")
    
    if result and "new_routing_rule" in result:
        new_rule = result["new_routing_rule"]
        
        cursor.execute("SELECT prompt_text FROM Config_Prompts WHERE target_app = ?", (correspondent,))
        prompt_row = cursor.fetchone()
        
        if prompt_row:
            existing_prompt = prompt_row['prompt_text']
            updated_prompt = existing_prompt + f"\n- {new_rule}"
            cursor.execute("UPDATE Config_Prompts SET prompt_text = ? WHERE target_app = ?", (updated_prompt, correspondent))
        else:
            # If no correspondent-specific prompt exists, create one using DRIVE_STAGE_2 as base
            cursor.execute("SELECT prompt_text FROM Config_Prompts WHERE target_app = 'DRIVE_STAGE_2'")
            base_row = cursor.fetchone()
            base_prompt = base_row['prompt_text'] if base_row else ""
            updated_prompt = base_prompt + f"\n- {new_rule}"
            cursor.execute("INSERT INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", (correspondent, updated_prompt))
            
        conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Processing Pipelines
# ---------------------------------------------------------------------------

def normalize_taxonomy(extracted_tag: str, whitelist_str: str) -> str:
    """
    Normalizes common plural/misspelled tags before evaluation.
    If it fails to match the whitelist, enforces 'Purpose/Review'.
    """
    if not extracted_tag:
        return "Purpose/Review"
        
    extracted_tag = extracted_tag.strip()
    whitelist = [item.strip() for item in whitelist_str.split('\n') if item.strip()]
    
    if extracted_tag in whitelist:
        return extracted_tag
        
    # Attempt basic plural normalization
    if extracted_tag.endswith('s') and extracted_tag[:-1] in whitelist:
        return extracted_tag[:-1]
    if extracted_tag.endswith('es') and extracted_tag[:-2] in whitelist:
        return extracted_tag[:-2]
        
    # Aggressively enforce exception fallback
    return "Purpose/Review"

def process_gmail_thread(artifact_id: str, email_context: Dict[str, Any], dynamic_array_str: str, whitelist_str: str) -> None:
    """
    Single-Pass processing for Gmail threads.
    """
    prompt = fetch_active_prompt('GMAIL').replace("[DYNAMIC_ARRAY]", dynamic_array_str)
    full_context = f"Whitelist:\n{whitelist_str}\n\nEmail Context:\n{json.dumps(email_context, indent=2)}"
    
    print(f"Processing Gmail thread {artifact_id}...")
    result = call_gemini(prompt, full_context)
    
    if result:
        # Normalize the taxonomy mapping
        taxonomy_path = result.get("taxonomy_path", "")
        normalized_path = normalize_taxonomy(taxonomy_path, whitelist_str)
        result["taxonomy_path"] = normalized_path
        
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
    result_s1 = call_gemini(fetch_active_prompt('DRIVE_STAGE_1'), context_s1)
    
    if not result_s1 or not result_s1.get("correspondent"):
        update_artifact_status(artifact_id, "ERROR_STAGE_1_FAILED")
        print(f"Stage 1 failed for {artifact_id}")
        return
        
    correspondent = result_s1["correspondent"]
    correspondent = normalize_taxonomy(correspondent, correspondent_whitelist)
    
    if correspondent == "UNKNOWN" or correspondent == "Purpose/Review":
        update_artifact_status(artifact_id, "UNKNOWN_CORRESPONDENT")
        print(f"Unknown correspondent for {artifact_id}")
        return
        
    print(f"Correspondent identified as '{correspondent}'. Proceeding to Stage 2...")
    
    # Stage 2: Enforce & Extract
    prompt_s2 = fetch_active_prompt('DRIVE_STAGE_2').replace("[CORRESPONDENT]", correspondent).replace("[DYNAMIC_ARRAY]", dynamic_array_str)
    context_s2 = f"Purpose Whitelist:\n{purpose_whitelist}\n\nOCR Text:\n{ocr_text}"
    result_s2 = call_gemini(prompt_s2, context_s2)
    
    if result_s2:
        # Normalize purpose
        purpose = result_s2.get("purpose", "")
        normalized_purpose = normalize_taxonomy(purpose, purpose_whitelist)
        result_s2["purpose"] = normalized_purpose
        
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
