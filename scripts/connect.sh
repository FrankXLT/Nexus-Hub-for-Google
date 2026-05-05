#!/bin/bash
# scripts/connect.sh
# Quick-Connect SSH script for Nexus

set -e
set -o pipefail

# Color Codes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}           Nexus Quick-Connect (SSH)                ${NC}"
echo -e "${CYAN}====================================================${NC}"

echo -e "Fetching existing VMs..."
IFS=$'\n' read -r -d '' -a vms < <( gcloud compute instances list --format="value(name,zone,status)" && printf '\0' )
if [ ${#vms[@]} -eq 0 ]; then
    echo -e "${RED}No VMs found.${NC}"
    exit 1
fi
for i in "${!vms[@]}"; do
    echo "[$i] ${vms[$i]}"
done
read -p "Select VM number: " vmIdx
SELECTED_VM="${vms[$vmIdx]}"
TARGET_VM=$(echo "$SELECTED_VM" | awk '{print $1}')
TARGET_ZONE=$(echo "$SELECTED_VM" | awk '{print $2}')

echo -e "\n${GREEN}Connecting to $TARGET_VM in $TARGET_ZONE...${NC}"
gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE