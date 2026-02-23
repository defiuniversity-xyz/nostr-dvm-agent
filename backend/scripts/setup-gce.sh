#!/usr/bin/env bash
set -euo pipefail

# One-time setup for a fresh Google Cloud Compute Engine instance.
# Run this script on the remote instance via SSH.

echo "==> Updating packages"
sudo apt-get update && sudo apt-get upgrade -y

echo "==> Installing Docker"
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker "$USER"

echo "==> Creating app directory"
sudo mkdir -p /opt/dvm-agent
sudo chown "$USER:$USER" /opt/dvm-agent

echo "==> Installing systemd service"
sudo tee /etc/systemd/system/dvm-agent.service > /dev/null <<'EOF'
[Unit]
Description=sats.ai DVM Agent
After=network.target docker.service
Requires=docker.service

[Service]
Restart=always
RestartSec=5
ExecStart=/usr/bin/docker run --rm --name dvm-agent --env-file /opt/dvm-agent/.env dvm-agent:latest
ExecStop=/usr/bin/docker stop dvm-agent

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable dvm-agent

echo "==> Setup complete"
echo "    1. Copy your .env file to /opt/dvm-agent/.env"
echo "    2. Run deploy-backend.sh to build and start the agent"
