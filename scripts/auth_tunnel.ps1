# scripts/auth_tunnel.ps1
$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "           Nexus Auth Tunnel Script                 " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

if (-not (Test-Path ".nexus_env")) {
    Write-Host "Error: .nexus_env file not found." -ForegroundColor Red
    exit
}

$TARGET_VM = (Get-Content .nexus_env | Where-Object { $_ -match "^TARGET_VM=" }) -replace "^TARGET_VM=",""
$TARGET_ZONE = (Get-Content .nexus_env | Where-Object { $_ -match "^TARGET_ZONE=" }) -replace "^TARGET_ZONE=",""

Write-Host "`nAn SSH tunnel is opening. When prompted, click the localhost link to authorize the application." -ForegroundColor Yellow

gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE --ssh-flag="-L 8080:localhost:8080" --command="cd /home/frank/nexus/current/backend && source venv/bin/activate && pip install google-auth-oauthlib google-api-python-client && python3 auth.py"