# scripts/health_check.ps1
$ErrorActionPreference = "Continue"
$env:CLOUDSDK_COMPUTE_USE_OPENSSH = "1"

Clear-Host
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "             Nexus Fleet Health Dashboard           " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$claspOut = clasp deployments 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host '[PASS] Apps Script Frontend...' -ForegroundColor Green
} else {
    Write-Host '[FAIL] Apps Script Frontend...' -ForegroundColor Red
}

$vms = gcloud compute instances list --format="value(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)"
$vmList = @($vms)

$remotePayload = @'
NEXUS_ROOT="$HOME/nexus"
echo "▼ Critical Services"
svc_status=$(systemctl is-active nexus.service 2>/dev/null || echo "inactive")
echo "  ├── Systemd (nexus.service)  : $svc_status"

if [ -f "$NEXUS_ROOT/shared/data/nexus.db" ]; then
  db_size=$(ls -lh "$NEXUS_ROOT/shared/data/nexus.db" | awk '{print $5}')
  echo "  └── Main Database (nexus.db) : $db_size"
else
  echo "  └── Main Database (nexus.db) : [FAIL] Missing"
fi

echo ""
echo "▼ Database Backups"
if [ -d "$NEXUS_ROOT/shared/backups" ]; then
  ls -lh "$NEXUS_ROOT/shared/backups" | grep "nexus_backup" | awk '{print "  ├── "$9" : "$5" ("$6" "$7" "$8")"}' || echo "  └── [PASS] Clean - No backups yet"
fi

echo ""
echo "▼ Offline Deployments (Orphans)"
if [ -d "$NEXUS_ROOT/releases" ]; then
  current_rel=$(readlink -f "$NEXUS_ROOT/current")
  ls -d "$NEXUS_ROOT/releases/"*/ 2>/dev/null | grep -v "$current_rel" | xargs -I {} stat -c "  ├── Release: %n : (%y)" {} | sed "s|$NEXUS_ROOT/releases/||g" | cut -d'.' -f1 || echo "  └── [PASS] Clean - Only current release exists"
fi
'@

foreach ($vm in $vmList) {
    if ([string]::IsNullOrWhiteSpace($vm)) { continue }
    $parts = $vm -split "\s+"
    $NAME = $parts[0]
    $ZONE = $parts[1]
    $STATUS = $parts[2]
    $IP = $parts[3]

    Write-Host "`n------------------------------------------------------------------------------"
    Write-Host "VM: $NAME | Zone: $ZONE | IP: $IP | [$STATUS]" -ForegroundColor Cyan

    try {
        $response = Invoke-WebRequest -Uri "http://$IP:8000/openapi.json" -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host '  ├── API Endpoint (Port 8000) : ' -NoNewline
            Write-Host '[PASS] HTTP 200 OK' -ForegroundColor Green
        } else {
            Write-Host '  ├── API Endpoint (Port 8000) : ' -NoNewline
            Write-Host '[FAIL] HTTP ' -NoNewline -ForegroundColor Red
            Write-Host $response.StatusCode -ForegroundColor Red
        }
    } catch {
        Write-Host '  ├── API Endpoint (Port 8000) : ' -NoNewline
        Write-Host '[FAIL] Timeout or unreachable' -ForegroundColor Red
    }

    if ($STATUS -eq "RUNNING") {
        $sshOut = gcloud compute ssh $NAME --zone=$ZONE --command="$remotePayload" --quiet --strict-host-key-checking=no 2>&1
        foreach ($line in $sshOut) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                Write-Host ""
                continue
            }
            if ($line -match '\[PASS\]') {
                $parts_l = $line -split '\[PASS\]', 2
                Write-Host $parts_l[0] -NoNewline
                Write-Host '[PASS]' -ForegroundColor Green -NoNewline
                Write-Host $parts_l[1]
            } elseif ($line -match '\[FAIL\]') {
                $parts_l = $line -split '\[FAIL\]', 2
                Write-Host $parts_l[0] -NoNewline
                Write-Host '[FAIL]' -ForegroundColor Red -NoNewline
                Write-Host $parts_l[1]
            } elseif ($line -match 'Systemd' -and $line -match 'inactive') {
                $parts_l = $line -split 'inactive', 2
                Write-Host $parts_l[0] -NoNewline
                Write-Host 'inactive' -ForegroundColor Red -NoNewline
                Write-Host $parts_l[1]
            } elseif ($line -match 'Systemd' -and $line -match 'active') {
                $parts_l = $line -split 'active', 2
                Write-Host $parts_l[0] -NoNewline
                Write-Host 'active' -ForegroundColor Green -NoNewline
                Write-Host $parts_l[1]
            } else {
                Write-Host $line
            }
        }
    }
}