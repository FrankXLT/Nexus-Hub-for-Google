#!/bin/bash
# scripts/deploy.sh
# Verbose CI/CD Deployment Script for Nexus

set -e
set -o pipefail

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

trap 'echo -e "\n${RED}Deployment failed! Please check the logs above.${NC}"' ERR

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}       Nexus for Google One-Click Deployment Wizard        ${NC}"
echo -e "${CYAN}====================================================${NC}"

if [ ! -f ".nexus_env" ]; then
    echo -e "${RED}Error: .nexus_env file not found.${NC}"
    exit 1
fi
TARGET_VM=$(grep "^TARGET_VM=" .nexus_env | cut -d'=' -f2)
TARGET_ZONE=$(grep "^TARGET_ZONE=" .nexus_env | cut -d'=' -f2)

read -p "Deploying to $TARGET_VM. Press Enter to confirm, or type 'list' to choose a different VM: " confirm_vm
if [ "$confirm_vm" == "list" ]; then
    echo "Fetching existing VMs..."
    IFS=$'\n' read -r -d '' -a vms < <( gcloud compute instances list --format="value(name,zone,status)" && printf '\0' )
    for i in "${!vms[@]}"; do
        echo "[$i] ${vms[$i]}"
    done
    read -p "Select VM number: " vmIdx
    SELECTED_VM="${vms[$vmIdx]}"
    TARGET_VM=$(echo "$SELECTED_VM" | awk '{print $1}')
    TARGET_ZONE=$(echo "$SELECTED_VM" | awk '{print $2}')
    cat > .nexus_env <<EOF
TARGET_VM=$TARGET_VM
TARGET_ZONE=$TARGET_ZONE
EOF
fi

INSTANCE_NAME=$TARGET_VM
ZONE=$TARGET_ZONE

echo "Fetching git branches..."
git fetch origin
branches=($(git branch -r | grep "origin/" | sed 's/.*origin\///'))
for i in "${!branches[@]}"; do
    echo "[$i] ${branches[$i]}"
done
read -p "Select branch number: " bIdx
SELECTED_BRANCH=${branches[$bIdx]}

if [[ "$INSTANCE_NAME" == *"prod"* && "$SELECTED_BRANCH" != "main" ]]; then
    read -p "Warning: Deploying non-main branch to prod! Continue? (Y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

git checkout $SELECTED_BRANCH
git pull origin $SELECTED_BRANCH

read -p "Backup remote SQLite database? (Y/n): " doBackup
if [[ ! "$doBackup" =~ ^[Nn]$ ]]; then
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="mkdir -p /home/frank/nexus/shared/backups && cp /home/frank/nexus/shared/data/nexus.db /home/frank/nexus/shared/backups/nexus_\$(date +%Y%m%d_%H%M%S).db || echo 'No DB to backup yet.'"
fi

echo -e "\n${YELLOW}[1/2] Syncing Serverless Frontend (Google Apps Script)...${NC}"
echo -e "Executing 'clasp push' to upload local HTML/JS/GS files to your Google Account."
if command -v clasp &> /dev/null; then
    clasp push
    echo -e "${GREEN}--> Apps Script UI synced successfully!${NC}"
else
    echo -e "${RED}Error: clasp is not installed. Please install it globally (npm install -g @google/clasp).${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[2/2] Deploying Backend to Google Cloud VM...${NC}"
echo -e "Connecting securely via SSH to pull updates, sync dependencies, and restart the daemon."

ENV_EXISTS=$(gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="if [ -f /home/frank/nexus/shared/.env ]; then echo 'YES'; else echo 'NO'; fi" 2>/dev/null | tr -d '\r')

if [ "$ENV_EXISTS" = "NO" ]; then
    echo -e "\n${RED}*** ACTION REQUIRED: shared/.env FILE MISSING ***${NC}"
    echo "Please provide the following configuration values:"
    read -p "NEXUS_HMAC_SECRET (type a highly unique, secure passphrase): " NEXUS_HMAC_SECRET
    read -p "NEXUS_API_KEY (Your Gemini API Key): " NEXUS_API_KEY
    read -p "NEXUS_WEBHOOK_URL (The permanent /exec URL for Apps Script): " NEXUS_WEBHOOK_URL

    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        mkdir -p /home/frank/nexus/shared
        echo \"NEXUS_HMAC_SECRET=\$NEXUS_HMAC_SECRET\" > /home/frank/nexus/shared/.env
        echo \"NEXUS_API_KEY=\$NEXUS_API_KEY\" >> /home/frank/nexus/shared/.env
        echo \"NEXUS_WEBHOOK_URL=\$NEXUS_WEBHOOK_URL\" >> /home/frank/nexus/shared/.env
        echo 'shared/.env file generated successfully.'
    "
else
    NEXUS_HMAC_SECRET=$(gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="grep '^NEXUS_HMAC_SECRET=' /home/frank/nexus/shared/.env | cut -d'=' -f2" 2>/dev/null | tr -d '\r')
fi

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
    set -e
    RELEASE_DIR=\"releases/\$(date +%Y%m%d_%H%M%S)\"
    FULL_RELEASE_DIR=\"/home/frank/nexus/\$RELEASE_DIR\"
    
    echo -e '\n[VM] 1. Preparing directories...'
    mkdir -p /home/frank/nexus/shared/data
    mkdir -p /home/frank/nexus/shared/backups
    mkdir -p /home/frank/nexus/releases
    
    echo -e '\n[VM] 2. Cloning code into new release directory...'
    git clone --branch $SELECTED_BRANCH https://github.com/FrankXLT/Nexus-for-Google.git \$FULL_RELEASE_DIR
    
    echo -e '\n[VM] 3. Activating Python Virtual Environment...'
    cd \$FULL_RELEASE_DIR/backend
    python3 -m venv venv
    source venv/bin/activate
    
    echo -e '\n[VM] 4. Installing dependencies via pip...'
    pip install -r requirements.txt
    
    echo -e '\n[VM] 5. Setting up Symlinks...'
    ln -s /home/frank/nexus/shared/data/nexus.db \$FULL_RELEASE_DIR/backend/nexus.db
    ln -s /home/frank/nexus/shared/.env \$FULL_RELEASE_DIR/backend/.env
    ln -s /home/frank/nexus/shared/credentials.json \$FULL_RELEASE_DIR/backend/credentials.json
    ln -s /home/frank/nexus/shared/token.json \$FULL_RELEASE_DIR/backend/token.json
    
    echo -e '\n[VM] 6. Running SQLite3 database migrations...'
    python3 db_init.py
    
    echo -e '\n[VM] 7. Updating main symlink...'
    ln -sfn \$FULL_RELEASE_DIR /home/frank/nexus/current
    
    echo -e '\n[VM] 8. Restarting the FastAPI systemd daemon...'
    sudo systemctl daemon-reload
    sudo systemctl restart nexus.service
    
    echo -e '\n[VM] Deployment sequence completed securely.'
"

VM_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null | tr -d '\r')
NEXUS_VM_URL="http://${VM_IP}:8000"

clear
echo -e "\n${RED}====================================================${NC}"
echo -e "${RED}                 ACTION REQUIRED                    ${NC}"
echo -e "${RED}====================================================${NC}"
echo -e "NEXUS_HMAC_SECRET: ${YELLOW}$NEXUS_HMAC_SECRET${NC}"
echo -e "NEXUS_VM_URL:      ${YELLOW}$NEXUS_VM_URL${NC}"
echo -e "\nPlease copy the values above. In a moment, your browser will open the Apps Script Editor. You MUST immediately go to: Project Settings (Gear Icon) -> Script Properties -> Add Script Property. Add NEXUS_HMAC_SECRET and NEXUS_VM_URL."
echo ""
read -p "Press Enter to open the Editor..."
clasp open