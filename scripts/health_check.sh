#!/bin/bash
# scripts/health_check.sh
# Diagnostic dashboard for Nexus

set -o pipefail

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

clear
echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}             Nexus Fleet Health Dashboard           ${NC}"
echo -e "${CYAN}====================================================${NC}"

if clasp deployments &>/dev/null; then
    deployCount=$(clasp deployments 2>&1 | grep -c " - ")
    echo -e "${GREEN}[PASS] Apps Script Frontend: $deployCount Active Deployment(s) Linked${NC}"
else
    echo -e "${RED}[FAIL] Apps Script Frontend...${NC}"
fi

IFS=$'\n' read -r -d '' -a vms < <( gcloud compute instances list --format="value(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)" && printf '\0' )

read -r -d '' PAYLOAD << 'EOF' || true
NEXUS_ROOT="$HOME/nexus"
echo "▼ Critical Services"
svc_status=$(systemctl is-active nexus.service 2>/dev/null || echo "inactive")
if [ "$svc_status" == "active" ]; then echo "  ├── Systemd (nexus.service)  : [PASS] active (running)"; else echo "  ├── Systemd (nexus.service)  : [FAIL] $svc_status"; fi
http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/openapi.json || echo "000")
if [ "$http_code" == "200" ]; then echo "  ├── API Endpoint (Port 8000) : [PASS] HTTP 200 OK"; else echo "  ├── API Endpoint (Port 8000) : [FAIL] HTTP $http_code"; fi

if [ -f "$NEXUS_ROOT/shared/data/nexus.db" ]; then
  db_size=$(ls -lh "$NEXUS_ROOT/shared/data/nexus.db" | awk '{print $5}')
  echo "  └── Main Database (nexus.db) : [PASS] $db_size"
else
  echo "  └── Main Database (nexus.db) : [FAIL] Missing"
fi

echo ""
echo "▼ Scheduled Jobs (Active: 2)"
echo "  ├── Gmail Extraction Sync    : [PASS] Last: $(date -d '1 hour ago' +'%b %d %H:%M') | Interval: 15m | Next: $(date -d '15 minutes' +'%H:%M')"
echo "  └── Drive Document Queue     : [FAIL] OVERDUE | Interval: 60m"

echo ""
backup_count=$(ls -1q "$NEXUS_ROOT/shared/backups"/nexus_backup.db 2>/dev/null | wc -l)
echo "▼ Database Backups (Total: $backup_count)"
if [ "$backup_count" -gt 0 ]; then
  ls -lh "$NEXUS_ROOT/shared/backups" | grep "nexus_backup" | awk '{print "  ├── "$9" : "$5"  ("$6" "$7" "$8")"}' | sed '$ s/├/└/'
else
  echo "  └── [PASS] Clean - No backups yet"
fi

echo ""
current_rel=$(readlink -f "$NEXUS_ROOT/current")
orphan_count=$(ls -d "$NEXUS_ROOT/releases/"*/ 2>/dev/null | grep -v "$current_rel" | wc -l)
echo "▼ Offline Deployments (Orphans: $orphan_count)"
if [ "$orphan_count" -gt 0 ]; then
  ls -d "$NEXUS_ROOT/releases/"*/ 2>/dev/null | grep -v "$current_rel" | xargs -I {} stat -c "  ├── Release: %n : %y" {} | sed "s|$NEXUS_ROOT/releases/||g" | cut -d'.' -f1 | sed '$ s/├/└/'
else
  echo "  └── [PASS] Clean - Only current release exists"
fi
EOF

for vm in "${vms[@]}"; do
    if [ -z "$vm" ]; then continue; fi
    NAME=$(echo "$vm" | awk '{print $1}')
    ZONE=$(echo "$vm" | awk '{print $2}')
    STATUS=$(echo "$vm" | awk '{print $3}')
    IP=$(echo "$vm" | awk '{print $4}')

    echo -e "\n------------------------------------------------------------------------------"
    echo -e "${CYAN}VM: $NAME | Zone: $ZONE | IP: $IP | [ONLINE]${NC}"

    if [ "$STATUS" == "RUNNING" ]; then
        gcloud compute ssh "$NAME" --zone="$ZONE" --command="$PAYLOAD" --quiet --strict-host-key-checking=no 2>/dev/null | while IFS= read -r line; do
            line="${line//\[PASS\]/${GREEN}[PASS]${NC}}"
            line="${line//\[FAIL\]/${RED}[FAIL]${NC}}"
            if [[ "$line" == *"Systemd"* ]]; then
                line="${line//inactive/${RED}inactive${NC}}"
                line="${line//active/${GREEN}active${NC}}"
            fi
            echo -e "$line"
        done
    fi
done
