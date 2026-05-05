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

# Configuration
INSTANCE_NAME="nexus-vm"
ZONE="us-central1-f"

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

ENV_EXISTS=$(gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="if [ -f /opt/nexus/backend/.env ]; then echo 'YES'; else echo 'NO'; fi" 2>/dev/null | tr -d '\r')

if [ "$ENV_EXISTS" = "NO" ]; then
    echo -e "\n${RED}*** ACTION REQUIRED: backend/.env FILE MISSING ***${NC}"
    echo "Please provide the following configuration values:"
    read -p "NEXUS_HMAC_SECRET (type a highly unique, secure passphrase): " NEXUS_HMAC_SECRET
    read -p "NEXUS_API_KEY (Your Gemini API Key): " NEXUS_API_KEY
    read -p "NEXUS_WEBHOOK_URL (The permanent /exec URL for Apps Script): " NEXUS_WEBHOOK_URL

    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
        mkdir -p /opt/nexus/backend
        echo \"NEXUS_HMAC_SECRET=\$NEXUS_HMAC_SECRET\" > /opt/nexus/backend/.env
        echo \"NEXUS_API_KEY=\$NEXUS_API_KEY\" >> /opt/nexus/backend/.env
        echo \"NEXUS_WEBHOOK_URL=\$NEXUS_WEBHOOK_URL\" >> /opt/nexus/backend/.env
        echo 'backend/.env file generated successfully.'
    "
else
    NEXUS_HMAC_SECRET=$(gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="grep '^NEXUS_HMAC_SECRET=' /opt/nexus/backend/.env | cut -d'=' -f2" 2>/dev/null | tr -d '\r')
fi

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
    set -e
    echo -e '\n[VM] 1. Pulling latest code from git...'
    cd /opt/nexus
    git pull origin development || echo 'Warning: Could not pull git. Make sure you pushed your changes or setup SSH.'
    
    echo -e '\n[VM] 2. Activating Python Virtual Environment...'
    source venv/bin/activate
    
    echo -e '\n[VM] 3. Installing dependencies via pip...'
    pip install -r requirements.txt
    
    echo -e '\n[VM] 4. Running SQLite3 database migrations...'
    python3 db_init.py
    
    echo -e '\n[VM] 5. Restarting the FastAPI systemd daemon...'
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
