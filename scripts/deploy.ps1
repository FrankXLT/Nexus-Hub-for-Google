# scripts/deploy.ps1
$ErrorActionPreference = "Stop"
$env:CLOUDSDK_COMPUTE_USE_OPENSSH = "1"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       Nexus for Google One-Click Deployment Wizard        " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

if (-not (Test-Path ".nexus_env")) {
    Write-Host "Error: .nexus_env file not found." -ForegroundColor Red
    exit
}
$TARGET_VM = (Get-Content .nexus_env | Where-Object { $_ -match "^TARGET_VM=" }) -replace "^TARGET_VM=",""
$TARGET_ZONE = (Get-Content .nexus_env | Where-Object { $_ -match "^TARGET_ZONE=" }) -replace "^TARGET_ZONE=",""

$confirm_vm = Read-Host "Deploying to $TARGET_VM. Press Enter to confirm, or type 'list' to choose a different VM"
if ($confirm_vm -eq "list") {
    Write-Host "Fetching existing VMs..."
    $vms = gcloud compute instances list --format="value(name,zone,status)"
    $vmsList = @($vms)
    for ($i=0; $i -lt $vmsList.Count; $i++) {
        Write-Host "[$i] $($vmsList[$i])"
    }
    $vmIdx = Read-Host "Select VM number"
    $SELECTED_VM = $vmsList[[int]$vmIdx]
    $parts = $SELECTED_VM -split "\s+"
    $TARGET_VM = $parts[0]
    $TARGET_ZONE = $parts[1]
    Set-Content -Path ".nexus_env" -Value "TARGET_VM=$TARGET_VM`nTARGET_ZONE=$TARGET_ZONE" -Encoding Ascii
}

$INSTANCE_NAME = $TARGET_VM
$ZONE = $TARGET_ZONE

Write-Host "Fetching git branches..."
git fetch origin
$branches = git branch -r | Select-String "origin/" | Where-Object { $_ -notmatch "HEAD" } | ForEach-Object { $_.ToString().Trim() -replace "origin/","" }
$bList = @($branches)
for ($i=0; $i -lt $bList.Count; $i++) {
    Write-Host "[$i] $($bList[$i])"
}
$bIdx = Read-Host "Select branch number"
$SELECTED_BRANCH = $bList[[int]$bIdx]

if ($INSTANCE_NAME -match "prod" -and $SELECTED_BRANCH -ne "main") {
    $confirm = Read-Host "Warning: Deploying non-main branch to prod! Continue? (Y/N)"
    if ($confirm -notmatch "^[Yy]$") { exit }
}

git checkout $SELECTED_BRANCH
git pull origin $SELECTED_BRANCH

$doBackup = Read-Host "Backup remote SQLite database? (Y/n)"
if ($doBackup -notmatch "^[Nn]$") {
    $BACKUP_CMD = "mkdir -p `$HOME/nexus/shared/backups && cp `$HOME/nexus/shared/data/nexus.db `$HOME/nexus/shared/backups/nexus_`$(date +%Y%m%d_%H%M%S).db || echo 'No DB to backup yet.'"
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --strict-host-key-checking=no --command=$BACKUP_CMD
}

Write-Host "`n[1/2] Syncing Serverless Frontend (Google Apps Script)..." -ForegroundColor Yellow
if (-not (Get-Command "clasp" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: clasp is not installed. Please install it globally (npm install -g @google/clasp)." -ForegroundColor Red
    exit
}
clasp push -f
$deployOut = clasp deploy -d "Nexus Auto-Deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>&1
$deployOutString = $deployOut -join "`n"

# Strip invisible ANSI color codes that break regex
$deployOutClean = $deployOutString -replace "`e\[[0-9;]*m", ""

if ($deployOutClean -match "(?:-\s|Deployed\s)([A-Za-z0-9_-]+)\s*@") {
    $deployId = $Matches[1]
} else {
    Write-Host "`n[FATAL] Error parsing Deployment ID. Clasp output was:" -ForegroundColor Red
    Write-Host $deployOutString -ForegroundColor Yellow
    exit
}
$NEXUS_WEB_APP_URL = "https://script.google.com/macros/s/$deployId/exec"
Write-Host "--> Apps Script UI synced successfully! URL: $NEXUS_WEB_APP_URL" -ForegroundColor Green

Write-Host "`n[2/2] Deploying Backend to Google Cloud VM..." -ForegroundColor Yellow

$envExists = gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --strict-host-key-checking=no --command="if [ -f `$HOME/nexus/shared/.env ]; then echo 'YES'; else echo 'NO'; fi"
$envExists = $envExists -replace "`r", ""
$envExists = $envExists -replace "`n", ""

if ($envExists -eq "NO") {
    Write-Host "`n*** ACTION REQUIRED: shared/.env FILE MISSING ***" -ForegroundColor Red
    $NEXUS_HMAC_SECRET = Read-Host "NEXUS_HMAC_SECRET (type a highly unique, secure passphrase)"
    $NEXUS_API_KEY = Read-Host "NEXUS_API_KEY (Your Gemini API Key)"

    $envScript = "mkdir -p `$HOME/nexus/shared && echo 'NEXUS_HMAC_SECRET=$NEXUS_HMAC_SECRET' > `$HOME/nexus/shared/.env && echo 'NEXUS_API_KEY=$NEXUS_API_KEY' >> `$HOME/nexus/shared/.env && echo 'NEXUS_WEBHOOK_URL=$NEXUS_WEB_APP_URL' >> `$HOME/nexus/shared/.env && echo 'shared/.env file generated successfully.'"
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --strict-host-key-checking=no --command=$envScript
} else {
    $NEXUS_HMAC_SECRET = gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --strict-host-key-checking=no --command="grep '^NEXUS_HMAC_SECRET=' `$HOME/nexus/shared/.env | cut -d'=' -f2"
    $NEXUS_HMAC_SECRET = $NEXUS_HMAC_SECRET -replace "`r", ""
    $NEXUS_HMAC_SECRET = $NEXUS_HMAC_SECRET -replace "`n", ""
}

$sshCommand = @"
    set -e
    NEXUS_ROOT="`$HOME/nexus"
    RELEASE_DIR=releases/`$(date +%Y%m%d_%H%M%S)
    FULL_RELEASE_DIR="`$NEXUS_ROOT/`$RELEASE_DIR"
    
    echo -e '\n[VM] 1. Preparing directories...'
    mkdir -p `$NEXUS_ROOT/shared/data
    mkdir -p `$NEXUS_ROOT/shared/backups
    mkdir -p `$NEXUS_ROOT/releases
    
    echo -e '\n[VM] 2. Cloning code into new release directory...'
    git clone --branch $SELECTED_BRANCH https://github.com/FrankXLT/Nexus-for-Google.git `$FULL_RELEASE_DIR
    
    echo -e '\n[VM] 3. Activating Python Virtual Environment...'
    cd `$FULL_RELEASE_DIR/backend
    python3 -m venv venv
    source venv/bin/activate
    
    echo -e '\n[VM] 4. Installing dependencies via pip...'
    pip install -r requirements.txt --progress-bar off --quiet
    
    echo -e '\n[VM] 5. Setting up Symlinks...'
    ln -s `$NEXUS_ROOT/shared/data/nexus.db `$FULL_RELEASE_DIR/backend/nexus.db
    ln -s `$NEXUS_ROOT/shared/.env `$FULL_RELEASE_DIR/backend/.env
    ln -s `$NEXUS_ROOT/shared/credentials.json `$FULL_RELEASE_DIR/backend/credentials.json
    ln -s `$NEXUS_ROOT/shared/token.json `$FULL_RELEASE_DIR/backend/token.json
    
    echo -e '\n[VM] 6. Running SQLite3 database migrations...'
    python3 db_init.py
    
    echo -e '\n[VM] 7. Updating main symlink...'
    ln -sfn `$FULL_RELEASE_DIR `$NEXUS_ROOT/current
    
    echo -e '\n[VM] 7.5. Patching systemd absolute paths...'
    echo -e '[Unit]\nDescription=Nexus FastAPI Backend\nAfter=network.target\n\n[Service]\nUser='`$USER'\nWorkingDirectory='`$HOME'/nexus/current/backend\nEnvironment=PATH='`$HOME'/nexus/current/backend/venv/bin\nExecStart='`$HOME'/nexus/current/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000\nRestart=always\n\n[Install]\nWantedBy=multi-user.target' | sudo tee /etc/systemd/system/nexus.service > /dev/null
    
    echo -e '\n[VM] 8. Restarting the FastAPI systemd daemon...'
    sudo systemctl daemon-reload
    sudo systemctl enable nexus.service
    sudo systemctl restart nexus.service
    
    echo -e '\n[VM] Deployment sequence completed securely.'
"@
$sshCommand = $sshCommand -replace "`r", ""
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --strict-host-key-checking=no --command="$sshCommand"

$vmIp = gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
$vmIp = $vmIp -replace "`r", ""
$vmIp = $vmIp -replace "`n", ""
$NEXUS_VM_URL = "http://${vmIp}:8000"

Write-Host "====================================================" -ForegroundColor Red
Write-Host "                 ACTION REQUIRED                    " -ForegroundColor Red
Write-Host "====================================================" -ForegroundColor Red
Write-Host "NEXUS_HMAC_SECRET: " -NoNewline; Write-Host $NEXUS_HMAC_SECRET -ForegroundColor Yellow
Write-Host "NEXUS_VM_URL:      " -NoNewline; Write-Host $NEXUS_VM_URL -ForegroundColor Yellow
Write-Host "`nPlease copy the variables above. In a moment, your browser will open the Apps Script Editor. You MUST immediately go to: Project Settings (Gear Icon) -> Script Properties -> Add Script Property. Add NEXUS_HMAC_SECRET and NEXUS_VM_URL."

Read-Host "Press Enter to open the Editor..."
$claspJson = Get-Content .clasp.json | ConvertFrom-Json
$scriptId = $claspJson.scriptId
$editorUrl = "https://script.google.com/d/$scriptId/edit"
Write-Host "`nIf the browser does not open automatically, please visit: " -NoNewline -ForegroundColor Cyan
Write-Host $editorUrl -BackgroundColor White -ForegroundColor Black
Start-Process $editorUrl