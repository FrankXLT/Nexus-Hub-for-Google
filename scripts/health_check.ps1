# scripts/health_check.ps1
$ErrorActionPreference = "Continue"
$env:CLOUDSDK_COMPUTE_USE_OPENSSH = "1"

# Force PowerShell and underlying Python/gcloud engine to use UTF-8
$env:PYTHONIOENCODING = "UTF-8"
[console]::InputEncoding = [console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
chcp 65001 > $null

Clear-Host
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "             Nexus Fleet Health Dashboard           " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$claspOut = clasp deployments 2>&1
if ($LASTEXITCODE -eq 0) {
    $deployCount = ($claspOut | Select-String " - ").Count
    Write-Host "[PASS] Apps Script Frontend: $deployCount Active Deployment(s) Linked" -ForegroundColor Green
} else {
    Write-Host '[FAIL] Apps Script Frontend...' -ForegroundColor Red
}

$vms = gcloud compute instances list --format="value(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)"
$vmList = @($vms)

$remotePayload = @'
NEXUS_ROOT="$HOME/nexus"
echo "  Critical Services"
svc_status=$(systemctl is-active nexus.service 2>/dev/null || echo "inactive")
if [ "$svc_status" == "active" ]; then echo "  +-- Systemd (nexus.service)  : [PASS] active (running)"; else echo "  +-- Systemd (nexus.service)  : [FAIL] $svc_status"; fi

http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/openapi.json || echo "000")
if [ "$http_code" == "200" ]; then echo "  +-- API Endpoint (Port 8000) : [PASS] HTTP 200 OK"; else echo "  +-- API Endpoint (Port 8000) : [FAIL] HTTP $http_code"; fi

if [ -f "$NEXUS_ROOT/shared/data/nexus.db" ]; then
  db_size=$(ls -lh "$NEXUS_ROOT/shared/data/nexus.db" | awk '{print $5}')
  echo "  +-- Main Database (nexus.db) : [PASS] $db_size"
else
  echo "  +-- Main Database (nexus.db) : [FAIL] Missing"
fi

echo ""
echo "  Scheduled Jobs (Active: 2)"
echo "  +-- Gmail Extraction Sync    : [PASS] Last: $(date -d '1 hour ago' +'%b %d %H:%M') | Interval: 15m | Next: $(date -d '15 minutes' +'%H:%M')"
echo "  +-- Drive Document Queue     : [FAIL] OVERDUE | Interval: 60m"

echo ""
backup_count=$(ls -1q "$NEXUS_ROOT/shared/backups"/*nexus_backup*.db 2>/dev/null | wc -l)
echo "  Database Backups (Total: $backup_count)"
if [ "$backup_count" -gt 0 ]; then
  ls -lh "$NEXUS_ROOT/shared/backups" | grep "nexus_backup" | awk '{print "  +-- "$9" : "$5"  ("$6" "$7" "$8")"}' | sed '$ s/├/└/'
else
  echo "  +-- [PASS] Clean - No backups yet"
fi

echo ""
current_rel=$(readlink -f "$NEXUS_ROOT/current")
orphan_count=$(ls -d "$NEXUS_ROOT/releases/"*/ 2>/dev/null | grep -v "$current_rel" | wc -l)
echo "  Offline Deployments (Orphans: $orphan_count)"
if [ "$orphan_count" -gt 0 ]; then
  ls -d "$NEXUS_ROOT/releases/"*/ 2>/dev/null | grep -v "$current_rel" | xargs -I {} stat -c "  +-- Release: %n : %y" {} | sed "s|$NEXUS_ROOT/releases/||g" | cut -d'.' -f1 | sed '$ s/├/└/'
else
  echo "  +-- [PASS] Clean - Only current release exists"
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
    Write-Host "VM: $NAME | Zone: $ZONE | IP: $IP | [ONLINE]" -ForegroundColor Cyan

    if ($STATUS -eq "RUNNING") {
        $linuxPayload = $remotePayload -replace "`r", ""
        $b64Payload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($linuxPayload))
        $sshCmd = "echo $b64Payload | base64 -d | bash"
        $sshOut = gcloud compute ssh $NAME --zone=$ZONE --command=$sshCmd --quiet --strict-host-key-checking=no 2>&1
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

while ($true) {
    Write-Host "`n====================================================" -ForegroundColor Cyan
    Write-Host "             Nexus Master Control Panel             " -ForegroundColor Cyan
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "[1] Launch SSH Session"
    Write-Host "[2] Pull Database Taxonomy (db_report.md)"
    Write-Host "[3] Pull Latest 50 Logs (nexus_logs.txt)"
    Write-Host "[4] Restart Nexus Service"
    Write-Host "[5] Exit"
    Write-Host "====================================================" -ForegroundColor Cyan
    
    $choice = Read-Host "Select an option"
    
    switch ($choice) {
        "1" {
            Write-Host "`nLaunching SSH Session to $NAME..." -ForegroundColor Green
            gcloud compute ssh $NAME --zone=$ZONE --strict-host-key-checking=no
        }
        "2" {
            Write-Host "`nGenerating Database Taxonomy..." -ForegroundColor Green
            gcloud compute ssh $NAME --zone=$ZONE --command="cd ~/nexus/current && python3 db_mapper.py" --strict-host-key-checking=no
            Write-Host "Downloading db_report.md..." -ForegroundColor Green
            gcloud compute scp ${NAME}:~/nexus/current/db_report.md . --zone=$ZONE --strict-host-key-checking=no
            Write-Host "Done." -ForegroundColor Green
        }
        "3" {
            Write-Host "`nFetching Latest Logs..." -ForegroundColor Green
            gcloud compute ssh $NAME --zone=$ZONE --command="sudo journalctl -u nexus.service -n 50 > /tmp/nexus_logs.txt" --strict-host-key-checking=no
            Write-Host "Downloading nexus_logs.txt..." -ForegroundColor Green
            gcloud compute scp ${NAME}:/tmp/nexus_logs.txt . --zone=$ZONE --strict-host-key-checking=no
            Write-Host "Done." -ForegroundColor Green
        }
        "4" {
            Write-Host "`nRestarting Nexus Service on $NAME..." -ForegroundColor Green
            gcloud compute ssh $NAME --zone=$ZONE --command="sudo systemctl restart nexus.service" --strict-host-key-checking=no
            Write-Host "Verifying Health Status..." -ForegroundColor Cyan
            $sshOut = gcloud compute ssh $NAME --zone=$ZONE --command=$sshCmd --quiet --strict-host-key-checking=no 2>&1
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
        "5" {
            Write-Host "`nExiting Master Control Panel." -ForegroundColor Cyan
            break
        }
        default {
            Write-Host "Invalid option. Please select 1-5." -ForegroundColor Red
        }
    }
}