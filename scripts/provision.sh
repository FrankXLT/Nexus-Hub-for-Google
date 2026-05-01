#!/bin/bash
# scripts/provision.sh
# Interactive Zero-Touch Provisioner for Nexus Hub

set -e
set -o pipefail

# Color Codes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}    Welcome to the Nexus Hub Provisioning Wizard    ${NC}"
echo -e "${CYAN}====================================================${NC}"
echo -e "This script will automatically configure your Google Cloud project,"
echo -e "enable the necessary APIs, and build your backend server."
echo ""

# Verify gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: Google Cloud CLI (gcloud) is not installed.${NC}"
    echo -e "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No Google Cloud Project selected.${NC}"
    echo -e "Please run: ${YELLOW}gcloud config set project YOUR_PROJECT_ID${NC}"
    exit 1
fi

ZONE="us-central1-f"
INSTANCE_NAME="nexus-hub-vm"

echo -e "Using Project: ${YELLOW}$PROJECT_ID${NC}"
echo -e "Using Zone:    ${YELLOW}$ZONE${NC}"
echo -e "Instance Name: ${YELLOW}$INSTANCE_NAME${NC}"
echo ""

read -p "Press [Enter] to begin the provisioning process..."

echo -e "\n${CYAN}[1/5] Enabling Google Workspace & AI APIs...${NC}"
echo -e "Nexus Hub needs permission to interact with your data. We are turning on the APIs for Gmail, Drive, Document AI, People, Tasks, and Pub/Sub."
gcloud services enable \
    gmail.googleapis.com \
    drive.googleapis.com \
    pubsub.googleapis.com \
    documentai.googleapis.com \
    people.googleapis.com \
    tasks.googleapis.com \
    --project=$PROJECT_ID
echo -e "${GREEN}APIs successfully enabled!${NC}"

echo -e "\n${CYAN}[2/5] Configuring Network Security...${NC}"
echo -e "Opening port 8000 so the Google Apps Script frontend can talk to our Python backend."
if gcloud compute firewall-rules describe nexus-hub-allow-8000 &> /dev/null; then
    echo -e "${GREEN}Firewall rule 'nexus-hub-allow-8000' already exists. Skipping.${NC}"
else
    gcloud compute firewall-rules create nexus-hub-allow-8000 \
        --action=ALLOW \
        --rules=tcp:8000 \
        --source-ranges=0.0.0.0/0 \
        --target-tags=nexus-hub-api \
        --project=$PROJECT_ID
    echo -e "${GREEN}Firewall rule created!${NC}"
fi

echo -e "\n${CYAN}[3/5] Manual Step: OAuth Configuration${NC}"
echo -e "We need to set up the 'OAuth Consent Screen' so you can securely log into your own app."
echo -e "${YELLOW}Instructions:${NC}"
echo -e "1. Go to: https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
echo -e "2. Select 'Internal' (if using Google Workspace) or 'External' (if personal Gmail) and click Create."
echo -e "3. Fill in the required app names and emails."
echo -e "4. Skip adding scopes here, just save and continue."
echo ""
read -p "Press [Enter] when you have configured the Consent Screen..."

echo -e "\n${CYAN}[4/5] Manual Step: Generating Credentials${NC}"
echo -e "Now we need to create the exact 'key' (Client ID) that allows the Python server to authenticate."
echo -e "${YELLOW}Instructions:${NC}"
echo -e "1. Go to: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo -e "2. Click 'CREATE CREDENTIALS' > 'OAuth client ID'."
echo -e "3. Select 'Desktop app' for the Application type."
echo -e "4. Click Create, then DOWNLOAD the JSON file."
echo -e "5. Rename the downloaded file EXACTLY to: credentials.json"
echo ""
read -p "Press [Enter] when you have downloaded 'credentials.json' to your local machine..."

echo -e "\n${CYAN}[5/5] Provisioning the Virtual Machine (VM)...${NC}"
echo -e "We are spinning up an e2-micro instance. The VM will automatically run a startup script to install Python, create the virtual environment, and configure the background service."

# Create e2-micro VM with metadata startup script
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --tags=nexus-hub-api \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata=startup-script='#!/bin/bash
echo ">>> Starting Nexus Hub Bootstrap..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 git curl

echo ">>> Creating /opt/nexus-hub directory..."
mkdir -p /opt/nexus-hub
chmod 777 /opt/nexus-hub
cd /opt/nexus-hub

echo ">>> Cloning Nexus Hub repository from GitHub..."
git clone https://github.com/FrankXLT/Nexus-Hub-for-Google.git . || echo "Directory not empty, skipping clone."

echo ">>> Initializing Python Virtual Environment..."
python3 -m venv venv

echo ">>> Configuring systemd daemon for FastAPI..."
cat > /etc/systemd/system/nexus-hub.service <<EOF
[Unit]
Description=Nexus Hub FastAPI Backend
After=network.target

[Service]
User=root
WorkingDirectory=/opt/nexus-hub
Environment=PATH=/opt/nexus-hub/venv/bin
ExecStart=/opt/nexus-hub/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable nexus-hub.service
echo ">>> Bootstrap complete!"
'

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}             Provisioning Complete!                 ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Your server is booting up. It will take ~2 minutes to install Python."
echo -e "Next steps (See INSTRUCTIONS.md):"
echo -e "1. Transfer your credentials.json to the VM."
echo -e "2. Run scripts/deploy.sh to push the code and start the backend."
echo ""
