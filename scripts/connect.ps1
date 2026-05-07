# scripts/connect.ps1
$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "           Nexus Quick-Connect (SSH)                " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

Write-Host "Fetching existing VMs..."
$vms = gcloud compute instances list --format="value(name,zone,status)"
$vmsList = @($vms)
if ($vmsList.Count -eq 0) {
    Write-Host "No VMs found." -ForegroundColor Red
    exit
}

for ($i=0; $i -lt $vmsList.Count; $i++) {
    Write-Host "[$i] $($vmsList[$i])"
}
$vmIdx = Read-Host "Select VM number"
$SELECTED_VM = $vmsList[[int]$vmIdx]
$parts = $SELECTED_VM -split "\s+"
$TARGET_VM = $parts[0]
$TARGET_ZONE = $parts[1]

Write-Host "`nConnecting to $TARGET_VM in $TARGET_ZONE..." -ForegroundColor Green
gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE --strict-host-key-checking=no