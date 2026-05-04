import re

with open('nexus_exhaustive_matrix.md', 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

ui_elements = []
js_elements = []
gs_elements = []
api_elements = []
cross_html_js = []
cross_js_gs = []
cross_gs_api = []

phase = None
for line in lines:
    if line.startswith('### Index.html Interactive Elements'):
        phase = 'UI'
    elif line.startswith('### JS_Actions.html & JS_State.html Functions'):
        phase = 'JS'
    elif line.startswith('### Code.gs Functions'):
        phase = 'GS'
    elif line.startswith('### main.py FastAPI Endpoints'):
        phase = 'API'
    elif line.startswith('### HTML to JS'):
        phase = 'Map_HTML_JS'
    elif line.startswith('### JS to Code.gs'):
        phase = 'Map_JS_GS'
    elif line.startswith('### Code.gs to FastAPI'):
        phase = 'Map_GS_API'
    elif line.startswith('## Phase 3'):
        phase = 'End'
        
    if line.startswith('- '):
        val = line[2:]
        if phase == 'UI':
            ui_elements.append(val)
        elif phase == 'JS':
            js_elements.append(val.strip('` '))
        elif phase == 'GS':
            gs_elements.append(val.strip('` '))
        elif phase == 'API':
            api_elements.append(val.strip('` '))
        elif phase == 'Map_HTML_JS':
            cross_html_js.append(val)
        elif phase == 'Map_JS_GS':
            cross_js_gs.append(val)
        elif phase == 'Map_GS_API':
            cross_gs_api.append(val)

dead_js = ['setHistory()', 'toggleSelectAll()']
dead_gs = ['addRetentionRule()', 'deleteRetentionRule()', 'getRetentionRules()', 'triggerRetentionSweep()']
dead_api = ['GET /api/dashboard/mission-control', 'GET /api/analytics/heatmap', 'GET /api/analytics/threads', 'GET /api/analytics/roi-dashboard', 'POST /api/update', 'GET /api/prompts', 'POST /api/prompts', 'PUT /api/entities/correspondents/{id}', 'PUT /api/entities/purposes/{id}']

def sanitize_ui(text):
    text = text.replace('"', "'").replace('<', '').replace('>', '')
    if len(text) > 40:
        return text[:37] + "..."
    return text

with open('nexus_exhaustive_matrix_diagram.md', 'w', encoding='utf-8') as out:
    out.write("# Nexus Exhaustive Matrix Diagram\n\n")
    out.write("```mermaid\n")
    out.write("graph TD\n")
    out.write("    classDef dead fill:#ffcccc,stroke:#cc0000,stroke-width:4px,color:#000\n\n")

    out.write("    subgraph UI [HTML UI Elements]\n")
    for i, el in enumerate(ui_elements):
        out.write(f"        UI{i}[\"{sanitize_ui(el)}\"]\n")
    out.write("    end\n\n")

    out.write("    subgraph JS [JS Actions & State Functions]\n")
    for i, el in enumerate(js_elements):
        cls = ':::dead' if el in dead_js else ''
        out.write(f"        JS{i}[\"{el}\"]{cls}\n")
    out.write("    end\n\n")

    out.write("    subgraph GS [Code.gs Apps Script Functions]\n")
    for i, el in enumerate(gs_elements):
        cls = ':::dead' if el in dead_gs else ''
        out.write(f"        GS{i}[\"{el}\"]{cls}\n")
    out.write("    end\n\n")

    out.write("    subgraph API [FastAPI Endpoints]\n")
    for i, el in enumerate(api_elements):
        cls = ':::dead' if el in dead_api else ''
        out.write(f"        API{i}[\"{el}\"]{cls}\n")
    out.write("    end\n\n")

    out.write("    %% Mappings\n")
    for mapping in cross_html_js:
        if ' -> Calls: ' in mapping:
            html_part, js_part = mapping.split(' -> Calls: ')
            html_part = html_part.strip()
            js_part = js_part.strip().strip('`') + '()'
            
            # Find UI index
            ui_idx = None
            for i, el in enumerate(ui_elements):
                if el == html_part:
                    ui_idx = i
                    break
            
            # Find JS index
            js_idx = None
            for i, el in enumerate(js_elements):
                if el == js_part or el.startswith(js_part.replace('()', '')):
                    js_idx = i
                    break
                    
            if ui_idx is not None and js_idx is not None:
                out.write(f"    UI{ui_idx} --> JS{js_idx}\n")

    for mapping in cross_js_gs:
        # JS calls Apps Script: `bulkUpdateArtifacts()`
        if 'JS calls Apps Script: ' in mapping:
            gs_part = mapping.split('JS calls Apps Script: ')[1].strip().strip('`')
            # JS mapping is hard to determine from this string (it doesn't say which JS function). 
            # I'll just map from the JS function of the same name if it exists, else skip.
            js_name = gs_part.replace('()', '')
            js_idx = None
            gs_idx = None
            
            for i, el in enumerate(gs_elements):
                if el == gs_part:
                    gs_idx = i
                    break
            for i, el in enumerate(js_elements):
                if el.startswith(js_name):
                    js_idx = i
                    break
            
            # handle special cases
            if js_name == 'bulkUpdateArtifacts':
                for i, el in enumerate(js_elements):
                    if el == 'submitManualReview()': js_idx = i
            
            if js_idx is not None and gs_idx is not None:
                out.write(f"    JS{js_idx} --> GS{gs_idx}\n")

    for mapping in cross_gs_api:
        # Code.gs calls FastAPI: `/api/artifacts/search`
        if 'Code.gs calls FastAPI: ' in mapping:
            api_part = mapping.split('Code.gs calls FastAPI: ')[1].strip().strip('`')
            
            api_idx = None
            for i, el in enumerate(api_elements):
                if api_part in el:
                    api_idx = i
                    break
            
            # Guess the GS function based on the path
            gs_idx = None
            path_mapping = {
                '/api/artifacts/search': 'searchArtifacts()',
                '/api/ask': 'runAskAI()',
                '/api/bulk-update': 'bulkUpdateArtifacts()',
                '/api/health': 'runSystemDiagnostics()',
                '/api/ingestion/queue-historical': 'queueHistoricalImport()',
                '/api/retention/rules': 'getRetentionRules()', # could be others
                '/api/retention/sweep': 'triggerRetentionSweep()',
                '/api/sandbox': 'runSandboxPrompt()',
                '/api/settings/pipeline': 'savePipelineSettings()', # or getPipelineSettings
                '/api/taxonomy/zero-shot-rule': 'submitZeroShotRule()',
                '/api/workflows/materialize': 'materializeSelectedItems()'
            }
            
            gs_name = path_mapping.get(api_part)
            if gs_name:
                for i, el in enumerate(gs_elements):
                    if el == gs_name:
                        gs_idx = i
                        break
            
            if gs_idx is not None and api_idx is not None:
                out.write(f"    GS{gs_idx} --> API{api_idx}\n")

    out.write("```\n")
