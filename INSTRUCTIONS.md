# Nexus for Google - The Ultimate Beginner's Installation Masterclass

Welcome to Nexus for Google! If you've never used a terminal, spun up a cloud server, or worked with APIs, you are exactly who this guide was written for. We are going to build your personal, privacy-first, automated AI knowledge graph from scratch. 

By the end of this guide, you will have your very own Google Cloud server running silently in the background, intercepting your emails and files to organize them using the power of Google's Gemini AI.

Let's begin!

---

## Phase 0: The Google Cloud Walled Garden

> **🧠 Knowledge Point: What is an API?**
> API stands for Application Programming Interface. Think of it as a drive-thru window for software. Instead of clicking buttons on a screen, your server "orders" data (like fetching an email) directly from Google's backend.

We need to tell Google Cloud to allow your new server to talk to your personal Gmail and Drive. Because we are self-hosting this, we are creating a "Walled Garden"—your data never leaves your personal Google Account ecosystem.

### Step 1: Create a Google Cloud Project & Enable APIs
1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and log in with your primary Google account.
2. Accept the Terms of Service.
3. Click the dropdown at the very top left (next to the Google Cloud logo) and click **NEW PROJECT**. Name it `Nexus` and click **Create**.
4. You must enable Billing for your project to use cloud servers. Go to the **Billing** menu and link a credit card. (Don't worry, the e2-micro server we are using is well within the free tier!).

*Note: Our interactive wizard script will actually enable the specific APIs for you in Phase 1, so you don't have to click through all of them manually!*

### Step 2: The OAuth Consent Screen
> **🧠 Knowledge Point: What is an OAuth Consent Screen?**
> When an app asks to read your emails, Google shows a warning screen asking "Do you trust this app?". Because *you* are building this app for *yourself*, we set this to "Internal" or testing mode so only you can use it.

1. Using the left-hand hamburger menu, go to **APIs & Services > OAuth consent screen**.
2. Select **Internal** (if you have a Google Workspace account) or **External** (if you have a standard `@gmail.com` account). Click **Create**.
3. Fill in the **App name** (`Nexus`), **User support email**, and **Developer contact information** (just use your own email).
4. Click **Save and Continue** at the bottom of the subsequent screens. You don't need to add Scopes manually here.

> **⚠️ GOTCHA: ADDING YOURSELF AS A TEST USER**
> Before you finish Phase 0, you **MUST** add your own Gmail address to the "Test users" list if you selected "External". If you skip this, you will hit a hard "Error 403: access_denied" when trying to log into your own app later!

### Step 3: Generating Your Secret Keys
> **🧠 Knowledge Point: What is Headless Authentication?**
> A "headless" server is a computer running in the cloud with no monitor or web browser. Since our server has no screen, it can't click "Log In with Google". We must generate a special file (`credentials.json`) that acts as a VIP pass.

1. On the left menu, click **Credentials**.
2. At the top, click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
3. Under **Application type**, choose **Desktop app** (this is crucial for headless authentication).
4. Name it `Nexus Headless Server` and click **Create**.
5. A popup will appear with your Client ID and Client Secret. Click the **DOWNLOAD JSON** button.
6. Find the downloaded file on your computer and rename it EXACTLY to `credentials.json`. Keep it handy; we will need it in Phase 2.

---

## Phase 1: The Interactive Provisioner Wizard

We have engineered an Infrastructure as Code (IaC) deployment script that handles all the heavy lifting via an interactive prompt. 

Run `./scripts/provision.ps1` (or `.sh`) and follow the interactive terminal prompts to provision your Google Cloud environment, OAuth consent screen, and API keys.

**Multi-Environment Workflow:**
The script will now ask you if you want to create a new environment or configure an existing one. If configuring an existing one, the script will automatically discover your existing VMs via Google Cloud. The `.nexus_env` file handles all the details invisibly, storing both the `TARGET_VM` and the `TARGET_ZONE`. When deploying, if you ever need to change your target VM, simply type `list` when prompted and select from the dynamically generated menu.

---

## Phase 2: Securely Authenticating Your Server

Your server needs permission to interact with your data. 

1. Ensure you have downloaded the `credentials.json` file as instructed in Phase 1. 
2. During the provisioning script execution, when prompted, provide the full local path to this `credentials.json` file. The script will securely transfer it to your newly created VM.
3. Once the provisioning and deployment phases are complete, run the interactive authentication tunnel script based on your operating system:
   - **Windows:** `.\scripts\auth_tunnel.ps1`
   - **Mac/Linux:** `./scripts/auth_tunnel.sh`
4. The script will open a secure SSH tunnel to your VM. 
5. When prompted in the terminal, click the provided `localhost` link. This will open your browser and ask you to log into your Google Account and authorize the application.
6. Accept the permissions. The authentication token will automatically be saved securely on your server.

---

## Blue-Green Symlink Architecture

Nexus uses a Zero-Downtime deployment model based on symlinks. When you run the deploy script, a new release is downloaded into `/home/frank/nexus/releases/[timestamp]`.
- **Database Location:** The SQLite database safely lives in `/home/frank/nexus/shared/data/nexus.db` and is symlinked to the new release folder.
- **Rollback:** The active directory is `/home/frank/nexus/current`. To perform an emergency rollback, see `DEBUGGING.md`.

Now that the backend brain is running, we need to upload the visual dashboard.

> **⚠️ GOTCHA: ENABLE THE APPS SCRIPT API**
> Before you can use `clasp` to upload the code, you must manually grant your computer permission. Visit [https://script.google.com/home/usersettings](https://script.google.com/home/usersettings) and toggle the **"Google Apps Script API"** to **ON**. If you don't, the deployment will fail with an API permission error.

1. Ensure you have [Node.js](https://nodejs.org/) installed on your local computer.
2. Install Google's Apps Script tool globally by running:
   ```bash
   npm install -g @google/clasp
   ```
3. Log your terminal into your Google Account:
   ```bash
   clasp login
   ```
4. **INITIALIZE YOUR PROJECT:** Before deploying, generate the required configuration map so `clasp` knows where to send the code. Run:
   ```bash
   clasp create --title "Nexus for Google"
   ```
   *(Without this step, the deployer will fail with a "Project settings not found" error!)*

5. Now, deploy the entire system using our verbose wizard based on your operating system:

### Windows Users
Run the deployment script using PowerShell. It automatically pushes updates to your server and frontend.
```powershell
.\scripts\deploy.ps1
```

### Mac/Linux Users
Make the script executable and run it using Bash. It automatically pushes updates to your server and frontend.
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

**What is the deployer doing?**
It automatically pushes your HTML and CSS files to Google Apps Script. Then, it securely reaches into your cloud server, pulls any code updates, updates the Python libraries, runs database migrations, and cleanly restarts the background server.

---

## Phase 4: Securing the Bridge (HMAC)

> **🧠 Knowledge Point: What is HMAC?**
> Hash-Based Message Authentication Code (HMAC) is like a secret handshake. Because your backend API is open to the internet, we need to ensure only *your* specific dashboard can command it. We give both the UI and the Server the same random password. The UI mathematically hashes your requests using the password, and the Server verifies it.

1. We need to tell your Apps Script dashboard what the secret password is. Go to [script.google.com](https://script.google.com) and open your Nexus project.
2. Open `Code.gs`.
3. Scroll to the bottom and paste this temporary code:
   ```javascript
   function runOnce() {
     configureHMAC("MAKE_UP_A_LONG_RANDOM_PASSWORD_HERE");
   }
   ```
4. Select `runOnce` from the top dropdown and click **Run**.
5. **CRITICAL:** Once it succeeds, delete the `runOnce` function entirely.
6. Next, tell the UI where your server lives. Go to **Project Settings** (gear icon) on the left.
7. Scroll down to **Script Properties** and click **Edit script properties**.
8. Add a property named `NEXUS_VM_URL`. Set the value to your server's External IP address (e.g., `http://192.168.10.125:8000`). You can find your IP in the Google Cloud Console under VM Instances.
9. **Lastly, on your cloud server:**
   Run `./scripts/connect.ps1` (or `.sh`) to easily SSH into your VM.
   ```bash
   cd /opt/nexus
   nano .env
   ```
10. Type in: `NEXUS_HMAC_SECRET=MAKE_UP_A_LONG_RANDOM_PASSWORD_HERE` (using the exact same password from step 3).
11. Add your Gemini API key on a new line: `GEMINI_API_KEY=your_key_here`.
12. Press `Ctrl+O` to save, `Enter` to confirm, and `Ctrl+X` to exit.
13. Type `sudo systemctl restart nexus.service`.

---

## Phase 5: Launching Your Dashboard

Now that your Walled Garden is built and secured, it's time to access the Nexus for Google Knowledge Graph.

1. Open your local terminal (where you originally ran the deploy scripts) and run:
   ```bash
   clasp open
   ```
   *This will launch the Google Apps Script editor in your browser.*
2. In the top right corner of the editor, click the blue **Deploy** button, then select **New deployment**.
3. Click the gear icon next to "Select type" and choose **Web app**.
4. In the configuration settings:
   - **Description:** `Initial Release`
   - **Execute as:** `Me (your email)`
   - **Who has access:** `Only myself` *(Crucial for privacy!)*
5. Click **Deploy**.
6. Google will provide you with a **Web App URL**. Copy this link!

**This URL is the permanent, private home for your AI knowledge graph.** Bookmark it.

**Congratulations! You have successfully built and secured a multi-tier cloud application. Welcome to Nexus for Google.**

---

## Critical Troubleshooting (Lessons Learned)

- **Apps Script Phantom Cache:** The `/exec` deployment URL is an immutable snapshot. Active UI development must strictly use the `/dev` (Test Deployment) URL. To force Google to clear the inner iframe cache after a clasp push, developers must append a version string to the URL (e.g., `?v=123`).
- **The OAuth Black Hole:** If the `/dev` URL loads a completely blank white screen, the browser has blocked a hidden authorization popup. Fix: Open `Code.gs` in the native Apps Script Editor, manually run `doGet()`, and accept the OAuth permission scopes.
- **API Method Matching:** A 405 Method Not Allowed error between Apps Script and FastAPI means the `UrlFetchApp` method (`'method': 'get'`) mismatches the FastAPI route decorator (`@app.get`). They must align perfectly.
- **Webhook Loop:** For the Python backend to push notifications back to the UI, the `NEXUS_WEBHOOK_URL` in the VM's `.env` file must be set to the permanent `/exec` deployment URL.