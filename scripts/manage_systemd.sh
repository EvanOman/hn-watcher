#!/bin/bash

set -euo pipefail

SERVICE_NAME=hn_watcher
TIMER_NAME="${SERVICE_NAME}.timer"

# Define color codes for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage information
show_usage() {
    echo -e "${BLUE}Usage:${NC}"
    echo "  $0 [options]"
    echo
    echo -e "${BLUE}Options:${NC}"
    echo "  -p, --pause     Pause the timer"
    echo "  -r, --resume    Resume the timer"
    echo "  -s, --status    Show current timer status"
    echo "  -h, --help      Show this help message"
}

# Function to show status without failing on inactive state
show_status() {
    echo -e "${YELLOW}Current timer status:${NC}"
    systemctl status "$TIMER_NAME" --no-pager || true
    
    # Show additional useful information
    echo -e "\n${BLUE}Timer state:${NC}"
    systemctl is-active "$TIMER_NAME" || true
    echo -e "${BLUE}Next trigger time:${NC}"
    systemctl list-timers --all | grep "$TIMER_NAME" || true
}

# Check if timer exists
if ! systemctl list-unit-files | grep -q "$TIMER_NAME"; then
    echo -e "${RED}Error: ${TIMER_NAME} does not exist.${NC}"
    exit 1
fi

# Default to showing status if no args provided
if [ $# -eq 0 ]; then
    show_status
    exit 0
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--pause)
            echo -e "${YELLOW}Stopping ${TIMER_NAME}...${NC}"
            sudo systemctl stop "$TIMER_NAME"
            echo -e "${GREEN}Timer stopped successfully.${NC}"
            show_status
            exit 0
            ;;
        -r|--resume)
            echo -e "${YELLOW}Starting ${TIMER_NAME}...${NC}"
            sudo systemctl start "$TIMER_NAME"
            echo -e "${GREEN}Timer started successfully.${NC}"
            show_status
            exit 0
            ;;
        -s|--status)
            show_status
            exit 0
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done 