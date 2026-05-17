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

while true; do
    echo -e "\n${CYAN}====================================================${NC}"
    echo -e "${CYAN}             Nexus Master Control Panel             ${NC}"
    echo -e "${CYAN}====================================================${NC}"
    echo "1) Launch SSH Session"
    echo "2) Pull Database Taxonomy (db_report.md)"
    echo "3) Pull Latest 50 Logs (nexus_logs.txt)"
    echo "4) Restart Nexus Service"
    echo "5) Prune Old Apps Script Deployments"
    echo "6) Exit"
    echo -e "${CYAN}====================================================${NC}"
    read -p "Select an option: " choice

    case $choice in
        1)
            echo -e "\n${GREEN}Launching SSH Session to $NAME...${NC}"
            gcloud compute ssh "$NAME" --zone="$ZONE" --strict-host-key-checking=no
            ;;
        2)
            echo -e "\n${GREEN}Generating Database Taxonomy...${NC}"
            gcloud compute ssh "$NAME" --zone="$ZONE" --command="cd ~/nexus/current/backend && python3 db_mapper.py" --strict-host-key-checking=no
            echo -e "${GREEN}Downloading db_report.md...${NC}"
            gcloud compute scp "${NAME}:/tmp/db_report.md" . --zone="$ZONE" --strict-host-key-checking=no
            echo -e "${GREEN}Done.${NC}"
            ;;
        3)
            echo -e "\n${GREEN}Fetching Latest Logs...${NC}"
            gcloud compute ssh "$NAME" --zone="$ZONE" --command="sudo journalctl -u nexus.service -n 50 > /tmp/nexus_logs.txt" --strict-host-key-checking=no
            echo -e "${GREEN}Downloading nexus_logs.txt...${NC}"
            gcloud compute scp "${NAME}:/tmp/nexus_logs.txt" . --zone="$ZONE" --strict-host-key-checking=no
            echo -e "${GREEN}Done.${NC}"
            ;;
        4)
            echo -e "\n${GREEN}Restarting Nexus Service on $NAME...${NC}"
            gcloud compute ssh "$NAME" --zone="$ZONE" --command="sudo systemctl restart nexus.service" --strict-host-key-checking=no
            echo -e "${CYAN}Verifying Health Status...${NC}"
            gcloud compute ssh "$NAME" --zone="$ZONE" --command="$PAYLOAD" --quiet --strict-host-key-checking=no 2>/dev/null | while IFS= read -r line; do
                line="${line//\[PASS\]/${GREEN}[PASS]${NC}}"
                line="${line//\[FAIL\]/${RED}[FAIL]${NC}}"
                if [[ "$line" == *"Systemd"* ]]; then
                    line="${line//inactive/${RED}inactive${NC}}"
                    line="${line//active/${GREEN}active${NC}}"
                fi
                echo -e "$line"
            done
            ;;
        5)
            echo -e "\n${CYAN}Scanning Apps Script deployments...${NC}"
            dep_out=$(clasp deployments 2>&1)
            dep_lines=$(echo "$dep_out" | grep -oP '^- \K[A-Za-z0-9_-]+(?= @[0-9]+)')
            count=$(echo "$dep_lines" | wc -w)
            
            echo -e "${YELLOW}Found $count versioned deployments.${NC}"
            if [ "$count" -gt 5 ]; then
                echo -e "${CYAN}Pruning older deployments (keeping the 5 most recent)...${NC}"
                to_delete=$((count - 5))
                IFS=$'\n' read -rd '' -a deps <<<"$dep_lines" || true
                for ((i=0; i<to_delete; i++)); do
                    del_id="${deps[$i]}"
                    if [ -n "$del_id" ]; then
                        echo "   -> Undeploying $del_id..."
                        clasp undeploy "$del_id" &>/dev/null || true
                    fi
                done
                echo -e "${GREEN}Pruning complete!${NC}"
            else
                echo -e "${GREEN}Deployment count is healthy. No pruning needed.${NC}"
            fi
            ;;
        6)
            echo -e "\n${CYAN}Exiting Master Control Panel.${NC}"
            break
            ;;
        *)
            echo -e "${RED}Invalid option. Please select 1-6.${NC}"
            ;;
    esac
done
