#!/bin/bash
# update.sh - CI/CD Executor for Nexus Hub
# Nexus Hub for Google

set -e

echo "======================================="
echo "Starting Nexus Hub Update Process..."
echo "======================================="

# 1. Gracefully stop docker containers
echo "Stopping Docker containers..."
if [ -f "docker-compose.yml" ]; then
    docker compose down
else
    echo "No docker-compose.yml found, skipping container stop."
fi

# 2. Pull latest changes from main branch
echo "Pulling latest changes from origin main..."
git pull origin main

# 3. Execute any Python files found in /migrations directory
if [ -d "migrations" ]; then
    echo "Checking for migrations..."
    # Execute python migrations in sorted order
    shopt -s nullglob
    for migration in migrations/*.py; do
        echo "Executing migration: $migration..."
        python3 "$migration"
    done
    shopt -u nullglob
else
    echo "No /migrations directory found. Skipping migrations."
fi

# 4. Run clasp push --force
echo "Deploying frontend to Google Apps Script..."
clasp push --force

# 5. Restart the containers
echo "Restarting Docker containers..."
if [ -f "docker-compose.yml" ]; then
    docker compose up -d
else
    echo "No docker-compose.yml found, skipping container start."
fi

echo "======================================="
echo "Update process completed successfully!"
echo "======================================="