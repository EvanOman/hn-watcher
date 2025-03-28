#!/bin/bash

set -euo pipefail

SERVICE_NAME="hn_watcher"

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
    echo "  -f, --follow       Follow the journal in real-time"
    echo "  -n, --lines N      Show the last N lines (default: 50)"
    echo "  -s, --since TIME   Show entries since TIME (e.g., '1 hour ago', 'yesterday')"
    echo "  -h, --help         Show this help message"
    echo
    echo -e "${BLUE}Examples:${NC}"
    echo "  $0                           # Show last 50 log entries"
    echo "  $0 -f                        # Follow logs in real-time"
    echo "  $0 -n 100                    # Show last 100 log entries"
    echo "  $0 -s \"2 hours ago\"          # Show entries from the last 2 hours"
}

# Default values
FOLLOW=0
NUM_LINES=50
SINCE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=1
            shift
            ;;
        -n|--lines)
            NUM_LINES="$2"
            shift 2
            ;;
        -s|--since)
            SINCE="$2"
            shift 2
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

# Check if the service or timer exists
if ! systemctl list-unit-files | grep -q "${SERVICE_NAME}.service" && ! systemctl list-unit-files | grep -q "${SERVICE_NAME}.timer"; then
    echo -e "${RED}Error: Neither ${SERVICE_NAME}.service nor ${SERVICE_NAME}.timer exist.${NC}"
    exit 1
fi

# Build the journalctl command
# Use the full unit name with the .service suffix
COMMAND="journalctl -u ${SERVICE_NAME}.service"

if [[ -n "$SINCE" ]]; then
    COMMAND="$COMMAND --since=\"$SINCE\""
elif [[ $FOLLOW -eq 0 ]]; then
    COMMAND="$COMMAND -n \"$NUM_LINES\""
fi

if [[ $FOLLOW -eq 1 ]]; then
    COMMAND="$COMMAND -f"
fi

# Display some info about what we're showing
echo -e "${GREEN}Viewing logs for ${YELLOW}${SERVICE_NAME}.service${GREEN}:${NC}"
if [[ $FOLLOW -eq 1 ]]; then
    echo -e "${BLUE}Following logs in real-time. Press Ctrl+C to exit.${NC}"
elif [[ -n "$SINCE" ]]; then
    echo -e "${BLUE}Showing logs since $SINCE.${NC}"
else
    echo -e "${BLUE}Showing last $NUM_LINES log entries.${NC}"
fi
echo

# You can also show timer info if it exists
if systemctl list-unit-files | grep -q "${SERVICE_NAME}.timer"; then
    echo -e "${GREEN}Timer status:${NC}"
    systemctl status "${SERVICE_NAME}.timer" --no-pager | grep -E "Active:|Trigger:|Triggers:" || true
    echo
fi

# Execute the command
echo -e "${YELLOW}Running: $COMMAND${NC}"
echo
eval "$COMMAND" 