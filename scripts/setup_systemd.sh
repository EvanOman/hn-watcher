#!/bin/bash

set -euo pipefail

# Get the absolute path of the repository directory (current directory)
REPO_DIR="$(pwd)"

# Get the current user
CURRENT_USER="${SUDO_USER:-$USER}"

SERVICE_NAME=hn_watcher
# Try to find uv in common locations
if command -v uv &> /dev/null; then
    SCRIPT_PATH=$(command -v uv)
else
    echo "Error: uv not found. Please install uv or modify this script to use pip"
    exit 1
fi

SERVICE_FILE=/etc/systemd/system/${SERVICE_NAME}.service
TIMER_FILE=/etc/systemd/system/${SERVICE_NAME}.timer

# Create systemd service file
cat <<EOF | sudo tee "$SERVICE_FILE" >/dev/null
[Unit]
Description=Run ${SERVICE_NAME}

[Service]
User=${CURRENT_USER}
Type=oneshot
WorkingDirectory=${REPO_DIR}
ExecStart=${SCRIPT_PATH} run -m hn_watcher 43243024
EOF

# Create systemd timer file
cat <<EOF | sudo tee "$TIMER_FILE" >/dev/null
[Unit]
Description=Timer for ${SERVICE_NAME}

[Timer]
OnCalendar=*:0/15
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload systemd configuration and start timer
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}.timer"

echo "Working directory set to: ${REPO_DIR}"