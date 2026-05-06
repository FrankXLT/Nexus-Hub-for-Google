# scripts/provision.ps1
$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "    Welcome to the Nexus for Google Provisioning Wizard    " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "This script will automatically configure your Google Cloud project,"
Write-Host "enable the necessary APIs, and build your backend server.`n"

Write-Host "Prerequisite: Google Cloud CLI" -ForegroundColor Cyan
Write-Host "Please ensure you have installed the Google Cloud CLI (gcloud)." -ForegroundColor Yellow
Write-Host "Download from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
Read-Host "Press [Enter] when you have installed gcloud and run 'gcloud auth login'..."

# Verify gcloud
if (-not (Get-Command "gcloud" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Google Cloud CLI (gcloud) is not installed." -ForegroundColor Red
    exit
}

Write-Host "`nPrerequisite: Google Cloud Project & Billing" -ForegroundColor Cyan
Write-Host "1. Go to https://console.cloud.google.com/" -ForegroundColor Yellow
Write-Host "2. Create a new project (e.g., 'Nexus')." -ForegroundColor Yellow
Write-Host "3. Go to the Billing menu and link a credit card." -ForegroundColor Yellow
Read-Host "Press [Enter] when your project is created and billing is enabled..."

$PROJECT_ID = Read-Host "Please enter your Google Cloud Project ID"
if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
    Write-Host "Error: No Google Cloud Project ID provided." -ForegroundColor Red
    exit
}
gcloud config set project $PROJECT_ID

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
$ruleName = "nexus-hub-allow-8000"
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
Write-Host "1. Go to: https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
Write-Host "2. Select 'Internal' or 'External' and click Create."
Write-Host "3. Fill in the required app names and emails."
Write-Host "4. Skip adding scopes here, just save and continue.`n"
Read-Host "Press [Enter] when you have configured the Consent Screen..."

Write-Host "`n[4/5] Manual Step: Generating Credentials" -ForegroundColor Cyan
Write-Host "Instructions:" -ForegroundColor Yellow
Write-Host "1. Go to: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
Write-Host "2. Click 'CREATE CREDENTIALS' > 'OAuth client ID'."
Write-Host "3. Select 'Desktop app' for the Application type."
Write-Host "4. Click Create, then DOWNLOAD the JSON file."
Write-Host "5. Rename the downloaded file EXACTLY to: credentials.json`n"
Read-Host "Press [Enter] when you have downloaded 'credentials.json' to your local machine..."

Write-Host "`n[5/5] Provisioning the Virtual Machine (VM)..." -ForegroundColor Cyan

if ($ENV_OPTION -eq "1") {
# The startup script payload
$startupScript = @"
#!/bin/bash
echo ">>> Starting Nexus Bootstrap..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 git curl

echo ">>> Creating /home/frank/nexus directory..."
mkdir -p /home/frank/nexus/shared/data
mkdir -p /home/frank/nexus/shared/backups
chmod -R 777 /home/frank/nexus

echo ">>> Configuring systemd daemon for FastAPI..."
cat > /etc/systemd/system/nexus.service <<EOF
[Unit]
Description=Nexus FastAPI Backend
After=network.target

[Service]
User=root
WorkingDirectory=/home/frank/nexus/current/backend
Environment=PATH=/home/frank/nexus/current/backend/venv/bin
ExecStart=/home/frank/nexus/current/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable nexus.service
echo ">>> Bootstrap complete!"
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
    Write-Host "Please check the gcloud error output above."
    
    # Keep the temp file for debugging
    exit
}

# Clean up the temporary file
Remove-Item -Path $tempScriptPath -Force -ErrorAction SilentlyContinue

$CREDS_PATH = Read-Host "Please enter the full local path to your downloaded credentials.json file"
if (-not (Test-Path $CREDS_PATH)) {
    Write-Host "Error: credentials.json not found at $CREDS_PATH" -ForegroundColor Red
    exit
}

Write-Host "Waiting for VM SSH daemon to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="mkdir -p /home/frank/nexus/shared"
gcloud compute scp $CREDS_PATH "$($INSTANCE_NAME):/home/frank/nexus/shared/credentials.json" --zone=$ZONE

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
Set-Content -Path ".nexus_env" -Value "TARGET_VM=$INSTANCE_NAME`nTARGET_ZONE=$ZONE" -Encoding Ascii
Write-Host "Success! Local clasp is now securely linked to your Google account and restricted to the frontend/ directory." -ForegroundColor Green

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host "             Provisioning Complete!                 " -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host "Your server is ready."
Write-Host "Next steps (See INSTRUCTIONS.md):"
Write-Host "1. Transfer your credentials.json to the VM."
Write-Host "2. Run scripts\deploy.ps1 to push the code and start the backend.`n"