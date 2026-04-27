#!/bin/bash
# setup.sh - Idempotent provisioning script for Ubuntu VM
# Nexus Hub for Google

set -e

echo "======================================="
echo "Starting Nexus Hub VM Provisioning..."
echo "======================================="

echo "Updating package lists..."
sudo apt-get update -y

# 1. Install Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker installed."
else
    echo "Docker is already installed."
fi

if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose Plugin..."
    sudo apt-get install -y docker-compose-plugin
    echo "Docker Compose installed."
else
    echo "Docker Compose is already installed."
fi

# 2. Install Node.js
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "Node.js installed."
else
    echo "Node.js is already installed."
fi

# 3. Install @google/clasp
if ! command -v clasp &> /dev/null; then
    echo "Installing @google/clasp..."
    sudo npm install -g @google/clasp
    echo "@google/clasp installed."
else
    echo "@google/clasp is already installed."
fi

# Ensure Python3 and pip are available (required for migrations)
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    sudo apt-get install -y python3 python3-pip
else
    echo "Python3 is already installed."
fi

# 4. Install Diagnostic Watchdog Cron Job
echo "Configuring Diagnostic Watchdog Cron Job..."
PROJECT_DIR=$(pwd)
CRON_JOB="*/15 * * * * cd $PROJECT_DIR && docker compose run --rm nexus-sync-engine python3 diagnostics.py"
(crontab -l 2>/dev/null | grep -v "diagnostics.py"; echo "$CRON_JOB") | crontab -
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