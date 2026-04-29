import re

def update_llm_engine(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update signature
    content = content.replace('def process_gmail_thread(artifact_id: str, email_context: Dict[str, Any], dynamic_array_str: str) -> None:',
                              'def process_gmail_thread(artifact_id: str, email_context: Dict[str, Any], dynamic_array_str: str) -> bool:')

    # 2. Update queries
    content = content.replace('tc.custom_extraction_rules as c_rules, tp.custom_extraction_rules as p_rules',
                              'tc.custom_extraction_rules as c_rules, tp.custom_extraction_rules as p_rules,\n               tp.auto_archive as auto_archive')

    content = content.replace('SELECT name as purpose_name, custom_extraction_rules as p_rules\n        FROM Taxonomy_Purposes',
                              'SELECT name as purpose_name, custom_extraction_rules as p_rules, auto_archive\n        FROM Taxonomy_Purposes')

    # 3. Add auto_archive_map
    content = content.replace('whitelist_paths = []', 'whitelist_paths = []\n    auto_archive_map = {}')

    content = content.replace("global_purps_list = [{'name': gp['purpose_name'], 'rules': gp['p_rules']} for gp in global_purposes]",
                              "global_purps_list = [{'name': gp['purpose_name'], 'rules': gp['p_rules'], 'auto_archive': gp['auto_archive']} for gp in global_purposes]")

    content = content.replace('whitelist_paths.append(taxonomy_path)',
                              "whitelist_paths.append(taxonomy_path)\n        auto_archive_map[taxonomy_path] = bool(row['auto_archive'])")

    content = content.replace('whitelist_paths.append(global_path)',
                              "whitelist_paths.append(global_path)\n                auto_archive_map[global_path] = bool(gp['auto_archive'])")

    # 4. Update return value
    # The print statement is "print(f\"Successfully processed {artifact_id}\")"
    content = content.replace('print(f"Successfully processed {artifact_id}")',
                              'print(f"Successfully processed {artifact_id}")\n        return auto_archive_map.get(normalized_path, False)')

    # The other print is "print(f\"Failed to parse LLM output for {artifact_id}\")"
    content = content.replace('print(f"Failed to parse LLM output for {artifact_id}")',
                              'print(f"Failed to parse LLM output for {artifact_id}")\n        return False')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

update_llm_engine('llm_engine.py')
