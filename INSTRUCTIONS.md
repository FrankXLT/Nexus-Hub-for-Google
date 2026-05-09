$instructionsContent = @"
# Nexus for Google - Installation Masterclass

Welcome to Nexus for Google! This guide will walk you through building your personal, privacy-first, automated AI knowledge graph from scratch. By following the interactive scripts below, you will provision a Google Cloud server, deploy your backend, and link it securely to your Google Account.

---

## Phase 1: Provisioning the Environment

To begin, open your terminal and run the provisioning script. This script will configure your Google Cloud project, enable the necessary APIs, and build your backend server.

```powershell
PS C:\Users\developer\Github\Nexus-for-Google> .\scripts\provision.ps1
====================================================
    Welcome to the Nexus for Google Provisioning Wizard
====================================================
This script will automatically configure your Google Cloud project,
enable the necessary APIs, and build your backend server.

Prerequisite: Google Cloud CLI
Checking authentication status...
Authenticated as: developer@example.com

Prerequisite: Google Cloud Project & Billing
1. Go to https://console.cloud.google.com/
2. Create a new project (e.g., 'Nexus').
3. Go to the Billing menu and link a credit card.
Press [Enter] when your project is created and billing is enabled...:

Fetching your Google Cloud Projects...
[0] nexus-project-abc123    Nexus
Select Project number: 0
Targeting Project: nexus-project-abc123
Updated property [core/project].

Do you want to (1) Create a NEW Nexus Environment or (2) Configure an EXISTING one?
(1/2): 1
Enter the Environment Label (e.g., dev, staging, prod): dev
Using Project: nexus-project-abc123
Using Zone:    us-central1-f
Instance Name: nexus-vm-dev

Press [Enter] to begin the provisioning process...:

[1/5] Enabling Google Workspace & AI APIs...
Please go to Google Cloud Console and enable the Drive and Gmail APIs.
Press [Enter] when complete...:
```

### 🛑 Browser Action: Enable APIs
Before continuing, ensure that you have enabled the required APIs (Gmail, Drive, Document AI, People, Tasks, and Compute Engine) in the Google Cloud Console. Once done, hit \`Enter\` in your terminal.

```powershell
Operation "operations/acat.p2-[REDACTED]" finished successfully.
APIs successfully enabled!

[2/5] Configuring Network Security...
Creating firewall...-Created [https://www.googleapis.com/compute/v1/projects/nexus-project-abc123/global/firewalls/nexus-allow-8000].
Creating firewall...done.
NAME              NETWORK  DIRECTION  PRIORITY  ALLOW     DENY  DISABLED
nexus-allow-8000  default  INGRESS    1000      tcp:8000        False
Firewall rule created!

[3/5] Manual Step: OAuth Configuration
Instructions:
1. Go to: https://console.cloud.google.com/apis/credentials/consent?project=nexus-project-abc123
2. Select 'Internal' or 'External' and click Create.
3. Fill in the required app names and emails.
4. Skip adding scopes here, just save and continue.
Press [Enter] when you have configured the Consent Screen...:
```

### 🛑 Browser Action: OAuth Consent Screen
Google needs to know you trust this application. Follow the URL provided in your terminal to create the Consent Screen. If you select **External**, you **MUST** add your own email address to the "Test users" list, or you will be locked out later.

```powershell
[4/5] Manual Step: Generating Credentials
Instructions:
1. Go to: https://console.cloud.google.com/apis/credentials?project=nexus-project-abc123
2. Click 'CREATE CREDENTIALS' > 'OAuth client ID'.
3. Select 'Desktop app' for the Application type.
4. Click Create, then DOWNLOAD the JSON file.
5. Rename the downloaded file EXACTLY to: credentials.json

Press [Enter] when you have downloaded 'credentials.json' to your local machine...:
```

### 🛑 Browser Action: Generate Credentials
This JSON file acts as the VIP pass for your headless server. Download it, rename it exactly to \`credentials.json\`, and note the folder where you saved it. Hit \`Enter\` in the terminal once it is secured on your hard drive.

```powershell
[5/5] Provisioning the Virtual Machine (VM)...
Created [https://www.googleapis.com/compute/v1/projects/nexus-project-abc123/zones/us-central1-f/instances/nexus-vm-dev].
NAME          ZONE           MACHINE_TYPE  PREEMPTIBLE  INTERNAL_IP  EXTERNAL_IP      STATUS
nexus-vm-dev  us-central1-f  e2-micro                   10.128.0.22  [YOUR_VM_IP]  RUNNING
Waiting 30 seconds for the VM's SSH daemon to initialize...

WARNING - POTENTIAL SECURITY BREACH!
The host key does not match the one Plink has cached for this server...
Update cached key? (y/n, Return cancels connection, i for more info) y

[6/6] Uploading Credentials...
Please enter the full local path to your downloaded credentials.json file: D:\Users\developer\Downloads\credentials.json
credentials.json          | 0 kB |   0.4 kB/s | ETA: 00:00:00 | 100%

Apps Script Initialization
Do you have an EXISTING Apps Script project to link?
(y/N): n
Commanding Google to create a new Apps Script Web App: '[DEV] Nexus for Google - 20260509_124619'...
Created new script: https://script.google.com/d/[REDACTED_SCRIPT_ID]/edit
└─ frontend\appsscript.json
Cloned one file..
Linking Apps Script to Google Cloud Project for Cloud Logging...
Apps Script linked to GCP Project for Cloud Logging.
Success! Local clasp is now securely linked to your Google account and restricted to the frontend/ directory.

====================================================
             Provisioning Complete!
====================================================
Your server is ready.
```

---

## Phase 2: Deploying the Application

Now that the infrastructure exists, we will push our frontend code to Google Apps Script and our Python backend to the Google Cloud VM.

```powershell
PS C:\Users\developer\Github\Nexus-for-Google> .\scripts\deploy.ps1
====================================================
       Nexus for Google One-Click Deployment Wizard
====================================================
Deploying to nexus-vm-dev.
Press Enter to confirm, or type 'list' to choose a different VM: 
Fetching git branches...
[0] development
Select branch number: 0
Already on 'development'
Your branch is up to date with 'origin/development'.
Backup remote SQLite database? (Y/n): n

[1/2] Syncing Serverless Frontend (Google Apps Script)...
Pushed 7 files at 12:47:19 PM.
└─ frontend\appsscript.json
└─ frontend\Code.gs
└─ frontend\CSS_Styles.html
└─ frontend\debug.gs
└─ frontend\Index.html
└─ frontend\JS_Actions.html
└─ frontend\JS_State.html
--> Apps Script UI synced successfully!
URL: https://script.google.com/macros/s/[REDACTED_DEPLOY_ID]/exec

[2/2] Deploying Backend to Google Cloud VM...

*** ACTION REQUIRED: shared/.env FILE MISSING ***
NEXUS_HMAC_SECRET (type a highly unique, secure passphrase): [YOUR_SUPER_SECRET_PASSPHRASE]
NEXUS_API_KEY (Your Gemini API Key): [YOUR_GEMINI_API_KEY]
shared/.env file generated successfully.
```

### 🛑 Action Required: Environment Variables
The first time you deploy, you will be prompted to create your \`.env\` file. 
* **NEXUS_HMAC_SECRET:** Create a long, secure passphrase. This acts as the password between your Apps Script frontend and your Linux backend.
* **NEXUS_API_KEY:** Paste your Gemini API key here.

```powershell
[VM] 1. Preparing directories...
[VM] 2. Cloning code into new release directory...
Cloning into '/home/developer/nexus/releases/20260509_164825'...
[VM] 3. Activating Python Virtual Environment...
[VM] 4. Installing dependencies via pip...
[VM] 5. Setting up Symlinks...
[VM] 6. Running SQLite3 database migrations...
Database initialization complete: nexus.db with STRICT tables and WAL mode enabled.
[VM] 7. Updating main symlink...
[VM] 7.5. Patching systemd absolute paths...
[VM] 8. Restarting the FastAPI systemd daemon...
Created symlink /etc/systemd/system/multi-user.target.wants/nexus.service -> /etc/systemd/system/nexus.service.
[VM] Deployment sequence completed securely.

====================================================
                 ACTION REQUIRED
====================================================
NEXUS_HMAC_SECRET: [YOUR_SUPER_SECRET_PASSPHRASE]
NEXUS_VM_URL:      http://[YOUR_VM_IP]:8000

Please copy the variables above.
In a moment, your browser will open the Apps Script Editor.
You MUST immediately go to: Project Settings (Gear Icon) -> Script Properties -> Add Script Property. Add NEXUS_HMAC_SECRET and NEXUS_VM_URL.
Press Enter to open the Editor...:
```

### 🛑 Browser Action: Apps Script Properties
Your Apps Script needs to know where your backend lives and what the password is. The script will automatically open the Google Apps Script editor. Go to **Project Settings (the gear icon)** > **Script Properties** and add the two variables displayed in your terminal.

---

## Phase 3: Securely Authenticating Your Server

Finally, we must authorize the newly deployed backend to read your data. Run the \`auth_tunnel\` script to open a secure bridge to your VM.

```powershell
PS C:\Users\developer\Github\Nexus-for-Google> .\scripts\auth_tunnel.ps1
====================================================
           Nexus Auth Tunnel Script
====================================================
Checking for backend code on VM...

An SSH tunnel is opening, please wait...
When the link appears, please use ctrl+click to open your browser and authorize.
Testing Google Workspace Authentication Bridge...
Initiating new OAuth flow...
NOTE: Because this VM is headless, you must set up an SSH tunnel to port 8080.
Example: ssh -L 8080:localhost:8080 user@your-vm-ip
Then complete the authentication flow in your local browser.

Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=[REDACTED_CLIENT_ID]...
```

### 🛑 Browser Action: Final Authorization
\`Ctrl+Click\` the URL provided in the terminal. You will be routed to a Google Sign-In page. Select your account, acknowledge the warning (since you built the app, it is safe), and grant the required permissions. 

Once you see the "Authentication successful!" screen in your browser, check your terminal for the final confirmation.

```powershell
Authentication successful! Token saved to 'token.json'.
Success!
Credentials are valid and ready to use.
PS C:\Users\developer\Github\Nexus-for-Google>
```

**Congratulations! Your Nexus for Google Walled Garden is successfully deployed, secured, and authenticated.**
"@

Set-Content -Path "INSTRUCTIONS.md" -Value $instructionsContent -Encoding UTF8
Write-Host "INSTRUCTIONS.md has been generated successfully!" -ForegroundColor Green