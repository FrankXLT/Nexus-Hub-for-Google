#!/bin/bash
# scripts/auth_tunnel.sh
# Secure Auth Tunnel for Nexus

set -e
set -o pipefail

# Color Codes
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}           Nexus Auth Tunnel Script                 ${NC}"
echo -e "${CYAN}====================================================${NC}"

if [ ! -f ".nexus_env" ]; then
    echo -e "${RED}Error: .nexus_env file not found.${NC}"
    exit 1
fi

TARGET_VM=$(grep "^TARGET_VM=" .nexus_env | cut -d'=' -f2)
TARGET_ZONE=$(grep "^TARGET_ZONE=" .nexus_env | cut -d'=' -f2)

echo -e "\n${YELLOW}An SSH tunnel is opening. When prompted, click the localhost link to authorize the application.${NC}"

gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE --ssh-flag="-L 8080:localhost:8080" --command="cd /home/frank/nexus/current/backend && source venv/bin/activate && pip install google-auth-oauthlib google-api-python-client && python3 auth.py"