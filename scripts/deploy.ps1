# scripts/deploy.ps1
$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       Nexus for Google One-Click Deployment Wizard        " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$INSTANCE_NAME = "nexus-vm"
$ZONE = "us-central1-f"

Write-Host "`n[1/2] Syncing Serverless Frontend (Google Apps Script)..." -ForegroundColor Yellow
if (-not (Get-Command "clasp" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: clasp is not installed. Please install it globally (npm install -g @google/clasp)." -ForegroundColor Red
    exit
}
clasp push
Write-Host "--> Apps Script UI synced successfully!" -ForegroundColor Green

Write-Host "`n[2/2] Deploying Backend to Google Cloud VM..." -ForegroundColor Yellow

$envExists = gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="if [ -f /opt/nexus/backend/.env ]; then echo 'YES'; else echo 'NO'; fi"
$envExists = $envExists -replace "`r", ""
$envExists = $envExists -replace "`n", ""

if ($envExists -eq "NO") {
    Write-Host "`n*** ACTION REQUIRED: backend/.env FILE MISSING ***" -ForegroundColor Red
    $NEXUS_HMAC_SECRET = Read-Host "NEXUS_HMAC_SECRET (type a highly unique, secure passphrase)"
    $NEXUS_API_KEY = Read-Host "NEXUS_API_KEY (Your Gemini API Key)"
    $NEXUS_WEBHOOK_URL = Read-Host "NEXUS_WEBHOOK_URL (The permanent /exec URL for Apps Script)"

    $envScript = @"
        mkdir -p /opt/nexus/backend
        echo "NEXUS_HMAC_SECRET=$NEXUS_HMAC_SECRET" > /opt/nexus/backend/.env
        echo "NEXUS_API_KEY=$NEXUS_API_KEY" >> /opt/nexus/backend/.env
        echo "NEXUS_WEBHOOK_URL=$NEXUS_WEBHOOK_URL" >> /opt/nexus/backend/.env
        echo "backend/.env file generated successfully."
"@
    $envScript = $envScript -replace "`r", ""
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=$envScript
} else {
    $NEXUS_HMAC_SECRET = gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="grep '^NEXUS_HMAC_SECRET=' /opt/nexus/backend/.env | cut -d'=' -f2"
    $NEXUS_HMAC_SECRET = $NEXUS_HMAC_SECRET -replace "`r", ""
    $NEXUS_HMAC_SECRET = $NEXUS_HMAC_SECRET -replace "`n", ""
}

# The SSH command payload that executes on the Linux machine
$sshCommand = @"
    set -e
    echo -e '\n[VM] 1. Pulling latest code from git...'
    cd /opt/nexus
    git pull origin development || echo 'Warning: Could not pull git. Make sure you pushed your changes or setup SSH.'
    
    echo -e '\n[VM] 2. Activating Python Virtual Environment...'
    source venv/bin/activate
    
    echo -e '\n[VM] 3. Installing dependencies via pip...'
    pip install -r requirements.txt
    
    echo -e '\n[VM] 4. Running SQLite3 database migrations...'
    python3 db_init.py
    
    echo -e '\n[VM] 5. Restarting the FastAPI systemd daemon...'
    sudo systemctl daemon-reload
    sudo systemctl restart nexus.service
    
    echo -e '\n[VM] Deployment sequence completed securely.'
"@
# Strip Windows carriage returns before sending to Linux
$sshCommand = $sshCommand -replace "`r", ""
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=$sshCommand

$vmIp = gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
$vmIp = $vmIp -replace "`r", ""
$vmIp = $vmIp -replace "`n", ""
$NEXUS_VM_URL = "http://${vmIp}:8000"

Clear-Host
Write-Host "====================================================" -ForegroundColor Red
Write-Host "                 ACTION REQUIRED                    " -ForegroundColor Red
Write-Host "====================================================" -ForegroundColor Red
Write-Host "NEXUS_HMAC_SECRET: " -NoNewline; Write-Host $NEXUS_HMAC_SECRET -ForegroundColor Yellow
Write-Host "NEXUS_VM_URL:      " -NoNewline; Write-Host $NEXUS_VM_URL -ForegroundColor Yellow
Write-Host "`nPlease copy the values above. In a moment, your browser will open the Apps Script Editor. You MUST immediately go to: Project Settings (Gear Icon) -> Script Properties -> Add Script Property. Add NEXUS_HMAC_SECRET and NEXUS_VM_URL."

Read-Host "Press Enter to open the Editor..."
clasp open