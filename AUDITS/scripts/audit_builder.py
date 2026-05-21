import os
import ast
import re
import sqlite3
import sys
import json
from datetime import datetime

# Add project root to path for backend module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Mock dotenv to avoid ModuleNotFoundError
try:
    import dotenv
except ImportError:
    from unittest.mock import MagicMock
    sys.modules['dotenv'] = MagicMock()

from backend.db_init import init_db, DB_PATH

# Restricted directories to ignore
IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', 'venv', 'env', '.venv'}

def get_all_files(root_dir):
    """Recursively find all files in the repository."""
    all_files = []
    for root, dirs, files in os.walk(root_dir):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files

def parse_python_file(filepath):
    """Use AST to extract class and function definitions with signatures and docstrings."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read())
            
        definitions = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                sig = ""
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig = ast.unparse(node.args)
                
                doc = ast.get_docstring(node)
                definitions[node.name] = {
                    'signature': sig,
                    'docstring': doc if doc else ""
                }
        return definitions
    except Exception:
        return {}

def parse_js_file(filepath):
    """Use Regex to extract function names from JS/GS files."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Regex to find functions
        patterns = [
            r'function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)',
            r'const\s+([a-zA-Z0-9_]+)\s*=\s*\((.*?)\)',
            r'let\s+([a-zA-Z0-9_]+)\s*=\s*\((.*?)\)',
            r'var\s+([a-zA-Z0-9_]+)\s*=\s*\((.*?)\)',
            r'([a-zA-Z0-9_]+)\s*\(\)\s*\{'
        ]
        
        definitions = {}
        for p in patterns:
            matches = re.findall(p, content)
            for m in matches:
                # Handle regex tuples vs single match
                name = m[0] if isinstance(m, tuple) else m
                sig = m[1] if isinstance(m, tuple) and len(m) > 1 else ""
                
                if name not in definitions:
                    definitions[name] = {
                        'signature': sig,
                        'docstring': ""
                    }
        return definitions
    except Exception:
        return {}

def ensure_db_initialized(db_path=DB_PATH):
    """Bootstrap DB if empty."""
    if not os.path.exists(db_path):
        init_db(db_path)
        return

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        if not cursor.fetchall():
            init_db(db_path)

def enrich_census_with_ai(census_map):
    """Enrich census data using Gemini API."""
    from google import genai
    api_key = os.getenv("NEXUS_API_KEY")
    if not api_key:
        return {}

    client = genai.Client(api_key=api_key)
    prompt = """You are an expert Software Architect. I am providing a JSON map of files and their function signatures. For every single function, generate a precise, 1-sentence description of its purpose within a Zero-Trust Data Orchestration system. Return ONLY a valid JSON object mapping the function name to its description string. Do not use markdown wrappers."""
    
    # Build context: flat map of function details
    context_map = {}
    for file, defs in census_map.items():
        for name, details in defs.items():
            context_map[name] = details
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, json.dumps(context_map)],
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception:
        return {}

def generate_phase_1(root_dir='.'):
    """Generate the formatted Phase 1 Markdown report."""
    files = get_all_files(root_dir)
    census_map = {}
    
    # Build census map
    for file in sorted(files):
        if any(ignored in file for ignored in IGNORE_DIRS):
            continue
            
        ext = os.path.splitext(file)[1]
        if ext == '.py':
            defs = parse_python_file(file)
        elif ext in ['.js', '.gs', '.html']:
            defs = parse_js_file(file)
        else:
            continue
            
        if defs:
            census_map[file] = defs
            
    # Enrich with AI
    ai_descriptions = enrich_census_with_ai(census_map)
    
    output = ["# Phase 1: Total Census\n"]
    for file, defs in census_map.items():
        layer = "Backend/Script" if file.endswith('.py') else "Frontend"
        output.append(f"- **`{file}`** ({layer} Module)")
        for d, details in sorted(defs.items()):
            desc = ai_descriptions.get(d) or details.get('docstring') or "Description unavailable."
            output.append(f"  - `{d}`: {desc}")
            
    return "\n".join(output)

def generate_phase_6_erd(db_path=DB_PATH):
    """Generate Mermaid ERD."""
    erd = ["# Phase 6: Database Entity-Relationship Diagram\n```mermaid\nerDiagram\n"]
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        for table in tables:
            erd.append(f"    {table} {{")
            cursor.execute(f"PRAGMA table_info({table})")
            for col in cursor.fetchall():
                erd.append(f"        {col['type']} {col['name']}")
            erd.append("    }")
            
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            for fk in cursor.fetchall():
                erd.append(f"    {table} ||--o{{ {fk['table']} : \"{fk['from']} -> {fk['to']}\"")
        erd.append("```")
    return "\n".join(erd)

def generate_phase_7_sampling(db_path=DB_PATH):
    """Sample DB rows."""
    output = ["# Phase 7: Database Row Sampling\n"]
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        for table in tables:
            output.append(f"## {table}")
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            count = cursor.fetchone()['cnt']
            
            if count == 0:
                output.append("Table is empty.\n")
                continue
            
            # Fetch samples
            cursor.execute(f"SELECT * FROM {table} ORDER BY rowid ASC LIMIT 3")
            rows = cursor.fetchall()
            if count > 3:
                cursor.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 3")
                rows.extend(cursor.fetchall()[::-1])
            
            # Markdown table
            cols = list(rows[0].keys())
            output.append("| " + " | ".join(cols) + " |")
            output.append("| " + " | ".join(["---"] * len(cols)) + " |")
            
            for row in rows:
                sanitized_row = []
                for c in cols:
                    val = str(row[c]) if row[c] is not None else ""
                    # Escape pipes and newlines so markdown tables don't break
                    val = val.replace("|", "&#124;").replace("\n", "<br>").replace("\r", "")
                    sanitized_row.append(val)
                output.append("| " + " | ".join(sanitized_row) + " |")
            output.append("")
    return "\n".join(output)

def generate_phase_8_prompts(defaults_dir='DEFAULTS'):
    """Generate Phase 8: Default Prompt Files."""
    output = ["# Phase 8: Default Prompt Files\n"]
    if not os.path.exists(defaults_dir):
        return "\n".join(output)
        
    for filename in sorted(os.listdir(defaults_dir)):
        if filename.endswith('.tmpl'):
            filepath = os.path.join(defaults_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            output.append(f"### {filename}\n")
            output.append(f"```text\n{content}\n```\n")
    return "\n".join(output)

def get_current_version_and_date():
    """Read latest version/date from CHANGELOG.md."""
    with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'## \[(v[\d\.]+)\] - ([\d\-]+)', content)
    if match:
        return match.group(1), match.group(2)
    return "v0.0.0", datetime.now().strftime('%Y-%m-%d')

def build_ast_context(root_dir='.'):
    """Build a comprehensive AST map of the codebase for the LLM."""
    files = get_all_files(root_dir)
    ast_map = {}
    for filepath in files:
        if filepath.endswith('.py'):
            rel_path = os.path.relpath(filepath, root_dir)
            ast_map[rel_path] = parse_python_file(filepath)
    return json.dumps(ast_map, indent=2)

def call_gemini_architect(ast_context, db_erd, phase):
    """Call Gemini to generate architectural diagrams based on exact context."""
    from google import genai
    api_key = os.getenv("NEXUS_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "> [API KEY NOT FOUND - MANUAL ARCHITECTURE REQUIRED]"
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an expert Software Architect. Analyze the following system architecture.
    
    AST Codebase Map (JSON):
    {ast_context}
    
    Database Schema (Mermaid ERD):
    {db_erd}
    """
    
    if phase == "3":
        prompt += """
        Task: Generate a highly detailed Phase 3 C4 Architecture Diagram (C4Container).
        Instructions:
        - Use the provided AST context to identify specific sub-components (e.g., FastAPI routers, Sync Engine, LLM Engine, Auth module).
        - Map the precise communication links between these specific modules based on the AST, not just generic 'Backend' to 'Database' links.
        - Output ONLY valid Mermaid.js code using C4Container syntax. Do not output conversational text or markdown wrappers.
        """
    elif phase == "9":
        prompt += """
        Task: Generate Phase 9 Pipeline Flow Audits.
        Instructions:
        You must analyze the AST and generate sequence diagrams and vulnerability matrices for ALL FIVE of the following pipelines:
        1. Gmail Ingestion Pipeline
        2. Drive Ingestion Pipeline
        3. Contacts/People API Pipeline
        4. Batch Gmail Ingest Pipeline
        5. Legacy Label Ingest Pipeline
        
        For EACH pipeline, provide:
        - A Mermaid `sequenceDiagram` mapping the exact function calls found in the AST. Wrap this in standard ```mermaid blocks.
        - A 'Vulnerability & Assumption Matrix' Markdown table below the diagram detailing where it might break or what it assumes (e.g., timeouts, JSON enforcement).
        Output standard Markdown text containing these headers, diagrams, and tables.
        """
        
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        text = response.text.strip()
        
        # Strip code blocks ONLY for phase 3 (which needs pure mermaid code)
        if phase == "3":
            text = re.sub(r"^```mermaid\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^```[a-z]*\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"```$", "", text)
            return text.strip()
        
        # Phase 9 remains full Markdown
        return text
    except Exception as e:
        return f"> [AI GENERATION FAILED: {e}]"

def compile_master_audit():
    """Assemble all phases and write to audit trace file."""
    version, date = get_current_version_and_date()
    
    print("Generating AST Context...")
    ast_context = build_ast_context()
    
    print("Generating Phase 6 (ERD)...")
    erd_content = generate_phase_6_erd()
    
    print("Generating Phase 3 (C4 Diagram)...")
    phase_3_content = call_gemini_architect(ast_context, erd_content, "3")
    
    print("Generating Phase 9 (Pipelines)...")
    phase_9_content = call_gemini_architect(ast_context, erd_content, "9")
    
    print("Assembling final document...")
    phases = {
        "1": generate_phase_1(),
        "2": "## Phase 2: Hook Map\n> [PENDING MANUAL AI ARCHITECT GENERATION]\n\n",
        "3": f"## Phase 3: C4 Architecture Diagram\n\n```mermaid\n{phase_3_content}\n```\n\n",
        "4": "## Phase 4: Database Verification\n> [PENDING MANUAL AI ARCHITECT GENERATION]\n\n",
        "5": "## Phase 5: Orphan Report\n> [PENDING MANUAL AI ARCHITECT GENERATION]\n\n",
        "6": erd_content,
        "7": generate_phase_7_sampling(),
        "8": generate_phase_8_prompts(),
        "9": f"## Phase 9: Pipeline Flow Audits (Front-to-Back)\n\n{phase_9_content}\n\n"
    }
    
    master_content = [f"# Nexus System Audit Trace - {version} ({date})\n"]
    for i in range(1, 10):
        master_content.append(phases[str(i)])
        
    filename = f"AUDITS/{version}_{date}_audit_trace.md"
    os.makedirs("AUDITS", exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(master_content))
    print(f"Audit trace written to {filename}")

if __name__ == "__main__":
    ensure_db_initialized()
    compile_master_audit()
