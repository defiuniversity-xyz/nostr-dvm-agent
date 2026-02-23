#!/usr/bin/env bash
set -euo pipefail

# Deploy the sats.ai DVM agent to a Google Cloud Compute Engine instance.
# Usage: ./deploy-backend.sh <INSTANCE_IP>
#
# Prerequisites:
#   - SSH access to the instance configured via gcloud or ~/.ssh/config
#   - Docker installed on the instance
#   - .env file at /opt/dvm-agent/.env on the instance

INSTANCE="${1:?Usage: deploy-backend.sh <INSTANCE_IP>}"
REMOTE_DIR="/opt/dvm-agent"

echo "==> Syncing source code to ${INSTANCE}:${REMOTE_DIR}"
rsync -avz --exclude '__pycache__' --exclude '.venv' --exclude '*.db' \
    -e ssh . "${INSTANCE}:${REMOTE_DIR}/app/"

echo "==> Building Docker image on remote"
ssh "${INSTANCE}" "cd ${REMOTE_DIR}/app && docker build -t dvm-agent:latest ."

echo "==> Restarting systemd service"
ssh "${INSTANCE}" "sudo systemctl restart dvm-agent"

echo "==> Checking service status"
ssh "${INSTANCE}" "sudo systemctl status dvm-agent --no-pager"

echo "==> Deploy complete"
