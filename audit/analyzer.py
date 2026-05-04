import re
import os

def analyze():
    with open('Index.html', 'r', encoding='utf-8') as f: index_html = f.read()
    with open('JS_Actions.html', 'r', encoding='utf-8') as f: js_actions = f.read()
    with open('JS_State.html', 'r', encoding='utf-8') as f: js_state = f.read()
    with open('Code.gs', 'r', encoding='utf-8') as f: code_gs = f.read()
    with open('main.py', 'r', encoding='utf-8') as f: main_py = f.read()

    # --- PHASE 1 ---
    interactive_elements = []
    for line in index_html.split('\n'):
        if re.search(r'\bon(click|change|submit)=', line):
            interactive_elements.append(line.strip())

    js_funcs = set(re.findall(r'\b([a-zA-Z0-9_]+)\s*:\s*function', js_actions + js_state))
    gs_funcs = set(re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', code_gs))
    api_endpoints = re.findall(r'@app\.(get|post|put|delete)\("([^"]+)"\)', main_py)

    # --- PHASE 2 ---
    html_to_js = []
    for el in interactive_elements:
        calls = re.findall(r'(?:appActions|appState|document)\.([a-zA-Z0-9_]+)|(toggleSidebar|toggleChip)', el)
        # flatten tuples
        extracted = [item for sublist in calls for item in sublist if item]
        html_to_js.append((el, extracted))

    # GS called by JS
    js_to_gs = set(re.findall(r'\.([a-zA-Z0-9_]+)\s*\(', js_actions + js_state))
    called_gs_funcs = gs_funcs.intersection(js_to_gs)

    # API called by GS
    called_apis = set(re.findall(r'sendToNexusVM\("([^"\?]+)', code_gs))

    # --- PHASE 3 ---
    broken_ui = []
    for el, calls in html_to_js:
        for c in calls:
            if c not in js_funcs and c not in ('getElementById', 'toggleSidebar', 'toggleChip'):
                broken_ui.append(f"`{c}` (called in `{el}`)")

    dead_js = []
    full_js = js_actions + js_state
    for f in js_funcs:
        if f in ('init'): continue
        # Count total word occurrences
        occurrences = len(re.findall(r'\b' + f + r'\b', index_html + full_js))
        if occurrences <= 1:
            dead_js.append(f)

    dead_gs = []
    for f in gs_funcs:
        if f in ('doGet', 'doPost', 'include'): continue
        if f not in called_gs_funcs:
            # check internal calls
            if len(re.findall(r'\b' + f + r'\s*\(', code_gs)) <= 1:
                dead_gs.append(f)

    dead_api = []
    for method, path in api_endpoints:
        base_path = path.split('{')[0].rstrip('/')
        matched = False
        for c_api in called_apis:
            c_api_base = c_api.split('{')[0].rstrip('/')
            if c_api_base == base_path or base_path in c_api_base or base_path.startswith(c_api_base):
                matched = True
                break
        if not matched:
            dead_api.append(f"{method.upper()} {path}")

    # Output MD
    with open('nexus_exhaustive_matrix.md', 'w', encoding='utf-8') as f:
        f.write("# Nexus Exhaustive Matrix\n\n")
        
        f.write("## Phase 1: The Total Census (Inventory)\n\n")
        f.write("### Index.html Interactive Elements\n")
        for el in interactive_elements: f.write(f"- `{el}`\n")
        
        f.write("\n### JS_Actions.html & JS_State.html Functions\n")
        for func in sorted(js_funcs): f.write(f"- `{func}()`\n")
        
        f.write("\n### Code.gs Functions\n")
        for func in sorted(gs_funcs): f.write(f"- `{func}()`\n")
        
        f.write("\n### main.py FastAPI Endpoints\n")
        for m, p in api_endpoints: f.write(f"- `{m.upper()} {p}`\n")

        f.write("\n## Phase 2: The Cross-Reference Mapping\n\n")
        f.write("### HTML to JS\n")
        for el, calls in html_to_js: 
            f.write(f"- `{el}` -> Calls: `{', '.join(calls) if calls else 'None'}`\n")
        
        f.write("\n### JS to Code.gs\n")
        for func in sorted(called_gs_funcs): f.write(f"- JS calls Apps Script: `{func}()`\n")
        
        f.write("\n### Code.gs to FastAPI\n")
        for api in sorted(called_apis): f.write(f"- Code.gs calls FastAPI: `{api}`\n")

        f.write("\n## Phase 3: The Comprehensive Orphan Report\n\n")
        f.write("### Broken UI Links\n")
        if broken_ui:
            for b in broken_ui: f.write(f"- **[BROKEN LINK]**: {b}\n")
        else:
            f.write("- None found\n")
            
        f.write("\n### Dead Frontend Code\n")
        if dead_js:
            for d in sorted(dead_js): f.write(f"- **[DEAD JS]**: `{d}()` is never called.\n")
        else:
            f.write("- None found\n")
            
        f.write("\n### Dead Middleware\n")
        if dead_gs:
            for d in sorted(dead_gs): f.write(f"- **[DEAD GS]**: `{d}()` is never called.\n")
        else:
            f.write("- None found\n")
            
        f.write("\n### Dead Backend Routes\n")
        if dead_api:
            for d in dead_api: f.write(f"- **[DEAD API]**: `{d}` is never called.\n")
        else:
            f.write("- None found\n")

if __name__ == '__main__':
    analyze()
    print('Done')
