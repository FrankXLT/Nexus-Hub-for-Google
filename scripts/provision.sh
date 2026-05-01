#!/bin/bash
# scripts/provision.sh
# Zero-Touch Provisioner for Automated GCP VM Deployment

echo "Starting Nexus Hub Zero-Touch Provisioning..."

# Set project variables
PROJECT_ID=$(gcloud config get-value project)
ZONE="us-central1-f"
INSTANCE_NAME="nexus-hub-vm"

echo "Using Project: $PROJECT_ID, Zone: $ZONE, Instance: $INSTANCE_NAME"

# 1. Create Firewall Rule for TCP 8000
echo "Creating firewall rule for TCP 8000..."
gcloud compute firewall-rules create nexus-hub-allow-8000 \
    --action=ALLOW \
    --rules=tcp:8000 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=nexus-hub-api || echo "Firewall rule may already exist."

# 2. Create e2-micro VM with metadata startup script
echo "Provisioning e2-micro VM instance..."
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --tags=nexus-hub-api \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata=startup-script='#!/bin/bash
echo "Running Nexus Hub Startup Script..."
# System Updates
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 git curl

# Create App Directory
mkdir -p /opt/nexus-hub
chown -R $USER:$USER /opt/nexus-hub
cd /opt/nexus-hub

# Create Python virtual environment and install requirements
python3 -m venv venv
source venv/bin/activate
# Note: pip install commands will be run when code is deployed.
# Example: pip install -r requirements.txt

# Configure systemd daemon for FastAPI
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

echo "Startup script completed."
'

echo "Provisioning completed."
echo "You can now connect to your instance using: gcloud compute ssh $INSTANCE_NAME"
