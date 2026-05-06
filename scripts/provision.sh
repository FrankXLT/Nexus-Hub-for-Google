#!/bin/bash
# scripts/provision.sh
# Interactive Zero-Touch Provisioner for Nexus

set -e
set -o pipefail

# Color Codes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}    Welcome to Nexus for Google Provisioning Wizard    ${NC}"
echo -e "${CYAN}====================================================${NC}"
echo -e "This script will automatically configure your Google Cloud project,"
echo -e "enable the necessary APIs, and build your backend server."
echo ""

echo -e "${CYAN}Prerequisite: Google Cloud CLI${NC}"
echo -e "${YELLOW}Please ensure you have installed the Google Cloud CLI (gcloud).${NC}"
echo -e "${YELLOW}Download from: https://cloud.google.com/sdk/docs/install${NC}"
read -p "Press [Enter] when you have installed gcloud and run 'gcloud auth login'..."

# Verify gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: Google Cloud CLI (gcloud) is not installed.${NC}"
    exit 1
fi

echo -e "\n${CYAN}Prerequisite: Google Cloud Project & Billing${NC}"
echo -e "${YELLOW}1. Go to https://console.cloud.google.com/${NC}"
echo -e "${YELLOW}2. Create a new project (e.g., 'Nexus').${NC}"
echo -e "${YELLOW}3. Go to the Billing menu and link a credit card.${NC}"
read -p "Press [Enter] when your project is created and billing is enabled..."

read -p "Please enter your Google Cloud Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No Google Cloud Project ID provided.${NC}"
    exit 1
fi
gcloud config set project "$PROJECT_ID"

echo -e "Do you want to:"
echo -e "1) Create a NEW Nexus Environment"
echo -e "2) Configure an EXISTING one"
read -p "Select option (1 or 2): " ENV_OPTION

if [ "$ENV_OPTION" == "2" ]; then
    echo -e "Fetching existing VMs..."
    IFS=$'\n' read -r -d '' -a vms < <( gcloud compute instances list --format="value(name,zone,status)" --project="$PROJECT_ID" && printf '\0' )
    if [ ${#vms[@]} -eq 0 ]; then
        echo -e "${RED}No VMs found.${NC}"
        exit 1
    fi
    for i in "${!vms[@]}"; do
        echo "[$i] ${vms[$i]}"
    done
    read -p "Select VM number: " vmIdx
    SELECTED_VM="${vms[$vmIdx]}"
    INSTANCE_NAME=$(echo "$SELECTED_VM" | awk '{print $1}')
    ZONE=$(echo "$SELECTED_VM" | awk '{print $2}')
    ENV_LABEL=${INSTANCE_NAME#nexus-vm-}
else
    ENV_OPTION="1"
    ZONE="us-central1-f"
    read -p "Enter the Environment Label (e.g., dev, staging, prod): " ENV_LABEL
    if [ -z "$ENV_LABEL" ]; then
        ENV_LABEL="dev"
    fi
    INSTANCE_NAME="nexus-vm-$ENV_LABEL"
fi

echo -e "Using Project: ${YELLOW}$PROJECT_ID${NC}"
echo -e "Using Zone:    ${YELLOW}$ZONE${NC}"
echo -e "Instance Name: ${YELLOW}$INSTANCE_NAME${NC}"
echo ""

read -p "Press [Enter] to begin the provisioning process..."

echo -e "\n${CYAN}[1/5] Enabling Google Workspace & AI APIs...${NC}"
echo -e "Please go to Google Cloud Console and enable the Drive and Gmail APIs."
read -p "Press Enter when complete..."
echo -e "Nexus needs permission to interact with your data. We are turning on the APIs for Gmail, Drive, Document AI, People, Tasks, and Pub/Sub."
gcloud services enable \
    gmail.googleapis.com \
    drive.googleapis.com \
    pubsub.googleapis.com \
    documentai.googleapis.com \
    people.googleapis.com \
    tasks.googleapis.com \
    compute.googleapis.com \
    --project=$PROJECT_ID
echo -e "${GREEN}APIs successfully enabled!${NC}"

echo -e "\n${CYAN}[2/5] Configuring Network Security...${NC}"
echo -e "Opening port 8000 so the Google Apps Script frontend can talk to our Python backend."
if gcloud compute firewall-rules describe nexus-allow-8000 &> /dev/null; then
    echo -e "${GREEN}Firewall rule 'nexus-allow-8000' already exists. Skipping.${NC}"
else
    gcloud compute firewall-rules create nexus-allow-8000 \
        --action=ALLOW \
        --rules=tcp:8000 \
        --source-ranges=0.0.0.0/0 \
        --target-tags=nexus-api \
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

if [ "$ENV_OPTION" == "1" ]; then
echo -e "We are spinning up an e2-micro instance. The VM will automatically run a startup script to install Python, create the virtual environment, and configure the background service."

# Create e2-micro VM with metadata startup script
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --tags=nexus-api \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata=startup-script='#!/bin/bash
echo ">>> Starting Nexus Bootstrap..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 git curl

echo ">>> Creating /home/frank/nexus directory..."
mkdir -p /home/frank/nexus/shared/data
mkdir -p /home/frank/nexus/shared/backups
chmod -R 777 /home/frank/nexus

echo ">>> Configuring systemd daemon for FastAPI..."
cat > /etc/systemd/system/nexus.service <<EOF
[Unit]
Description=Nexus FastAPI Backend
After=network.target

[Service]
User=root
WorkingDirectory=/home/frank/nexus/current/backend
Environment=PATH=/home/frank/nexus/current/backend/venv/bin
ExecStart=/home/frank/nexus/current/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable nexus.service
echo ">>> Bootstrap complete!"
'

fi

echo -e "\n${CYAN}[6/6] Uploading Credentials...${NC}"
CREDS_EXISTS=$(gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --quiet --command="if [ -f /home/frank/nexus/shared/credentials.json ]; then echo 'YES'; else echo 'NO'; fi" 2>/dev/null | tr -d '\r')

if [ "$CREDS_EXISTS" = "YES" ]; then
    echo -e "${GREEN}Credentials already found on VM, skipping upload.${NC}"
else
    read -p "Please enter the full local path to your downloaded credentials.json file: " CREDS_PATH
    if [ ! -f "$CREDS_PATH" ]; then
        echo -e "${RED}Error: credentials.json not found at $CREDS_PATH${NC}"
        exit 1
    fi

    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --quiet --command="mkdir -p /home/frank/nexus/shared"
    gcloud compute scp "$CREDS_PATH" $INSTANCE_NAME:/home/frank/nexus/shared/credentials.json --zone=$ZONE --quiet
fi

echo -e "\n${CYAN}Apps Script Initialization${NC}"
UPPER_ENV=$(echo "$ENV_LABEL" | tr '[:lower:]' '[:upper:]')
echo -e "${CYAN}Please name your Apps Script project: 'Nexus for Google - [$UPPER_ENV]'${NC}"
echo -e "${YELLOW}Please open the Google Apps Script Editor for your project.${NC}"
echo -e "${YELLOW}Click the Gear Icon (Project Settings) on the left sidebar.${NC}"
echo -e "${YELLOW}Under 'IDs', copy the Script ID.${NC}"
read -p "Please paste your Script ID here: " SCRIPT_ID

cat > .clasp.json <<EOF
{"scriptId":"$SCRIPT_ID","rootDir":"frontend/"}
EOF
cat > .nexus_env <<EOF
TARGET_VM=$INSTANCE_NAME
TARGET_ZONE=$ZONE
EOF
echo -e "${GREEN}Success! Local clasp is now securely linked to your Google account and restricted to the frontend/ directory.${NC}"

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}             Provisioning Complete!                 ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Your server is ready."
echo -e "Next steps (See INSTRUCTIONS.md):"
echo -e "1. Run scripts/deploy.sh to push the code and start the backend."
echo -e "2. Run scripts/auth_tunnel.sh to authenticate the server."
echo ""echo -e "1. Run scripts/deploy.sh to push the code and start the backend."
echo -e "2. Run scripts/auth_tunnel.sh to authenticate the server."
echo ""