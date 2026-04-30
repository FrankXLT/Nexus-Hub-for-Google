import json

def patch_llm_engine():
    with open("llm_engine.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update persist_llm_results signature
    content = content.replace(
        "def persist_llm_results(artifact_id: str, summary: str, custom_data: Dict[str, Any], status: str) -> None:",
        "def persist_llm_results(artifact_id: str, summary: str, custom_data: Dict[str, Any], status: str, telemetry: Dict[str, int] = {}) -> None:"
    )

    # 2. Update the Artifact_History INSERT inside persist_llm_results
    old_insert = """    cursor.execute(\"\"\"
        INSERT INTO Artifact_History (artifact_id, timestamp, actor, action_type, previous_state, new_state)
        VALUES (?, ?, ?, ?, ?, ?)
    \"\"\", (artifact_id, now, "LLM_ENGINE", "AI_EXTRACTION", previous_state_json, new_state_json))"""
    
    new_insert = """    processing_time_ms = telemetry.get('processing_time_ms')
    api_tokens_used = telemetry.get('api_tokens_used')
    cursor.execute(\"\"\"
        INSERT INTO Artifact_History (artifact_id, timestamp, actor, action_type, previous_state, new_state, processing_time_ms, api_tokens_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    \"\"\", (artifact_id, now, "LLM_ENGINE", "AI_EXTRACTION", previous_state_json, new_state_json, processing_time_ms, api_tokens_used))"""
    content = content.replace(old_insert, new_insert)

    # 3. Update call_gemini usages
    content = content.replace(
        "return call_gemini(prompt_string, context)",
        "result, _ = call_gemini(prompt_string, context)\n    return result"
    )
    content = content.replace(
        "result = call_gemini(prompt, \"\")",
        "result, _ = call_gemini(prompt, \"\")"
    )
    content = content.replace(
        "return call_gemini(prompt, context)",
        "result, _ = call_gemini(prompt, context)\n    return result"
    )

    # process_gmail_thread
    content = content.replace(
        "result = call_gemini(prompt, full_context)",
        "result, telemetry = call_gemini(prompt, full_context)"
    )
    content = content.replace(
        """        persist_llm_results(
            artifact_id=artifact_id,
            summary=result.get("summary", ""),
            custom_data=result, # Storing the entire result including requires_action, taxonomy_path
            status=status
        )""",
        """        persist_llm_results(
            artifact_id=artifact_id,
            summary=result.get("summary", ""),
            custom_data=result, # Storing the entire result including requires_action, taxonomy_path
            status=status,
            telemetry=telemetry
        )"""
    )

    # process_drive_document Stage 1
    content = content.replace(
        "result_s1 = call_gemini(prompt_s1, context_s1)",
        "result_s1, telemetry_s1 = call_gemini(prompt_s1, context_s1)"
    )
    content = content.replace(
        """persist_llm_results(artifact_id, "Pending Discovery", custom_data, "Correspondent/Review")""",
        """persist_llm_results(artifact_id, "Pending Discovery", custom_data, "Correspondent/Review", telemetry_s1)"""
    )

    # process_drive_document Stage 2
    content = content.replace(
        "result_s2 = call_gemini(prompt_s2, context_s2)",
        "result_s2, telemetry_s2 = call_gemini(prompt_s2, context_s2)\n    combined_telemetry = {\n        'processing_time_ms': telemetry_s1.get('processing_time_ms', 0) + telemetry_s2.get('processing_time_ms', 0),\n        'api_tokens_used': telemetry_s1.get('api_tokens_used', 0) + telemetry_s2.get('api_tokens_used', 0)\n    }"
    )
    content = content.replace(
        """        persist_llm_results(
            artifact_id=artifact_id,
            summary=result_s2.get("title", ""),
            custom_data=custom_data,
            status=status
        )""",
        """        persist_llm_results(
            artifact_id=artifact_id,
            summary=result_s2.get("title", ""),
            custom_data=custom_data,
            status=status,
            telemetry=combined_telemetry
        )"""
    )

    # ask_rag SQL
    content = content.replace(
        "sql_json = call_gemini(prompt_sql, \"\")",
        "sql_json, _ = call_gemini(prompt_sql, \"\")"
    )
    # ask_rag summary
    content = content.replace(
        "summary_json = call_gemini(prompt_summary, \"\")",
        "summary_json, _ = call_gemini(prompt_summary, \"\")"
    )

    with open("llm_engine.py", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    patch_llm_engine()
    print("Done")
