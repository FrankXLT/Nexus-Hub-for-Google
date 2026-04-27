#!/bin/bash
# setup.sh - Idempotent provisioning script for Ubuntu VM
# Nexus Hub for Google

set -e

# Error Trap Function
trap_error() {
    local error_msg="$1"
    local instruction_ref="$2"
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] FAILURE: $error_msg" >> setup_diagnostics.log
    
    if [ -f ".env" ]; then
        # Load env vars safely
        export $(grep -v '^#' .env | xargs)
        if [ -n "$NEXUS_WEBHOOK_URL" ]; then
            curl -s -X POST -H "Content-Type: application/json" -d "{\"title\":\"Nexus Hub Provisioning Failure\",\"message\":\"$error_msg\"}" "$NEXUS_WEBHOOK_URL" > /dev/null || true
        fi
    fi
    
    echo -e "\n[!] FAILURE: $error_msg"
    if [ -n "$instruction_ref" ]; then
        echo -e "Please review [INSTRUCTIONS.md](./INSTRUCTIONS.md) -> $instruction_ref\n"
    fi
    exit 1
}

handle_error() {
    trap_error "An unexpected error occurred on line $1." "General Setup"
}
trap 'handle_error $LINENO' ERR

echo "======================================="
echo "Starting Nexus Hub VM Provisioning..."
echo "======================================="

# Checkpoints
if [ ! -f ".env" ]; then
    trap_error ".env file not found." "Phase 0, Step 2"
fi

if [ ! -f "credentials.json" ]; then
    trap_error "credentials.json not found." "Phase 0, Step 3"
fi

echo "Updating package lists..."
sudo apt-get update -y || trap_error "Failed to update apt packages." "Phase 1"

# 1. Install Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh || trap_error "Failed to download Docker install script." "Phase 1"
    sudo sh get-docker.sh || trap_error "Failed to execute Docker install script." "Phase 1"
    rm get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker installed."
else
    echo "Docker is already installed."
fi

if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose Plugin..."
    sudo apt-get install -y docker-compose-plugin || trap_error "Failed to install Docker Compose." "Phase 1"
    echo "Docker Compose installed."
else
    echo "Docker Compose is already installed."
fi

# Assert Docker is running
docker info &> /dev/null || trap_error "Docker daemon is not running or accessible." "Phase 1"

# 2. Install Node.js
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - || trap_error "Failed to setup Node.js repo." "Phase 1"
    sudo apt-get install -y nodejs || trap_error "Failed to install Node.js." "Phase 1"
    echo "Node.js installed."
else
    echo "Node.js is already installed."
fi

# 3. Install @google/clasp
if ! command -v clasp &> /dev/null; then
    echo "Installing @google/clasp..."
    sudo npm install -g @google/clasp || trap_error "Failed to install clasp." "Phase 1"
    echo "@google/clasp installed."
else
    echo "@google/clasp is already installed."
fi

# Ensure Python3 and pip are available (required for migrations)
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt-get install -y python3 python3-pip || trap_error "Failed to install Python3." "Phase 1"
else
    echo "Python3 is already installed."
fi

# 4. Install Diagnostic Watchdog Cron Job
echo "Configuring Diagnostic Watchdog Cron Job..."
PROJECT_DIR=$(pwd)
CRON_JOB="*/15 * * * * cd $PROJECT_DIR && docker compose run --rm nexus-sync-engine python3 diagnostics.py"
(crontab -l 2>/dev/null | grep -v "diagnostics.py"; echo "$CRON_JOB") | crontab - || trap_error "Failed to install cron job." "Phase 1"
echo "Cron job installed: runs every 15 minutes."

echo "======================================="
echo "PROVISIONING COMPLETE"
echo "======================================="
echo "ACTION REQUIRED: You must manually authenticate clasp to deploy to Google Apps Script."
echo "1. On your local machine, run: clasp login"
echo "2. Copy the contents of your local ~/.clasprc.json file."
echo "3. On this VM, create a new file at ~/.clasprc.json and paste the copied contents."
echo "   (or create it in the project root if you prefer to use a local clasp configuration)"
echo "4. Ensure the file has strict permissions: chmod 600 ~/.clasprc.json"
echo "======================================="
