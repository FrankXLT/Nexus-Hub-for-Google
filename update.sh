#!/bin/bash
# update.sh - CI/CD Executor for Nexus Hub
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
            curl -s -X POST -H "Content-Type: application/json" -d "{\"title\":\"Nexus Hub Update Failure\",\"message\":\"$error_msg\"}" "$NEXUS_WEBHOOK_URL" > /dev/null || true
        fi
    fi
    
    echo -e "\n[!] FAILURE: $error_msg"
    if [ -n "$instruction_ref" ]; then
        echo -e "Please review [INSTRUCTIONS.md](./INSTRUCTIONS.md) -> $instruction_ref\n"
    fi
    exit 1
}

handle_error() {
    trap_error "An unexpected error occurred on line $1." "General Update"
}
trap 'handle_error $LINENO' ERR

echo "======================================="
echo "Starting Nexus Hub Update Process..."
echo "======================================="

# Checkpoints
if [ ! -f ".env" ]; then
    trap_error ".env file not found." "Phase 0, Step 2"
fi

if [ ! -f "credentials.json" ]; then
    trap_error "credentials.json not found." "Phase 0, Step 3"
fi

if [ ! -f "token.json" ]; then
    trap_error "token.json not found. Please authenticate first." "Phase 5, Step 2"
fi

if ! command -v docker &> /dev/null; then
    trap_error "Docker is not installed." "Phase 1, Step 1"
fi

# 1. Gracefully stop docker containers
echo "Stopping Docker containers..."
if [ -f "docker-compose.yml" ]; then
    docker compose down || trap_error "Failed to stop Docker containers." "Phase 6"
else
    trap_error "docker-compose.yml not found." "Phase 6"
fi

# 2. Pull latest changes from main branch
echo "Pulling latest changes from origin main..."
git pull origin main || trap_error "Failed to pull from git origin." "Phase 6"

# 3. Execute any Python files found in /migrations directory
if [ -d "migrations" ]; then
    echo "Checking for migrations..."
    shopt -s nullglob
    for migration in migrations/*.py; do
        echo "Executing migration: $migration..."
        docker compose run --rm nexus-api python3 "$migration" || trap_error "Migration $migration failed." "Phase 6"
    done
    shopt -u nullglob
else
    echo "No /migrations directory found. Skipping migrations."
fi

# 4. Run clasp push --force
echo "Deploying frontend to Google Apps Script..."
clasp push --force || trap_error "Failed to push clasp to Apps Script. Did you authenticate?" "Phase 4"

# 5. Restart the containers
echo "Restarting Docker containers..."
docker compose up -d || trap_error "Failed to start Docker containers." "Phase 6"

# Assert containers are up and return 200
echo "Waiting for Nexus API to become healthy..."
sleep 5
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health || echo "000")
if [ "$HTTP_STATUS" -ne 200 ]; then
    trap_error "Docker containers started, but API health check returned HTTP $HTTP_STATUS." "Phase 6"
fi

echo "======================================="
echo "Update process completed successfully!"
echo "======================================="
