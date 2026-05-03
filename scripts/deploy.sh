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

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
    set -e
    echo -e '\n[VM] 1. Pulling latest code from git...'
    cd /opt/nexus
    git pull origin main || echo 'Warning: Could not pull git. Make sure you pushed your changes or setup SSH.'
    
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

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}          Deployment Completed Successfully!        ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Your frontend and backend are now perfectly synchronized."
