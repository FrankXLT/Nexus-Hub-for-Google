# Nexus Hub for Google - User Manual & Setup Instructions

## Phase 0: Google Cloud Console Prerequisites

Before provisioning the VM, you must configure the Google Cloud Project and generate your credentials.

### 1. Enable Required APIs
Navigate to **APIs & Services > Library** in the GCP Console and enable the following:
* Gmail API
* Google Drive API
* Cloud Pub/Sub API
* Document AI API

![Enable APIs Screenshot](docs/img/gcp_enable_apis.png)

### 2. Configure OAuth Consent Screen
Because this is an internal tool, configure the OAuth screen for "Internal" use to bypass Google's app verification process.
1. Navigate to **APIs & Services > OAuth consent screen**.
2. Select **Internal** and click Create.
3. Under Scopes, manually add `https://www.googleapis.com/auth/gmail.modify` and `https://www.googleapis.com/auth/drive`.

![OAuth Scopes Screenshot](docs/img/gcp_oauth_scopes.png)

### 3. Generate Desktop App Credentials
The Python VM requires a headless OAuth flow. 
1. Navigate to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Select **Desktop app** as the Application type. Name it "Nexus Hub Headless VM".
4. Download the generated JSON file and rename it exactly to `credentials.json`. 

![Download Credentials Screenshot](docs/img/gcp_download_credentials.png)
*(Save this file; you will SCP or paste it into your VM in Phase 1).*

## Phase 1: Virtual Machine Provisioning & CI/CD

### 1. Provisioning the Google Cloud VM
To set up the persistent e2-micro VM environment on Google Cloud Platform, follow these steps:

1. Clone this repository into your target Ubuntu VM:
   ```bash
   git clone https://github.com/your-username/Nexus-Hub-for-Google.git
   cd Nexus-Hub-for-Google
   ```
2. Execute the setup script to install Docker, Docker Compose, Node.js, and `@google/clasp`.
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

### 2. Google Apps Script Authentication
The VM needs headless access to push code to your Google Apps Script environment.

1. On your **local machine** (where you have a browser), run:
   ```bash
   clasp login
   ```
2. Complete the OAuth flow in your browser.
3. Locate the `.clasprc.json` file generated in your local home directory (e.g., `C:\Users\YourUser\.clasprc.json` or `~/.clasprc.json`).
4. Copy the entire JSON contents of this file.
5. On your **Google Cloud VM**, create a new file in your user's home directory:
   ```bash
   nano ~/.clasprc.json
   ```
6. Paste the copied contents, save the file, and restrict its permissions:
   ```bash
   chmod 600 ~/.clasprc.json
   ```

### 3. Deploying Updates
Whenever you need to pull the latest changes from the `main` branch, run migrations, and redeploy both the VM services and the Apps Script frontend, use the update executor:

```bash
chmod +x update.sh
./update.sh
```

## Phase 2: Database Setup

### 1. Initializing the Database
The synchronization engine requires a strictly structured SQLite database (`nexus.db`) to index your Google Workspace taxonomy and custom AI-extracted data.

To initialize the database locally or on the VM:
```bash
python3 db_init.py
```
This will generate the `nexus.db` file in the root directory. Ensure this file remains excluded from version control (it is ignored by default in the `.gitignore`).

## Phase 3: Backend Webhook & Security Setup

### 1. Configure the `.env` File
The FastAPI backend requires an HMAC secret to cryptographically verify incoming webhooks from Google Apps Script. 

1. Create a `.env` file in the root directory of your project:
   ```bash
   nano .env
   ```
2. Generate a secure, random string and add it to the file:
   ```env
   NEXUS_HMAC_SECRET=your_super_secret_random_string_here
   ```
3. Save and close. Ensure this file is never committed to version control.

### 2. Running the FastAPI Server
To test the webhook receiver locally during development:
```bash
# Ensure dependencies are installed (e.g., via pip)
pip install fastapi uvicorn python-dotenv

# Run the server with hot-reloading
python3 main.py
```
The server will bind to port 8000 and is now ready to receive secure webhooks. In production, this will run inside a Docker container behind Nginx.

## Phase 4: Apps Script Frontend Deployment

### 1. Deploying the Code
After running `clasp push` (or executing `update.sh`), your Google Apps Script project will contain `Code.gs`.

1. Open your Google Apps Script project editor (via script.google.com).
2. Ensure you have published it as a Web App:
   - Click **Deploy** > **New deployment**.
   - Select type **Web app**.
   - Execute as: **Me**.
   - Who has access: **Only myself**.

### 2. Configuring the Cryptographic Bridge
To allow the Apps Script frontend to communicate securely with your Python VM, you must configure the shared HMAC secret.

1. In the Apps Script editor, open `Code.gs`.
2. Locate the `configureHMAC(secretString)` function.
3. Temporarily modify the function call at the bottom of the file (or run it via the Run button) by passing your EXACT secret from the VM's `.env` file:
   ```javascript
   function runOnce() {
     configureHMAC("your_super_secret_random_string_here");
   }
   ```
4. Select `runOnce` from the function dropdown and click **Run**.
5. **CRITICAL:** Once executed successfully, delete the `runOnce` function and the secret string from your editor entirely. Do not commit it to version control.

### 3. Set the VM URL
You will also need to inform Apps Script where your backend VM is located.
1. Go to **Project Settings** (gear icon) in the Apps Script editor.
2. Under **Script Properties**, click **Edit script properties**.
3. Add a new property named `NEXUS_VM_URL` and set its value to your VM's public HTTPS URL (e.g., `https://nexus.yourdomain.com`).
4. Save the script properties.

## Phase 5: Google Workspace API Authentication (Headless VM)

To allow your Python VM backend to synchronize with your Gmail and Google Drive, you need to authorize it via an OAuth 2.0 flow.

### 1. Download `credentials.json` from GCP
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project. Go to **APIs & Services > Credentials**.
3. Click **Create Credentials > OAuth client ID**.
4. Select **Desktop app** as the application type and create it.
5. Click the download icon to save the JSON file to your local machine.
6. Rename this file to `credentials.json` and upload/copy its contents to the root directory of your Nexus Hub project on the VM.

### 2. Generate `token.json` via SSH Tunnel
Because your VM is headless (has no web browser), you cannot complete the OAuth login flow directly on the server. You must create an SSH tunnel to forward the local port.

1. Open a terminal on your **local machine** and start an SSH tunnel to your VM mapping port 8080:
   ```bash
   ssh -L 8080:localhost:8080 your-user@your-vm-ip-address
   ```
2. Once connected via SSH, ensure you are in the Nexus Hub directory. Install dependencies and run the auth script:
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   python3 auth.py
   ```
3. The script will output a message stating the local server is running.
4. On your **local machine**, open a web browser and navigate to:
   ```
   http://localhost:8080
   ```
5. Follow the Google authentication prompts to grant access to Gmail and Drive.
6. Once successful, the browser will display a confirmation message, and `auth.py` on the VM will automatically generate and save `token.json`. Your VM is now authenticated!

## Phase 6: Running System Diagnostics

The system features an isolated diagnostic suite that checks database integrity, OAuth validity, and uploads a JSON report directly to Google Drive.

### 1. Triggering Diagnostics from the Frontend
You can trigger the diagnostic suite directly from the Google Apps Script frontend. 

1. Open your Google Apps Script project editor (`Code.gs`).
2. You can trigger the `runSystemDiagnostics` function programmatically or hook it up to an HTML button in your `Index.html` (e.g., `google.script.run.withSuccessHandler(console.log).runSystemDiagnostics()`).
3. If you run it from the backend editor as a test:
   ```javascript
   function testDiagnostics() {
     const result = runSystemDiagnostics();
     Logger.log(result);
   }
   ```
4. The VM will perform the read/write tests, check the tokens, and if successful, upload a detailed JSON file to a newly created `Nexus Diagnostics` folder in your Google Drive.

### 2. Triggering Diagnostics Locally on the VM
If you suspect the webhook bridge is broken, you can bypass the frontend and run the tests directly on the VM:

```bash
python3 diagnostics.py
```
This will print the JSON report directly to your terminal.

## Phase 7: Delta Synchronization Setup

The `sync_engine.py` script requires access to the Google Workspace APIs. Ensure that you have already generated the `token.json` using the Phase 5 instructions.

### 1. Enabling APIs in Google Cloud Console
To allow the sync engine to fetch changes, you must enable the respective APIs in your GCP project:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project.
3. Navigate to **APIs & Services > Library**.
4. Search for and enable the following APIs:
   - **Gmail API**
   - **Google Drive API**

### Configure the `.env` File (Updated for v1.1)
Update the environment file on your VM to include your API keys, telemetry webhooks, and Drive folder IDs:
1. Open the `.env` file:
   ```bash
   nano .env

NEXUS_HMAC_SECRET=your_super_secret_random_string_here
GEMINI_API_KEY=your_gemini_api_key_here

# Pushover API for Critical System Alerts (Phase 28)
NEXUS_WEBHOOK_URL=https://api.pushover.net/1/messages.json?user=YOUR_USER_KEY&token=YOUR_APP_TOKEN

# Google Drive Folder ID for taxonomy_seed.json ingest (Phase 25)
DRIVE_SEED_FOLDER_ID=your_google_drive_folder_id_here

### 2. Installing Sync Engine Dependencies
Dependencies are automatically installed via the `Dockerfile` when running `docker compose up -d`. There is no need for manual `pip install` commands.

### 3. Running the Sync Engine
You can trigger the synchronization engine manually to fetch delta changes:
```bash
python3 sync_engine.py
```
This script will read the last known token from the `nexus.db` `Sync_State` table, fetch only the modified files/emails since the last check, and update the token. In a production environment, this script should be scheduled via `cron` or a task runner.

## Phase 8: LLM Engine & Gemini Integration

The `llm_engine.py` module is responsible for analyzing the text of documents and emails using Google's Gemini models.

### 1. Generating a Gemini API Key
To use the `google-genai` SDK, you must generate an API key from Google AI Studio.
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Click **Get API key** and generate a new key for your project.

### 2. Configure the `.env` File
Update the environment file on your VM to include the new API key:
1. Open the `.env` file:
   ```bash
   nano .env
   ```
2. Add your Gemini API Key:
   ```env
   NEXUS_HMAC_SECRET=your_super_secret_random_string_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
3. Save and close.

### 3. Install the GenAI SDK
Dependencies like the Google GenAI SDK are automatically installed via the `Dockerfile`. Ensure your container is running the latest build:
```bash
docker compose up -d --build
```

## Phase 9: Frontend Web App Deployment

The zero-dependency Material Design UI is now complete. You must deploy it as a Web App to access the dashboard.

### 1. Push Code to Apps Script
First, ensure all new HTML files (`Index.html`, `CSS_Styles.html`, `JS_State.html`, `JS_Actions.html`) are pushed to your Google Apps Script project.
From your local machine or the VM:
```bash
clasp push
```

### 2. Publish as a Web App
1. Open your Apps Script editor (`script.google.com`).
2. In the top right corner, click **Deploy > New deployment**.
3. Click the gear icon next to "Select type" and choose **Web app**.
4. Fill out the configuration:
   - **Description:** "Nexus Hub v0.9.0 Frontend" (or similar).
   - **Execute as:** "Me" (your email).
   - **Who has access:** "Only myself".
5. Click **Deploy**.
6. Copy the **Web app URL** provided. This is your personal, secure link to the Nexus Hub dashboard. You can bookmark this URL.

## Phase 10: Advanced Integrations (Telemetry & Zero-Trust Seeding)

With the v1.1 update, Nexus Hub supports immediate push notifications for critical errors and passive taxonomy ingestion from external scrapers.

### 1. Pushover Push Notifications (Telemetry Matrix)
To receive immediate mobile alerts for critical system failures (like SQLite database locks or dropped OAuth credentials):
1. Create an account at [Pushover.net](https://pushover.net/) and install the mobile app.
2. Copy your **User Key** from the main dashboard.
3. Click **Create an Application/API Token**, name it "Nexus Hub", and copy the generated **API Token/Key**.
4. Construct your webhook URL and add it to your `.env` file as `NEXUS_WEBHOOK_URL`:
   ```env
   NEXUS_WEBHOOK_URL=https://api.pushover.net/1/messages.json?user=YOUR_USER_KEY&token=YOUR_APP_TOKEN
   ```

### 2. Configure the Drive Seeder Folder (Taxonomy Bootstrapping)
To enable the backend Python VM to automatically ingest new correspondents and purposes from your external Nexus for Gmail worker:
1. Open Google Drive and create a dedicated folder for Nexus data transfers.
2. Open the folder and copy the Folder ID from the URL: `https://drive.google.com/drive/folders/[COPY_THIS_ID_HERE]`.
3. Add this ID to the `DRIVE_SEED_FOLDER_ID` variable in your `.env` file.
4. Ensure your standalone Apps Script (Nexus for Gmail) is programmed to save the `taxonomy_seed.json` file directly into this folder. 
5. The background `sync_engine.py` will automatically detect the file, ingest the multi-dimensional entity data, and place the new items in your UI's Zero-Trust Review Queue.