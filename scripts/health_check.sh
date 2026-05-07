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
    echo -e "${GREEN}[PASS] Apps Script Frontend...${NC}"
else
    echo -e "${RED}[FAIL] Apps Script Frontend...${NC}"
fi

IFS=$'\n' read -r -d '' -a vms < <( gcloud compute instances list --format="value(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)" && printf '\0' )

read -r -d '' PAYLOAD << 'EOF' || true
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
EOF

for vm in "${vms[@]}"; do
    if [ -z "$vm" ]; then continue; fi
    NAME=$(echo "$vm" | awk '{print $1}')
    ZONE=$(echo "$vm" | awk '{print $2}')
    STATUS=$(echo "$vm" | awk '{print $3}')
    IP=$(echo "$vm" | awk '{print $4}')

    echo -e "\n------------------------------------------------------------------------------"
    echo -e "${CYAN}VM: $NAME | Zone: $ZONE | IP: $IP | [$STATUS]${NC}"

    if curl -s -m 5 -f -o /dev/null "http://$IP:8000/openapi.json"; then
        echo -e "  ├── API Endpoint (Port 8000) : ${GREEN}[PASS] HTTP 200 OK${NC}"
    else
        echo -e "  ├── API Endpoint (Port 8000) : ${RED}[FAIL] Timeout or unreachable${NC}"
    fi

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
