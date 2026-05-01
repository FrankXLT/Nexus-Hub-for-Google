# Nexus Hub for Google - The Ultimate Beginner's Installation Masterclass

Welcome to Nexus Hub! If you've never used a terminal, spun up a cloud server, or worked with APIs, you are exactly who this guide was written for. We are going to build your personal, privacy-first, automated AI knowledge graph from scratch. 

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
3. Click the dropdown at the very top left (next to the Google Cloud logo) and click **NEW PROJECT**. Name it `Nexus Hub` and click **Create**.
4. You must enable Billing for your project to use cloud servers. Go to the **Billing** menu and link a credit card. (Don't worry, the e2-micro server we are using is well within the free tier!).

*Note: Our interactive wizard script will actually enable the specific APIs for you in Phase 1, so you don't have to click through all of them manually!*

### Step 2: The OAuth Consent Screen
> **🧠 Knowledge Point: What is an OAuth Consent Screen?**
> When an app asks to read your emails, Google shows a warning screen asking "Do you trust this app?". Because *you* are building this app for *yourself*, we set this to "Internal" or testing mode so only you can use it.

1. Using the left-hand hamburger menu, go to **APIs & Services > OAuth consent screen**.
2. Select **Internal** (if you have a Google Workspace account) or **External** (if you have a standard `@gmail.com` account). Click **Create**.
3. Fill in the **App name** (`Nexus Hub`), **User support email**, and **Developer contact information** (just use your own email).
4. Click **Save and Continue** at the bottom of the subsequent screens. You don't need to add Test users or Scopes manually here.

### Step 3: Generating Your Secret Keys
> **🧠 Knowledge Point: What is Headless Authentication?**
> A "headless" server is a computer running in the cloud with no monitor or web browser. Since our server has no screen, it can't click "Log In with Google". We must generate a special file (`credentials.json`) that acts as a VIP pass.

1. On the left menu, click **Credentials**.
2. At the top, click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
3. Under **Application type**, choose **Desktop app** (this is crucial for headless authentication).
4. Name it `Nexus Hub Headless Server` and click **Create**.
5. A popup will appear with your Client ID and Client Secret. Click the **DOWNLOAD JSON** button.
6. Find the downloaded file on your computer and rename it EXACTLY to `credentials.json`. Keep it handy; we will need it in Phase 2.

---

## Phase 1: The Interactive Provisioner Wizard

We have engineered an Infrastructure as Code (IaC) deployment script that does all the heavy lifting. It will automatically spin up your server and install everything.

1. Open your computer's terminal (Command Prompt/PowerShell on Windows, Terminal on Mac/Linux).
2. Ensure you have the Google Cloud CLI installed. (If not, download it [here](https://cloud.google.com/sdk/docs/install)).
3. Authenticate your terminal by running:
   ```bash
   gcloud auth login
   gcloud config set project [YOUR_PROJECT_ID]
   ```
4. Navigate to the folder where you downloaded/cloned the Nexus Hub code.
5. Run the provisioning wizard:
   ```bash
   chmod +x scripts/provision.sh
   ./scripts/provision.sh
   ```

**What is the wizard doing?**
- **Enabling APIs:** It turns on the invisible pipelines to Gmail, Drive, Document AI, Tasks, and People.
- **Firewall Rules:** It punches a tiny, secure hole in the Google Cloud firewall (Port 8000) so your web dashboard can talk to the server.
- **VM Creation:** It rents an `e2-micro` server and injects a "startup script". This script automatically installs Python, SQLite3, and sets up a `systemd` daemon (a background process that ensures your server runs 24/7 even if it reboots).

---

## Phase 2: Securely Authenticating Your Server

Your server is alive, but it doesn't have the VIP pass (`credentials.json`) to read your emails yet.

1. Open a terminal and use `gcloud` to securely transfer your file to the new server:
   ```bash
   gcloud compute scp /path/to/your/credentials.json nexus-hub-vm:/opt/nexus-hub/ --zone=us-central1-f
   ```

2. Next, we need to generate an active login session. We do this by creating a secure "SSH Tunnel" from your local computer to the cloud server. Run this command:
   ```bash
   gcloud compute ssh nexus-hub-vm --zone=us-central1-f --ssh-flag="-L 8080:localhost:8080"
   ```

3. You are now logged into the cloud server! Run these commands to trigger the login flow:
   ```bash
   cd /opt/nexus-hub
   source venv/bin/activate
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   python3 auth.py
   ```

4. The terminal will print a message saying a local server is running. Open your web browser and go to: `http://localhost:8080`.
5. Follow the Google Login prompts. You will see a warning saying "Google hasn't verified this app." Click **Advanced**, then **Go to Nexus Hub (unsafe)**. Click **Continue** to grant access to your Gmail and Drive.
6. The terminal will automatically save a new file called `token.json`. Your server is permanently authenticated! You can type `exit` to leave the SSH session.

---

## Phase 3: The Frontend UI & One-Click Deployer

Now that the backend brain is running, we need to upload the visual dashboard.

1. Ensure you have [Node.js](https://nodejs.org/) installed on your local computer.
2. Install Google's Apps Script tool globally by running:
   ```bash
   npm install -g @google/clasp
   ```
3. Log your terminal into your Google Account:
   ```bash
   clasp login
   ```
4. Now, deploy the entire system using our verbose wizard:
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

1. We need to tell your Apps Script dashboard what the secret password is. Go to [script.google.com](https://script.google.com) and open your Nexus Hub project.
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
8. Add a property named `NEXUS_VM_URL`. Set the value to your server's External IP address (e.g., `http://34.123.45.67:8000`). You can find your IP in the Google Cloud Console under VM Instances.
9. **Lastly, on your cloud server:**
   ```bash
   gcloud compute ssh nexus-hub-vm --zone=us-central1-f
   cd /opt/nexus-hub
   nano .env
   ```
10. Type in: `NEXUS_HMAC_SECRET=MAKE_UP_A_LONG_RANDOM_PASSWORD_HERE` (using the exact same password from step 3).
11. Add your Gemini API key on a new line: `GEMINI_API_KEY=your_key_here`.
12. Press `Ctrl+O` to save, `Enter` to confirm, and `Ctrl+X` to exit.
13. Type `sudo systemctl restart nexus-hub.service`.

**Congratulations! You have successfully built and secured a multi-tier cloud application. Welcome to the Nexus Hub.**
