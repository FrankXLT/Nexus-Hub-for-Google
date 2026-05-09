#!/bin/bash
# scripts/auth_tunnel.sh
# Secure Auth Tunnel for Nexus

set -e
set -o pipefail
export CLOUDSDK_COMPUTE_USE_OPENSSH=1

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

echo -e "Checking for backend code on VM..."
if ! gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE --strict-host-key-checking=no --command="if [ ! -d \$HOME/nexus/current/backend ]; then exit 1; fi"; then
    echo -e "${RED}Error: Backend code not found on VM. You must run the deploy script before authenticating.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}An SSH tunnel is opening, please wait... When the link appears, please open your browser to the URL and authorize. ${NC}"

gcloud compute ssh $TARGET_VM --zone=$TARGET_ZONE --ssh-flag="-L 8080:localhost:8080" --command="sudo pkill -f auth.py >/dev/null 2>&1 ; sleep 2 ; cd \$HOME/nexus/current/backend && source venv/bin/activate && pip install google-auth-oauthlib google-api-python-client --quiet && python3 -u auth.py"