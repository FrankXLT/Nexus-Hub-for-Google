# scripts\test_api.ps1
$ErrorActionPreference = "Stop"

# ---> IMPORTANT: Update this to your VM's exact IP Address <---
$VM_IP = "34.55.85.170" 
$PORT = "8000"
$BASE_URL = "http://${VM_IP}:${PORT}"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      Nexus API Connection Tester       " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Test 1: Firewall & Web Server Check
Write-Host "`n[1/2] Testing Firewall & Web Server (Port $PORT)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BASE_URL/openapi.json" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "--> [PASS] Server is online and Firewall is OPEN!" -ForegroundColor Green
    }
} catch {
    Write-Host "--> [FAIL] Could not reach the server. Is the VM running and Firewall open?" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# Test 2: Internal API Logic Check
Write-Host "`n[2/2] Testing Nexus API Logic (/api/health/quota)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/health/quota" -Method Get -TimeoutSec 5
    Write-Host "--> [PASS] API is responding and executing Python code!" -ForegroundColor Green
    Write-Host "    Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor DarkGray
} catch {
    Write-Host "--> [FAIL] API endpoint failed. The Python backend might have crashed." -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nDiagnostics Complete!" -ForegroundColor Cyan