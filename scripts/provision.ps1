# scripts/provision.ps1
$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "    Welcome to the Nexus for Google Provisioning Wizard    " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "This script will automatically configure your Google Cloud project,"
Write-Host "enable the necessary APIs, and build your backend server.`n"

Write-Host "Prerequisite: Google Cloud CLI" -ForegroundColor Cyan
if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Google Cloud CLI (gcloud) is not installed." -ForegroundColor Red
    Write-Host "Please download from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit
}

Write-Host "Checking authentication status..."
$ACTIVE_ACCOUNT = gcloud auth list --filter=status:ACTIVE --format="value(account)"

if ([string]::IsNullOrWhiteSpace($ACTIVE_ACCOUNT)) {
    Write-Host "No active Google Cloud account found." -ForegroundColor Yellow
    $doLogin = Read-Host "Would you like to log in now? (Y/n)"
    if ($doLogin -notmatch "^[nN]") {
        gcloud auth login
        $ACTIVE_ACCOUNT = gcloud auth list --filter=status:ACTIVE --format="value(account)"
    } else {
        Write-Host "Authentication required to continue. Exiting." -ForegroundColor Red
        exit
    }
}
Write-Host "Authenticated as: $ACTIVE_ACCOUNT" -ForegroundColor Green

Write-Host "`nPrerequisite: Google Cloud Project & Billing" -ForegroundColor Cyan
Write-Host "1. Go to " -NoNewline -ForegroundColor Yellow
Write-Host "https://console.cloud.google.com/" -BackgroundColor White -ForegroundColor Black
Write-Host "2. Create a new project (e.g., 'Nexus')." -ForegroundColor Yellow
Write-Host "3. Go to the Billing menu and link a credit card." -ForegroundColor Yellow
Read-Host "Press [Enter] when your project is created and billing is enabled..."

Write-Host "`nFetching your Google Cloud Projects..." -ForegroundColor Cyan
$projects = gcloud projects list --format="value(projectId,name)"
$projectList = @($projects)

if ($projectList.Count -eq 0) {
    Write-Host "Error: No Google Cloud projects found. Please create one in the console first." -ForegroundColor Red
    exit
}

for ($i=0; $i -lt $projectList.Count; $i++) {
    Write-Host "[$i] $($projectList[$i])"
}

$projIdx = Read-Host "Select Project number"
$SELECTED_PROJECT = $projectList[[int]$projIdx]
$PROJECT_ID = ($SELECTED_PROJECT -split "\s+")[0]

Write-Host "Targeting Project: $PROJECT_ID" -ForegroundColor Green
gcloud config set project $PROJECT_ID --quiet

$ENV_OPTION = Read-Host "Do you want to (1) Create a NEW Nexus Environment or (2) Configure an EXISTING one? (1/2)"

if ($ENV_OPTION -eq "2") {
    Write-Host "Fetching existing VMs..."
    $vms = gcloud compute instances list --format="value(name,zone,status)" --project=$PROJECT_ID
    $vmsList = @($vms)
    for ($i=0; $i -lt $vmsList.Count; $i++) {
        Write-Host "[$i] $($vmsList[$i])"
    }
    $vmIdx = Read-Host "Select VM number"
    $SELECTED_VM = $vmsList[[int]$vmIdx]
    $parts = $SELECTED_VM -split "\s+"
    $INSTANCE_NAME = $parts[0]
    $ZONE = $parts[1]
    $ENV_LABEL = $INSTANCE_NAME -replace "^nexus-vm-",""
} else {
    $ENV_OPTION = "1"
    $ZONE = "us-central1-f"
    $ENV_LABEL = Read-Host "Enter the Environment Label (e.g., dev, staging, prod)"
    if ([string]::IsNullOrWhiteSpace($ENV_LABEL)) {
        $ENV_LABEL = "dev"
    }
    $INSTANCE_NAME = "nexus-vm-$ENV_LABEL"
}

Write-Host "Using Project: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "Using Zone:    $ZONE" -ForegroundColor Yellow
Write-Host "Instance Name: $INSTANCE_NAME`n" -ForegroundColor Yellow

Read-Host "Press [Enter] to begin the provisioning process..."

Write-Host "`n[1/5] Enabling Google Workspace & AI APIs..." -ForegroundColor Cyan
Write-Host "Please go to Google Cloud Console and enable the Drive and Gmail APIs." -ForegroundColor Yellow
Read-Host "Press [Enter] when complete..."
gcloud services enable `
    gmail.googleapis.com `
    drive.googleapis.com `
    pubsub.googleapis.com `
    documentai.googleapis.com `
    people.googleapis.com `
    tasks.googleapis.com `
    compute.googleapis.com `
    --project=$PROJECT_ID
Write-Host "APIs successfully enabled!" -ForegroundColor Green

Write-Host "`n[2/5] Configuring Network Security..." -ForegroundColor Cyan
$ruleName = "nexus-allow-8000"
$existingRule = gcloud compute firewall-rules list --filter="name=$ruleName" --format="value(name)" --project=$PROJECT_ID

if (![string]::IsNullOrWhiteSpace($existingRule) -and $existingRule -match $ruleName) {
    Write-Host "Firewall rule '$ruleName' already exists. Skipping." -ForegroundColor Green
} else {
    gcloud compute firewall-rules create $ruleName `
        --action=ALLOW `
        --rules=tcp:8000 `
        --source-ranges=0.0.0.0/0 `
        --target-tags=nexus-hub-api `
        --project=$PROJECT_ID
    Write-Host "Firewall rule created!" -ForegroundColor Green
}

Write-Host "`n[3/5] Manual Step: OAuth Configuration" -ForegroundColor Cyan
Write-Host "Instructions:" -ForegroundColor Yellow
Write-Host "1. Go to: " -NoNewline -ForegroundColor Yellow
Write-Host "https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID" -BackgroundColor White -ForegroundColor Black
Write-Host "2. Select 'Internal' or 'External' and click Create." -ForegroundColor Yellow
Write-Host "3. Fill in the required app names and emails." -ForegroundColor Yellow
Write-Host "4. Skip adding scopes here, just save and continue.`n" -ForegroundColor Yellow
Read-Host "Press [Enter] when you have configured the Consent Screen..."

Write-Host "`n[4/5] Manual Step: Generating Credentials" -ForegroundColor Cyan
Write-Host "Instructions:" -ForegroundColor Yellow
Write-Host "1. Go to: " -NoNewline -ForegroundColor Yellow
Write-Host "https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID" -BackgroundColor White -ForegroundColor Black
Write-Host "2. Click 'CREATE CREDENTIALS' > 'OAuth client ID'." -ForegroundColor Yellow
Write-Host "3. Select 'Desktop app' for the Application type." -ForegroundColor Yellow
Write-Host "4. Click Create, then DOWNLOAD the JSON file." -ForegroundColor Yellow
Write-Host "5. Rename the downloaded file EXACTLY to: credentials.json`n" -ForegroundColor Yellow
Read-Host "Press [Enter] when you have downloaded 'credentials.json' to your local machine..."

Write-Host "`n[5/5] Provisioning the Virtual Machine (VM)..." -ForegroundColor Cyan

if ($ENV_OPTION -eq "1") {
# The startup script payload
$startupScript = @"
#!/bin/bash
echo ">>> Starting Nexus Bootstrap..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 git curl
"@

# Write to a temporary file to bypass PowerShell string parsing issues
$tempScriptPath = "startup-script.sh"
Set-Content -Path $tempScriptPath -Value $startupScript -Encoding Ascii

# Execute gcloud using the file instead of the inline string
gcloud compute instances create $INSTANCE_NAME `
    --project=$PROJECT_ID `
    --zone=$ZONE `
    --machine-type=e2-micro `
    --tags=nexus-api `
    --scopes=https://www.googleapis.com/auth/cloud-platform `
    --metadata-from-file="startup-script=$tempScriptPath"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n====================================================" -ForegroundColor Red
    Write-Host "          Error: VM Provisioning Failed!            " -ForegroundColor Red
    Write-Host "====================================================" -ForegroundColor Red
    Write-Host "Please check the gcloud error output above." -ForegroundColor White
    
    # Keep the temp file for debugging
    exit
}

Write-Host "Waiting 30 seconds for the VM's SSH daemon to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

$serviceContent = "[Unit]\nDescription=Nexus FastAPI Backend\nAfter=network.target\n\n[Service]\nUser=`$USER\nWorkingDirectory=`$HOME/nexus/current/backend\nEnvironment=PATH=`$HOME/nexus/current/backend/venv/bin\nExecStart=`$HOME/nexus/current/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000\nRestart=always\n\n[Install]\nWantedBy=multi-user.target"
$bootstrapCmd = "mkdir -p `$HOME/nexus/shared/data `$HOME/nexus/shared/backups && chmod -R 777 `$HOME/nexus/shared && echo -e '$serviceContent' > /tmp/nexus.service && sudo mv /tmp/nexus.service /etc/systemd/system/nexus.service && sudo systemctl daemon-reload && sudo systemctl enable nexus.service"
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="$bootstrapCmd" --quiet --strict-host-key-checking=no

# Clean up the temporary file
Remove-Item -Path $tempScriptPath -Force -ErrorAction SilentlyContinue

}

Write-Host "`n[6/6] Uploading Credentials..." -ForegroundColor Cyan
$CREDS_EXISTS = gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --quiet --strict-host-key-checking=no --command="if [ -f `$HOME/nexus/shared/credentials.json ]; then echo 'YES'; else echo 'NO'; fi"
$CREDS_EXISTS = $CREDS_EXISTS -replace "`r", ""
$CREDS_EXISTS = $CREDS_EXISTS -replace "`n", ""

if ($CREDS_EXISTS -eq "YES") {
    Write-Host "Credentials already found on VM, skipping upload." -ForegroundColor Green
} else {
    $CREDS_PATH = Read-Host "Please enter the full local path to your downloaded credentials.json file"
    if (-not (Test-Path $CREDS_PATH)) {
        Write-Host "Error: credentials.json not found at $CREDS_PATH" -ForegroundColor Red
        exit
    }

    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --quiet --strict-host-key-checking=no --command="mkdir -p `$HOME/nexus/shared"
    gcloud compute scp $CREDS_PATH "$($INSTANCE_NAME):~/nexus/shared/credentials.json" --zone=$ZONE --quiet --strict-host-key-checking=no
}

Write-Host "`nApps Script Initialization" -ForegroundColor Cyan
$UPPER_ENV = $ENV_LABEL.ToUpper()
Write-Host "Please name your Apps Script project: 'Nexus for Google - [$UPPER_ENV]'" -ForegroundColor Cyan
Write-Host "Please open the Google Apps Script Editor for your project." -ForegroundColor Yellow
Write-Host "Click the Gear Icon (Project Settings) on the left sidebar." -ForegroundColor Yellow
Write-Host "Under 'IDs', copy the Script ID." -ForegroundColor Yellow
$SCRIPT_ID = Read-Host "Please paste your Script ID here"

$claspJsonContent = "{`"scriptId`":`"$SCRIPT_ID`",`"rootDir`":`"frontend/`"}"
Set-Content -Path ".clasp.json" -Value $claspJsonContent -Encoding Ascii
clasp setting projectId $PROJECT_ID
Write-Host "Apps Script linked to GCP Project for Cloud Logging." -ForegroundColor Green
Set-Content -Path ".nexus_env" -Value "TARGET_VM=$INSTANCE_NAME`nTARGET_ZONE=$ZONE" -Encoding Ascii
Write-Host "Success! Local clasp is now securely linked to your Google account and restricted to the frontend/ directory." -ForegroundColor Green

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host "             Provisioning Complete!                 " -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host "Your server is ready."
Write-Host "Next steps (See INSTRUCTIONS.md):"
Write-Host "1. Run scripts\deploy.ps1 to push the code and start the backend."
Write-Host "2. Run scripts\auth_tunnel.ps1 to authenticate the server.`n"