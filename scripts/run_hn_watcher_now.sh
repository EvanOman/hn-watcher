#!/bin/bash

set -euo pipefail

SERVICE_NAME="hn_watcher"

# Define color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Attempting to trigger ${YELLOW}${SERVICE_NAME}${BLUE} service to run now...${NC}"

# Check if the service exists
if ! systemctl list-unit-files | grep -q "${SERVICE_NAME}.service"; then
    echo -e "${RED}Error: ${SERVICE_NAME}.service does not exist.${NC}"
    exit 1
fi

# Trigger the service to run immediately
echo -e "${YELLOW}Running: sudo systemctl start ${SERVICE_NAME}.service${NC}"
sudo systemctl start "${SERVICE_NAME}.service"

# Check if the service started successfully
if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    echo -e "${GREEN}Service ${SERVICE_NAME} has been triggered successfully.${NC}"
else
    # For oneshot services, they might complete too quickly to show as active
    echo -e "${YELLOW}Service ${SERVICE_NAME} was triggered but may have already completed (oneshot service).${NC}"
    
    # Show the last few log entries to confirm it ran
    echo
    echo -e "${BLUE}Recent logs from the service:${NC}"
    journalctl -u "${SERVICE_NAME}.service" -n 10 --no-pager
fi

echo
echo -e "${GREEN}To see complete logs, run:${NC}"
echo -e "  ${YELLOW}./view_hn_watcher_logs.sh${NC}" 