#!/bin/bash
# scripts/deploy.sh
# CI/CD Deployment Script for Nexus Hub

set -e
set -o pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

trap 'echo -e "${RED}Deployment failed! Please check the logs above.${NC}"' ERR

echo -e "${YELLOW}Starting Nexus Hub CI/CD Deployment...${NC}"

# Configuration
INSTANCE_NAME="nexus-hub-vm"
ZONE="us-central1-f" # Modify this if your instance is in a different zone

# 1. Sync Apps Script UI Locally
echo -e "${GREEN}[1/2] Syncing Apps Script UI locally via clasp...${NC}"
if command -v clasp &> /dev/null; then
    clasp push
    echo -e "${GREEN}Apps Script UI synced successfully.${NC}"
else
    echo -e "${RED}Error: clasp is not installed. Please install it globally (npm install -g @google/clasp).${NC}"
    exit 1
fi

# 2. Deploy Backend to GCP VM
echo -e "${GREEN}[2/2] Connecting to GCP VM to deploy backend updates...${NC}"
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
    set -e
    echo '--> Pulling latest git updates...'
    cd /opt/nexus-hub
    git pull origin main
    
    echo '--> Activating virtual environment & installing pip dependencies...'
    source venv/bin/activate
    pip install -r requirements.txt
    
    echo '--> Executing database migrations...'
    python3 db_init.py
    
    echo '--> Restarting systemd service...'
    sudo systemctl restart nexus-hub.service
    echo '--> Backend successfully deployed and restarted.'
"

echo -e "${GREEN}Deployment completed successfully!${NC}"
