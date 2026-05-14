import os

db_init_path = 'backend/db_init.py'
with open(db_init_path, 'r', encoding='utf-8') as f:
    content = f.read()

prompts_code = '''
    PROMPT_AGENT_PROFILER_PERSONAL = "You are a Zero Trust Identity Profiler. Evaluate this personal email address. Return a strictly formatted JSON profiling the persona based on the provided context."
    PROMPT_AGENT_PROFILER_COMMERCIAL = "You are a Commercial Domain Profiler. Using web search grounding, evaluate this corporate domain. Identify the company, their industry, and map them to our internal business taxonomy."
    PROMPT_AGENT_CLASSIFIER = "You are a Zero Trust Classifier. Map this artifact to an established Category and Purpose. If the Entity is provided, only evaluate for Purpose."

    cursor.execute("SELECT target_app FROM Config_Prompts WHERE target_app = ?", ('agent_profiler_personal',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('agent_profiler_personal', PROMPT_AGENT_PROFILER_PERSONAL))
        
    cursor.execute("SELECT target_app FROM Config_Prompts WHERE target_app = ?", ('agent_profiler_commercial',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('agent_profiler_commercial', PROMPT_AGENT_PROFILER_COMMERCIAL))
        
    cursor.execute("SELECT target_app FROM Config_Prompts WHERE target_app = ?", ('agent_classifier',))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)", ('agent_classifier', PROMPT_AGENT_CLASSIFIER))
'''

target_str = "    cursor.execute(\"SELECT target_app FROM Config_Prompts WHERE target_app = ?\", ('DRIVE_STAGE_2',))\n    if cursor.fetchone() is None:\n        cursor.execute(\"INSERT INTO Config_Prompts (target_app, prompt_text) VALUES (?, ?)\", ('DRIVE_STAGE_2', PROMPT_DRIVE_STAGE_2))\n"

if target_str in content:
    content = content.replace(target_str, target_str + prompts_code)
else:
    print('Target string not found in db_init.py')
    exit(1)

with open(db_init_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated db_init.py successfully.')

llm_engine_path = 'backend/llm_engine.py'
with open(llm_engine_path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'import logging' not in content:
    content = content.replace('import json', 'import json\nimport logging\n\nlogger = logging.getLogger(__name__)\nlogging.basicConfig(level=logging.INFO)')

engine_code = '''
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
                response_mime_type="application/json",
                tools=[{"google_search_retrieval": {}}]
            ),
        )
        end_time = time.time()
        elapsed = end_time - start_time
        
        logger.debug(f"Raw Gemini response: {response.text}")
        logger.info(f"Profiler completed in {elapsed:.2f} seconds.")
        
        return json.loads(response.text)
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
    
    context = f"Artifact Text:\\n{artifact_text}"
    if entity_known:
        context += "\\n\\nNote: Entity is known, only evaluate for Purpose."
    if allowed_categories:
        context += f"\\n\\nAllowed Categories: {', '.join(allowed_categories)}"
        
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
'''

if 'def run_agent_profiler' not in content:
    content += '\n' + engine_code
else:
    print('Functions already present in llm_engine.py')

with open(llm_engine_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated llm_engine.py successfully.')
