"""
LLM Engine for Nexus.
Handles batch processing and Gemini API interactions for automated metadata extraction.
Implements Two-Stage Triage for Drive documents and Single-Pass extraction for Gmail.
"""

import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
import os
import sqlite3
import time
from typing import Dict, Any, Optional, Tuple, List

from google import genai
from google.genai import types
from tenacity import retry, wait_exponential, stop_after_attempt

from db_init import DB_PATH

def strip_markdown_json(text: str) -> str:
    """
    Strips markdown code blocks from a string to prepare it for JSON parsing.
    """
    raw_text = text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    return raw_text.strip()

# ---------------------------------------------------------------------------
# Master AI Prompts (Section 9.3)
# ---------------------------------------------------------------------------

def fetch_active_prompt(prompt_key: str) -> str:
    """
    Fetches the active prompt from the Config_Prompts table in the database.
    
    Args:
        prompt_key (str): The unique identifier for the target application (e.g., 'GMAIL', 'DRIVE_STAGE_1').
        
    Returns:
        str: The raw prompt text stored in the SQLite database.
        
    Raises:
        ValueError: If the requested prompt_key does not exist.
    """
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
    """
    Initializes the Gemini client, explicitly using NEXUS_API_KEY from environment.
    
    Returns:
        genai.Client: An initialized Google GenAI SDK client.
        
    Raises:
        ValueError: If the 'NEXUS_API_KEY' environment variable is not defined or empty.
    """
    api_key = os.getenv("NEXUS_API_KEY")
    if not api_key:
        logger.error("CRITICAL: NEXUS_API_KEY environment variable is missing or empty. LLM Engine cannot proceed.")
        raise ValueError("NEXUS_API_KEY environment variable is not set or empty.")
    
    # Explicitly pass api_key to ensure the SDK does not fall back to GEMINI_API_KEY
    return genai.Client(api_key=api_key)

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def call_gemini(prompt: str, context: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, int]]:
    """
    Calls the Gemini API with exponential backoff and forces JSON output.
    Safely handles parsing errors with a try/except block to catch hallucinated text.
    
    Args:
        prompt (str): The master system prompt dictating behavior and rules.
        context (str): The payload data (OCR text, email body, entity profiles).
        
    Returns:
        Tuple[Optional[Dict[str, Any]], Dict[str, int]]: The parsed JSON dictionary from Gemini, and telemetry metadata.
    """
    client = get_genai_client()
    import time
    start_time = time.time()
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, context],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        end_time = time.time()
        elapsed_ms = int((end_time - start_time) * 1000)
        tokens = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') and response.usage_metadata else 0
        telemetry = {"processing_time_ms": elapsed_ms, "api_tokens_used": tokens}
        return json.loads(response.text), telemetry
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Parsing Error or Safety Block. Details: {e}")
        if response and response.text:
            print(f"Raw Output: {response.text}")
        return None, {}
    except Exception as e:
        print(f"Gemini API Error: {e}")
        raise # Raise to trigger tenacity retry

def run_sandbox_prompt(artifact_id: str, prompt_string: str) -> Optional[Dict[str, Any]]:
    """
    Executes a temporary prompt against an artifact's raw text without saving state.
    Used exclusively by the frontend Sandbox UI to test prompt iterations securely.
    
    Args:
        artifact_id (str): The unique identifier of the artifact to test against.
        prompt_string (str): The temporary experimental prompt.
        
    Returns:
        Optional[Dict[str, Any]]: The JSON output from Gemini.
        
    Raises:
        ValueError: If the artifact does not exist or lacks raw text.
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
    result, _ = call_gemini(prompt_string, context)
    return result

# ---------------------------------------------------------------------------
# Database Operations
# ---------------------------------------------------------------------------

def update_artifact_status(artifact_id: str, status: str) -> None:
    """
    Updates only the status of an artifact, usually in response to an extraction failure.
    
    Args:
        artifact_id (str): The target artifact.
        status (str): The new status string (e.g., 'ERROR_LLM_PARSE').
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    cursor.execute("UPDATE Workspace_Artifacts SET status = ? WHERE artifact_id = ?", (status, artifact_id))
    conn.commit()
    conn.close()

def persist_llm_results(artifact_id: str, summary: str, custom_data: Dict[str, Any], status: str, telemetry: Dict[str, int] = {}) -> None:
    """
    Writes the successful extraction to Workspace_Artifacts and logs the change to Artifact_History
    for strict immutable auditing.
    
    Args:
        artifact_id (str): The processed artifact ID.
        summary (str): The 1-sentence summary generated by the LLM.
        custom_data (Dict[str, Any]): The dynamic JSON payload containing extracted fields.
        status (str): The new operational status (e.g., 'PROCESSED', 'Purpose/Review').
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
    processing_time_ms = telemetry.get('processing_time_ms')
    api_tokens_used = telemetry.get('api_tokens_used')
    cursor.execute("""
        INSERT INTO Artifact_History (artifact_id, timestamp, actor, action_type, previous_state, new_state, processing_time_ms, api_tokens_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (artifact_id, now, "LLM_ENGINE", "AI_EXTRACTION", previous_state_json, new_state_json, processing_time_ms, api_tokens_used))
    
    conn.commit()
    conn.close()

async def generate_tuning_rule(artifact_id: str, original_json: Dict[str, Any], corrected_json: Dict[str, Any]) -> None:
    """
    Asynchronously generates a tuning rule based on a user's manual override
    and appends it to the correspondent's active prompt inside the Config_Prompts table.
    
    Args:
        artifact_id (str): The ID of the artifact that was miscategorized.
        original_json (Dict[str, Any]): The incorrect payload generated by the model.
        corrected_json (Dict[str, Any]): The ground-truth payload submitted by the human user.
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
    result, _ = call_gemini(prompt, "")
    
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
    
    Args:
        extracted_tag (str): The raw string returned by the LLM.
        whitelist_str (str): The newline-separated master whitelist from the database.
        
    Returns:
        str: The normalized string, or 'Purpose/Review' if no exact match is found.
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

def process_gmail_thread(artifact_id: str, email_context: Dict[str, Any], dynamic_array_str: str) -> bool:
    """
    Single-Pass processing for Gmail threads.
    Injects full multi-dimensional taxonomy profiles and extracts metadata in one prompt.
    
    Args:
        artifact_id (str): The unique database key for the Gmail thread.
        email_context (Dict[str, Any]): The thread metadata (Sender, Subject, Body Snippet).
        dynamic_array_str (str): A stringified JSON array of custom fields to request from the LLM.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.name as correspondent_name, p.name as purpose_name, 
               c.name as category_name, e.workspace_alias
        FROM purposes p
        JOIN categories c ON p.category_id = c.id
        JOIN entities e ON e.category_id = c.id
        WHERE p.scope = 'Categorical' AND e.nexus_state = 'active'
    """)
    rows = cursor.fetchall()

    cursor.execute("""
        SELECT name as purpose_name
        FROM purposes
        WHERE scope = 'Universal'
    """)
    global_purposes = cursor.fetchall()
    
    # Pre-fetch aliases for entities to replicate "sending_subdomains" contextual info
    cursor.execute("""
        SELECT e.name as entity_name, a.alias_string 
        FROM aliases a
        JOIN entities e ON a.entity_id = e.id
        WHERE e.nexus_state = 'active'
    """)
    alias_rows = cursor.fetchall()
    aliases_by_entity = {}
    for r in alias_rows:
        ent = r['entity_name']
        if ent not in aliases_by_entity:
            aliases_by_entity[ent] = []
        aliases_by_entity[ent].append(r['alias_string'])

    conn.close()

    entity_profiles = {}
    whitelist_paths = []
    auto_archive_map = {}
    
    global_purps_list = [{'name': gp['purpose_name']} for gp in global_purposes]
    
    for row in rows:
        corr_name = row['correspondent_name']
        purp_name = row['purpose_name']
        cat_name = row['category_name']
        
        taxonomy_path = f"{cat_name} \\ {corr_name} \\ {purp_name}"
        whitelist_paths.append(taxonomy_path)
        auto_archive_map[taxonomy_path] = False # Safe default since auto_archive is removed
        
        # Append global purposes to the current correspondent
        for gp in global_purps_list:
            global_path = f"{cat_name} \\ {corr_name} \\ {gp['name']}"
            if global_path not in whitelist_paths:
                whitelist_paths.append(global_path)
                auto_archive_map[global_path] = False
        
        if corr_name not in entity_profiles:
            profile = {
                'aliases': aliases_by_entity.get(corr_name, []),
                'workspace_alias': row['workspace_alias'] or ''
            }
            entity_profiles[corr_name] = profile

    whitelist_str = "\n".join(whitelist_paths)
    profiles_str = json.dumps(entity_profiles, indent=2)

    with open(os.path.join("DEFAULTS", "gmail_extraction.tmpl"), "r", encoding="utf-8") as f:
        prompt = f.read().replace("[DYNAMIC_ARRAY]", dynamic_array_str)
    prompt = prompt.replace("[ENTITY_PROFILES]", profiles_str)
    
    full_context = f"Entity Profiles:\n{profiles_str}\n\nEmail Context:\n{json.dumps(email_context, indent=2)}"
    
    print(f"Processing Gmail thread {artifact_id}...")
    
    # Architectural Intent: Single-Pass for Gmail
    # Because Gmail already provides heavily structured context (explicit verified Senders, Subjects),
    # the LLM can confidently route the document to the deepest Purpose node in a single request,
    # optimizing API latency and cost.
    result, telemetry = call_gemini(prompt, full_context)
    
    if result:
        # Normalize the taxonomy mapping
        taxonomy_path = result.get("taxonomy_path", "")
        normalized_path = normalize_taxonomy(taxonomy_path, whitelist_str)
        result["taxonomy_path"] = normalized_path
        
        discovered_purpose = result.get("discovered_purpose")
        if discovered_purpose and normalized_path == "Purpose/Review":
            result["pending_discovery"] = discovered_purpose
            status = "Purpose/Review"
        elif normalized_path == "Purpose/Review":
            status = "Purpose/Review"
        else:
            status = "PROCESSED"
        
        persist_llm_results(
            artifact_id=artifact_id,
            summary=result.get("summary", ""),
            custom_data=result, # Storing the entire result including requires_action, taxonomy_path
            status=status,
            telemetry=telemetry
        )
        print(f"Successfully processed {artifact_id}")
        return auto_archive_map.get(normalized_path, False)
    else:
        update_artifact_status(artifact_id, "ERROR_LLM_PARSE")
        print(f"Failed to parse LLM output for {artifact_id}")
        return False

def process_drive_document(artifact_id: str, ocr_text: str, dynamic_array_str: str) -> None:
    """
    Two-Stage Triage processing for Drive documents.
    Validates the Correspondent before requesting expensive custom field extractions.
    
    Args:
        artifact_id (str): The unique database key for the Drive document.
        ocr_text (str): The raw, unformatted text stripped from the PDF/Image.
        dynamic_array_str (str): A stringified JSON array of custom fields to request during Stage 2.
    """
    print(f"Processing Drive document {artifact_id} (Stage 1)...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.name as correspondent_name, e.workspace_alias
        FROM entities e
        JOIN categories c ON e.category_id = c.id
        WHERE e.nexus_state = 'active' AND e.use_in_drive_structure = 1
    """)
    corr_rows = cursor.fetchall()

    cursor.execute("""
        SELECT e.name as entity_name, a.alias_string 
        FROM aliases a
        JOIN entities e ON a.entity_id = e.id
        WHERE e.nexus_state = 'active'
    """)
    alias_rows = cursor.fetchall()
    aliases_by_entity = {}
    for r in alias_rows:
        ent = r['entity_name']
        if ent not in aliases_by_entity:
            aliases_by_entity[ent] = []
        aliases_by_entity[ent].append(r['alias_string'])

    entity_profiles = {}
    correspondent_whitelist = []
    for row in corr_rows:
        corr_name = row['correspondent_name']
        correspondent_whitelist.append(corr_name)
            
        entity_profiles[corr_name] = {
            'aliases': aliases_by_entity.get(corr_name, []),
            'workspace_alias': row['workspace_alias'] or ''
        }
    
    profiles_str = json.dumps(entity_profiles, indent=2)
    correspondent_whitelist_str = "\n".join(correspondent_whitelist)

    # Stage 1: Triage (Identify Correspondent)
    # Architectural Intent: Two-Stage Triage for Drive
    # Drive documents are entirely unstructured OCR text. Injecting the entire taxonomy schema
    # simultaneously overwhelms the LLM and dilutes field-specific instructions. Stage 1 identifies
    # the Vendor/Correspondent first.
    prompt_s1 = fetch_active_prompt('DRIVE_STAGE_1').replace("[ENTITY_PROFILES]", profiles_str)
    context_s1 = f"Entity Profiles:\n{profiles_str}\n\nOCR Text:\n{ocr_text}"
    result_s1, telemetry_s1 = call_gemini(prompt_s1, context_s1)
    
    if not result_s1 or not result_s1.get("correspondent"):
        update_artifact_status(artifact_id, "ERROR_STAGE_1_FAILED")
        print(f"Stage 1 failed for {artifact_id}")
        conn.close()
        return
        
    correspondent = result_s1["correspondent"]
    correspondent = normalize_taxonomy(correspondent, correspondent_whitelist_str)
    
    if correspondent == "UNKNOWN" or correspondent == "Purpose/Review":
        discovered = result_s1.get("discovered_correspondent")
        if discovered:
            custom_data = {"pending_discovery": discovered}
            persist_llm_results(artifact_id, "Pending Discovery", custom_data, "Correspondent/Review", telemetry_s1)
            print(f"Unknown correspondent for {artifact_id}, routed to Correspondent/Review with discovery: {discovered}")
        else:
            update_artifact_status(artifact_id, "UNKNOWN_CORRESPONDENT")
            print(f"Unknown correspondent for {artifact_id}")
        conn.close()
        return
        
    print(f"Correspondent identified as '{correspondent}'. Proceeding to Stage 2...")
    
    # Stage 2: Query Purposes for this Correspondent
    # Architectural Intent: We dynamically construct a tiny, hyper-focused prompt only containing
    # the valid Purposes for the successfully verified Stage 1 Correspondent.

    cursor.execute("""
        SELECT p.name as purpose_name
        FROM purposes p
        LEFT JOIN entities e ON p.category_id = e.category_id
        WHERE e.name = ? OR p.scope = 'Universal'
    """, (correspondent,))
    purp_rows = cursor.fetchall()
    conn.close()
    
    purpose_whitelist = []
    for row in purp_rows:
        purpose_whitelist.append(row['purpose_name'])
            
    purpose_whitelist_str = "\n".join(purpose_whitelist)
    
    # Stage 2: Enforce & Extract
    prompt_s2 = fetch_active_prompt('DRIVE_STAGE_2').replace("[CORRESPONDENT]", correspondent).replace("[DYNAMIC_ARRAY]", dynamic_array_str)
    context_s2 = f"Purpose Whitelist:\n{purpose_whitelist_str}\n\nOCR Text:\n{ocr_text}"
    try:
        result_s2, telemetry_s2 = call_gemini(prompt_s2, context_s2)
    except RetryError as e:
        print(f"LLM processing failed after all retries for {artifact_id}: {e}")
        update_artifact_status(artifact_id, "FAILED")
        return
    combined_telemetry = {
        'processing_time_ms': telemetry_s1.get('processing_time_ms', 0) + telemetry_s2.get('processing_time_ms', 0),
        'api_tokens_used': telemetry_s1.get('api_tokens_used', 0) + telemetry_s2.get('api_tokens_used', 0)
    }
    
    if result_s2:
        # Normalize purpose
        purpose = result_s2.get("purpose", "")
        normalized_purpose = normalize_taxonomy(purpose, purpose_whitelist_str)
        result_s2["purpose"] = normalized_purpose
        
        # Merge correspondent into the final custom data payload
        custom_data = result_s2.get("custom_fields", {})
        if not isinstance(custom_data, dict):
            custom_data = {"raw_custom_fields": custom_data}
            
        custom_data["document_date"] = result_s2.get("document_date")
        custom_data["title"] = result_s2.get("title")
        custom_data["purpose"] = result_s2.get("purpose")
        custom_data["correspondent"] = correspondent
        
        discovered_purpose = result_s2.get("discovered_purpose")
        if discovered_purpose and normalized_purpose == "Purpose/Review":
            custom_data["pending_discovery"] = discovered_purpose
            status = "Purpose/Review"
        elif normalized_purpose == "Purpose/Review":
            status = "Purpose/Review"
        else:
            status = "PROCESSED"
        
        persist_llm_results(
            artifact_id=artifact_id,
            summary=result_s2.get("title", ""),
            custom_data=custom_data,
            status=status,
            telemetry=combined_telemetry
        )
        print(f"Successfully processed {artifact_id}")
        return auto_archive_map.get(normalized_path, False)
    else:
        update_artifact_status(artifact_id, "ERROR_STAGE_2_FAILED")
        print(f"Stage 2 failed for {artifact_id}")

def ask_rag(question: str) -> str:
    """
    Converts a natural language query into an automated SQLite fetch and contextual summary.
    
    Args:
        question (str): The natural language string submitted by the user.
        
    Returns:
        str: A human-readable synthesis constructed by Gemini based on database rows.
    """
    prompt_sql = f"""You are a SQLite expert. Convert the user's question into a safe SQLite query targeting the `Workspace_Artifacts` table.
Table Schema:
- artifact_id (TEXT PRIMARY KEY)
- taxonomy_id (INTEGER)
- raw_text (TEXT)
- summary (TEXT)
- custom_data (TEXT JSON)
- status (TEXT)

Question: {question}

Return ONLY valid JSON containing the SQL query. Do not return anything else. Limit results to 10.
{{ "sql": "SELECT ... LIMIT 10" }}"""

    sql_json, _ = call_gemini(prompt_sql, "")
    if not sql_json or "sql" not in sql_json:
        return "Sorry, I couldn't generate a query for that."
        
    sql = sql_json["sql"]
    
    assert sql.upper().startswith("SELECT"), "Query must start with SELECT"
    if any(keyword in sql.upper() for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]):
        raise ValueError("Destructive queries are not allowed.")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
    except Exception as e:
        conn.close()
        return f"Database error: {e}"
    conn.close()
    
    if not rows:
        return "No relevant artifacts found in the database."
        
    fetched_data = [dict(row) for row in rows]
    
    prompt_summary = f"""You are an AI Assistant. Answer the user's question based ONLY on the provided database rows.

Question: {question}
Database Rows: {json.dumps(fetched_data, indent=2)}

Return ONLY valid JSON containing the answer.
{{ "answer": "Your human-readable summary" }}"""

    summary_json, _ = call_gemini(prompt_summary, "")
    if summary_json and "answer" in summary_json:
        return summary_json["answer"]
    
    return "Sorry, I couldn't generate a summary."

def evaluate_quarantine_clusters(conn: sqlite3.Connection) -> None:
    """
    Evaluates clustered artifacts in the quarantine queue.
    Currently acts as a safe stub to prevent sync_engine crashes.
    """
    print("Quarantine evaluation bypassed: Stub implementation active.")

async def append_zero_shot_rule(artifact_ids: list[str], instruction: str) -> dict:
    """
    Appends a new extraction rule instruction to the purpose shared by the provided artifacts.
    (Stubbed out in Zero Trust schema because custom_extraction_rules was removed from purposes table).
    """
    return {"status": "error", "message": "Zero-shot rules are deprecated in the Zero Trust Schema architecture."}

if __name__ == "__main__":
    print("Nexus LLM Engine initialized.")


def deduplicate_legacy_labels(raw_labels: list) -> list:
    """
    Uses Gemini to lexically deduplicate a list of raw legacy labels.
    """
    with open(os.path.join("DEFAULTS", "deduplicate_legacy_labels.tmpl"), "r", encoding="utf-8") as f:
        prompt = f.read()
    
    context = json.dumps(raw_labels)
    result, _ = call_gemini(prompt, context)
    
    ret = []
    if isinstance(result, list):
        ret = result
    elif isinstance(result, dict) and 'labels' in result:
        ret = result['labels']
    elif isinstance(result, dict):
        for val in result.values():
            if isinstance(val, list):
                ret = val
                break
                
    from diagnostics import write_migration_trace
    write_migration_trace("2_DEDUPLICATED_LABELS", ret)
    return ret

def profile_and_map_entities(cleaned_labels: list, current_categories: list) -> list:
    """
    Profiles deduplicated labels in batches using Search Grounding and maps them to categories.
    """
    client = get_genai_client()
    with open(os.path.join("DEFAULTS", "profile_and_map_entities.tmpl"), "r", encoding="utf-8") as f:
        prompt = f.read().replace("[CURRENT_CATEGORIES]", json.dumps(current_categories))

    all_results = []
    for i in range(0, len(cleaned_labels), 10):
        batch = cleaned_labels[i:i+10]
        context = json.dumps(batch)
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, context],
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                ),
            )
            batch_result = json.loads(strip_markdown_json(response.text))
            if isinstance(batch_result, list):
                all_results.extend(batch_result)
            elif isinstance(batch_result, dict):
                for k, v in batch_result.items():
                    if isinstance(v, list):
                        all_results.extend(v)
                        break
        except Exception as e:
            logger.error(f"Error in profile_and_map_entities batch: {e}")
            
    from diagnostics import write_migration_trace
    write_migration_trace("3_PROFILED_ENTITIES", all_results)
    return all_results

# ---------------------------------------------------------------------------
# Zero Trust AI Service Layer
# ---------------------------------------------------------------------------

def run_agent_profiler(domain: str, is_personal: bool = False, context: str = None) -> Optional[Dict[str, Any]]:
    """
    Runs the appropriate profiler agent (personal or commercial) to identify the entity.
    """
    prompt_key = 'agent_profiler_personal' if is_personal else 'agent_profiler_commercial'
    prompt = fetch_active_prompt(prompt_key)
    
    client = get_genai_client()
    start_time = time.time()
    
    logger.info(f"Initiating Profiler for {domain}")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, context or f"Evaluate domain/email: {domain}"],
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            ),
        )
        end_time = time.time()
        elapsed = end_time - start_time
        
        logger.debug(f"Raw Gemini response: {response.text}")
        logger.info(f"Profiler completed in {elapsed:.2f} seconds.")
        
        return json.loads(strip_markdown_json(response.text))
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Parsing Error or Safety Block in Profiler. Details: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini API Error in Profiler: {e}")
        raise

def run_agent_classifier(artifact_text: str, entity_known: bool = False, allowed_categories: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Runs the Zero Trust Classifier. Maps artifact to Category and Purpose.
    """
    prompt = fetch_active_prompt('agent_classifier')
    
    context = f"Artifact Text:\n{artifact_text}"
    if entity_known:
        context += "\n\nNote: Entity is known, only evaluate for Purpose."
    if allowed_categories:
        context += f"\n\nAllowed Categories: {', '.join(allowed_categories)}"
        
    client = get_genai_client()
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, context],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        
        # Telemetry
        category_id = result.get('category_id')
        purpose_id = result.get('purpose_id')
        logger.info(f"Classifier resolved Category ID: {category_id}, Purpose ID: {purpose_id}")
        
        return result
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Parsing Error or Safety Block in Classifier. Hallucination catch. Details: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini API Error in Classifier: {e}")
        raise

def run_bulk_profiler(sender: str, bulk_context: str) -> Optional[Dict[str, Any]]:
    """
    Uses profiler prompt with concatenated snippets to profile an entity in bulk.
    """
    prompt_key = 'agent_profiler_commercial' # Defaulting to commercial, could be dynamic
    prompt = fetch_active_prompt(prompt_key)
    
    client = get_genai_client()
    context = f"Evaluate domain/email: {sender}\n\nBulk Context Snippets:\n{bulk_context}"
    logger.info(f"Initiating Bulk Profiler for {sender}")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, context],
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            ),
        )
        return json.loads(strip_markdown_json(response.text))
    except Exception as e:
        logger.error(f"Error in Bulk Profiler for {sender}: {e}")
        return None

def run_bulk_classifier(entity_name: str, artifacts: List[dict]) -> Optional[List[Dict[str, Any]]]:
    """
    Instructs LLM to map a JSON array of artifacts from the entity to specific Purposes.
    """
    client = get_genai_client()
    prompt = f"You are a Zero Trust Bulk Classifier. The entity is '{entity_name}'. Map each artifact in the following JSON array to a specific 'purpose' and return a JSON list of objects containing 'id' and 'purpose'."
    
    context = json.dumps(artifacts)
    logger.info(f"Initiating Bulk Classifier for {entity_name} with {len(artifacts)} artifacts")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, context],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and 'artifacts' in result:
            return result['artifacts']
        return result
    except Exception as e:
        logger.error(f"Error in Bulk Classifier for {entity_name}: {e}")
        return None
