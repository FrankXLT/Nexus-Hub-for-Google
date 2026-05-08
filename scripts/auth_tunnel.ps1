# scripts/auth_tunnel.ps1
$ErrorActionPreference = "Stop"
$env:CLOUDSDK_COMPUTE_USE_OPENSSH = "1"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "           Nexus Auth Tunnel Script                 " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

if (-not (Test-Path ".nexus_env")) {
    Write-Host "Error: .nexus_env file not found." -ForegroundColor Red
    exit
}

$TARGET_VM = (Get-Content .nexus_env | Where-Object { $_ -match "^TARGET_VM=" }) -replace "^TARGET_VM=",""
$TARGET_ZONE = (Get-Content .nexus_env | Where-Object { $_ -match "^TARGET_ZONE=" }) -replace "^TARGET_ZONE=",""

Write-Host "Checking for backend code on VM..."
$null = gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE --command="if [ ! -d `$HOME/nexus/current/backend ]; then exit 1; fi"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Backend code not found on VM. You must run the deploy script before authenticating." -ForegroundColor Red
    exit
}

Write-Host "`nAn SSH tunnel is opening, please wait..." -ForegroundColor Yellow
Write-Host "When the link appears, please use ctrl+click to open your browser and authorize. " -NoNewline -ForegroundColor Yellow

$authCommand = "sudo fuser -k 8080/tcp >/dev/null 2>&1 ; cd `$HOME/nexus/current/backend && source venv/bin/activate && pip install google-auth-oauthlib google-api-python-client --quiet && python3 -u auth.py"
gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE --strict-host-key-checking=no --ssh-flag="-L 8080:localhost:8080" --command="$authCommand"