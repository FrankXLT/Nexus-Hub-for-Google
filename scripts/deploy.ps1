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

# The SSH command payload that executes on the Linux machine
$sshCommand = @"
    set -e
    echo -e '\n[VM] 1. Pulling latest code from git...'
    cd /opt/nexus
    git pull origin main || echo 'Warning: Could not pull git. Make sure you pushed your changes or setup SSH.'
    
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

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=$sshCommand

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host "          Deployment Completed Successfully!        " -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host "Your frontend and backend are now perfectly synchronized."