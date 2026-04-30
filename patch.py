import re

with open('CSS_Styles.html', 'r', encoding='utf-8') as f:
    css = f.read()

# Replace :root
new_root = """  :root {
    --bg-dark: #121212;
    --bg-panel: #1E1E1E;
    --text-main: #E0E0E0;
    --text-muted: #9E9E9E;
    --accent-blue: #4A90E2; 
    --accent-red: #E24A4A;  
    --accent-alert: #F5A623;
    --success: #27AE60;

    --primary-color: var(--accent-blue);
    --primary-hover: #357abd;
    --surface-color: var(--bg-panel);
    --background-color: var(--bg-dark);
    --border-color: #333;
    --text-primary: var(--text-main);
    --text-secondary: var(--text-muted);
    --success-color: var(--success);
    --warning-color: var(--accent-alert);
    --error-color: var(--accent-red);
    
    --sidebar-width: 280px;
    --header-height: 70px;
    
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }"""
css = re.sub(r':root\s*\{[^}]+\}', new_root, css)

# We need to add the new blueprint styles from ROADMAP
blueprint_styles = """
  /* UPGRADED: Top Bar & Search Area */
  .top-bar {
      background-color: var(--bg-panel);
      border-bottom: 1px solid #333;
      display: flex;
      flex-direction: column;
      padding: 15px 30px;
      gap: 12px;
  }

  .search-row {
      display: flex;
      align-items: center;
      gap: 20px;
      width: 100%;
  }

  /* Omnibox Wrapper with embedded icons */
  .omnibox-wrapper {
      flex-grow: 1;
      max-width: 900px;
      display: flex;
      align-items: center;
      background-color: var(--bg-dark);
      border: 1px solid #444;
      border-radius: 24px;
      padding: 4px 16px;
      transition: border-color 0.2s;
  }

  .omnibox-wrapper:focus-within {
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
  }

  .search-icon { color: var(--text-muted); margin-right: 8px; }

  .omnibox {
      flex-grow: 1;
      background: transparent;
      border: none;
      color: white;
      font-size: 15px;
      padding: 10px 0;
      outline: none;
  }

  .omnibox-actions {
      display: flex;
      gap: 8px;
      margin-left: 10px;
  }

  .icon-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 6px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: 0.2s;
  }

  .icon-btn:hover { background-color: #333; color: white; }
  .icon-btn.save:hover { color: var(--success); }

  /* Interactive Search Chips */
  .chips-row {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 4px;
      margin-left: 42px; /* Aligns with input text */
  }

  .chip {
      background-color: #2A2A2A;
      border: 1px solid #444;
      color: var(--text-main);
      padding: 5px 12px;
      border-radius: 16px;
      font-size: 12px;
      cursor: pointer;
      white-space: nowrap;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: 0.2s;
  }

  .chip:hover { background-color: #383838; border-color: #555; }
  .chip.active { background-color: rgba(74, 144, 226, 0.15); border-color: var(--accent-blue); color: var(--accent-blue); }

  /* View Controls */
  .view-controls { display: flex; background: #121212; border-radius: 8px; padding: 4px; border: 1px solid #333; }
  .view-btn { background: transparent; color: var(--text-muted); border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; }
  .view-btn.active { background: #333; color: white; }

  /* Blueprint Sidebar Overrides */
  .sidebar { width: 280px; background-color: var(--bg-panel); display: flex; flex-direction: column; border-right: 1px solid #333; transition: width 0.3s ease; overflow-x: hidden; }
  .sidebar.collapsed { width: 70px; }
  .brand-header { height: 70px; display: flex; align-items: center; padding: 0 20px; border-bottom: 1px solid #333; gap: 15px; white-space: nowrap; }
  .menu-toggle { background: none; border: none; color: white; cursor: pointer; padding: 5px; display: flex; align-items: center; justify-content: center; }
  .menu-toggle:hover { color: var(--accent-blue); }
  .brand-text { font-size: 20px; font-weight: bold; color: white; transition: opacity 0.2s; }
  .sidebar.collapsed .brand-text, .sidebar.collapsed .nav-text, .sidebar.collapsed .system-toggles { opacity: 0; pointer-events: none; display: none; }
  
  .nav-item { display: flex; align-items: center; padding: 12px; margin-bottom: 8px; border-radius: 6px; cursor: pointer; transition: background 0.2s; color: var(--text-main); white-space: nowrap; }
  .nav-icon { min-width: 24px; display: flex; justify-content: center; margin-right: 15px; }
  .nav-item.active { background-color: #333; color: white; border-radius: 6px; margin-right: 0;}
  .nav-item:hover:not(.active) { background-color: #2A2A2A; }

  /* Old specific dark mode fixes */
  .data-grid th { background-color: var(--bg-panel); color: var(--text-muted); }
  .data-grid tbody tr:hover { background-color: #2A2A2A; }
  .data-grid tbody tr.selected { background-color: #333; }
  .detail-group { background: var(--bg-panel); border: 1px solid #333; }
  .detail-row { border-bottom: 1px solid #333; }
  .json-chip { background-color: #333; border-color: #444; color: var(--text-main); }
  
  /* Inputs and Textareas in dark mode */
  input[type="text"], select, textarea {
    background-color: var(--bg-dark);
    color: var(--text-main);
    border: 1px solid #444;
  }
  
  /* For elements with direct hardcoded background colors */
  .tab-content [style*="background: #fff"], 
  .tab-content [style*="background-color: #fff"], 
  .tab-content [style*="background-color: #fefefe"] {
      background-color: var(--bg-panel) !important;
      border-color: #444 !important;
  }
  
  /* Modals */
  .modal > div {
      background-color: var(--bg-panel) !important;
      border-color: #444 !important;
  }

  /* Table Container */
  .table-container { background-color: var(--bg-dark); }
"""

css = css.replace('</style>', blueprint_styles + '\n</style>')

with open('CSS_Styles.html', 'w', encoding='utf-8') as f:
    f.write(css)

# Update Index.html
with open('Index.html', 'r', encoding='utf-8') as f:
    index = f.read()

sidebar_new = """      <!-- Sidebar -->
      <nav class="sidebar" id="sidebar">
        <div class="brand-header">
            <button class="menu-toggle" onclick="toggleSidebar()">
                <i class="material-icons">menu</i>
            </button>
            <span class="brand-text">Nexus Hub</span>
        </div>
        
        <div class="nav-menu">
            <div class="nav-item active" onclick="appState.switchTab('grid', event)">
                <div class="nav-icon"><i class="material-icons">grid_view</i></div>
                <span class="nav-text">Workspace</span>
            </div>
            <div class="nav-item" onclick="appState.switchTab('correspondent-review', event)">
                <div class="nav-icon"><i class="material-icons">fact_check</i></div>
                <span class="nav-text">Zero-Trust Review</span>
            </div>
            <div class="nav-item" onclick="appState.switchTab('entity-management', event)">
                <div class="nav-icon"><i class="material-icons">account_tree</i></div>
                <span class="nav-text">Entity Management</span>
            </div>
            <div class="nav-item" onclick="appState.switchTab('prompt-sandbox', event)">
                <div class="nav-icon"><i class="material-icons">science</i></div>
                <span class="nav-text">Prompt Sandbox</span>
            </div>
            <div class="nav-item" onclick="appState.switchTab('pipeline-orchestrator', event)">
                <div class="nav-icon"><i class="material-icons">tune</i></div>
                <span class="nav-text">Pipeline Orchestrator</span>
            </div>
            <div class="nav-item" onclick="appState.switchTab('inbox-cleanup', event)">
                <div class="nav-icon"><i class="material-icons">delete_sweep</i></div>
                <span class="nav-text">Inbox Cleanup</span>
            </div>
            <div class="nav-item" onclick="appState.switchTab('audit', event)">
                <div class="nav-icon"><i class="material-icons">history</i></div>
                <span class="nav-text">Audit Timeline</span>
            </div>
            <div class="nav-item" onclick="appState.switchTab('ai-assistant', event)">
                <div class="nav-icon"><i class="material-icons">smart_toy</i></div>
                <span class="nav-text">AI Assistant</span>
            </div>
        </div>

        <div class="system-toggles">
            <div style="font-size: 10px; text-transform: uppercase; color: #666; margin-bottom: 15px; font-weight: bold; letter-spacing: 1px;">Diagnostics</div>
            <div class="nav-item" onclick="appActions.triggerDiagnostics()" style="margin: 0; padding: 12px 20px; background: transparent;">
                <div class="nav-icon"><i class="material-icons">health_and_safety</i></div>
                <span class="nav-text">Run Diagnostics</span>
            </div>
        </div>
      </nav>"""

# Extract the old sidebar and replace
sidebar_regex = re.compile(r'<!-- Sidebar -->.*?<!-- Main Content Area -->', re.DOTALL)
index = sidebar_regex.sub(sidebar_new + '\n\n      <!-- Main Content Area -->', index)

# Add Top Bar to Main Content Area
top_bar_html = """        <!-- Global Top Bar -->
        <div class="top-bar">
            <div class="search-row">
                <div class="omnibox-wrapper">
                    <i class="material-icons search-icon">search</i>
                    <input type="text" id="ast-input" class="omnibox" placeholder="Search AST... (e.g., 'Purpose:Receipt AND Date:>2026-03')">
                    
                    <div class="omnibox-actions">
                        <button class="icon-btn save" title="Save Query">
                            <i class="material-icons">bookmark_border</i>
                        </button>
                        <button class="icon-btn" title="Advanced Search">
                            <i class="material-icons">tune</i>
                        </button>
                    </div>
                </div>
                
                <!-- System Health Badge -->
                <div id="system-health-badge" class="health-badge" style="background-color: var(--success); color: white; padding: 6px 12px; border-radius: 16px; font-size: 12px; display: flex; align-items: center; gap: 6px; cursor: help;" title="System Health: Checking...">
                    <i class="material-icons" style="font-size: 16px;">health_and_safety</i>
                    <span id="health-status-text">Health: OK</span>
                </div>

                <!-- Quota Governor Metric Card (Adapted for Header) -->
                <div style="width: 250px; padding: 0 16px;" title="Historical batches are automatically throttled at 70% capacity to reserve bandwidth for real-time incoming Gmail webhooks.">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <strong style="font-size: 0.75rem;">Quota Governor</strong>
                    <span id="quota-status" style="font-size: 0.75rem; color: var(--accent-blue); font-weight: bold;">Loading...</span>
                  </div>
                  <div style="background: #333; border-radius: 4px; height: 8px; width: 100%; overflow: hidden;">
                    <div id="quota-bar" style="background: var(--accent-blue); height: 100%; width: 0%;"></div>
                  </div>
                  <div style="text-align: right; font-size: 0.65rem; color: var(--text-muted); margin-top: 2px;">
                    <span id="quota-used">0</span> / <span id="quota-limit">10000</span> Calls
                  </div>
                </div>
            </div>

            <!-- Interactive Search Chips -->
            <div class="chips-row">
                <button class="chip" onclick="toggleChip(this, 'Action:Required')">
                    <i class="material-icons" style="font-size: 14px;">error_outline</i> Action Needed
                </button>
                <button class="chip" onclick="toggleChip(this, 'Has:Attachment')">
                    <i class="material-icons" style="font-size: 14px;">attachment</i> Has Attachment
                </button>
                <button class="chip" onclick="toggleChip(this, 'Source:Drive')">
                    <i class="material-icons" style="font-size: 14px;">folder</i> Drive Files
                </button>
            </div>
        </div>"""

index = index.replace('<main class="main-content">', '<main class="main-content">\n' + top_bar_html)

# Remove old quota governor from Data Grid pane (it spans multiple lines)
old_quota = r'<!-- Quota Governor Metric Card -->\s*<div style="padding: 0 16px; margin-bottom: 10px;">.*?</div>\s*</div>\s*</div>'
index = re.sub(old_quota, '', index, flags=re.DOTALL)

with open('Index.html', 'w', encoding='utf-8') as f:
    f.write(index)


# Now update JS_Actions.html
with open('JS_Actions.html', 'r', encoding='utf-8') as f:
    js_actions = f.read()

health_ping_js = """  init: function() {
    this.refreshData(); // Fetch initial data
    this.loadPipelineSettings(); // Fetch UI configurations
    this.loadQuotaGovernor();
    this.startHealthPing();
  },

  startHealthPing: function() {
    this.pingHealth();
    setInterval(() => this.pingHealth(), 60000);
  },

  pingHealth: function() {
    google.script.run
      .withSuccessHandler((result) => {
        const badge = document.getElementById('system-health-badge');
        const text = document.getElementById('health-status-text');
        if (result && result.status === 'success') {
           badge.style.backgroundColor = 'var(--success)';
           text.textContent = 'Health: OK';
           badge.title = 'System is operating normally.';
        } else {
           badge.style.backgroundColor = 'var(--accent-red)';
           text.textContent = 'Health: Error';
           badge.title = 'Failed to reach API';
        }
      })
      .withFailureHandler((error) => {
        const badge = document.getElementById('system-health-badge');
        const text = document.getElementById('health-status-text');
        badge.style.backgroundColor = 'var(--accent-red)';
        text.textContent = 'Health: Error';
        badge.title = error.message;
      })
      .pingHealthAPI();
  },"""

js_actions = js_actions.replace("""  init: function() {
    this.refreshData(); // Fetch initial data
    this.loadPipelineSettings(); // Fetch UI configurations
    this.loadQuotaGovernor();
  },""", health_ping_js)

# Add sidebar toggle function to end of js_actions object
js_actions = js_actions.replace('};\n</script>', """  toggleSidebar: function() { document.getElementById('sidebar').classList.toggle('collapsed'); },
  toggleChip: function(button, astString) {
      button.classList.toggle('active');
      const input = document.getElementById('ast-input');
      let currentVal = input.value.trim();

      if (button.classList.contains('active')) {
          if (!currentVal.includes(astString)) {
              input.value = currentVal ? `${currentVal} AND ${astString}` : astString;
          }
      } else {
          let regex = new RegExp(`( AND )?${astString}( AND )?`);
          input.value = currentVal.replace(regex, function(match, p1, p2) {
              return (p1 && p2) ? ' AND ' : '';
          }).trim();
      }
      input.focus();
  }
};

window.toggleSidebar = function() { appActions.toggleSidebar(); };
window.toggleChip = function(btn, str) { appActions.toggleChip(btn, str); };

</script>""")

with open('JS_Actions.html', 'w', encoding='utf-8') as f:
    f.write(js_actions)
