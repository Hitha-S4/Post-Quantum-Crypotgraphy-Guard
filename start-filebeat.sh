#!/bin/bash

# Start Filebeat with corrected configuration
# This script must be run with sudo

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Starting Filebeat with Corrected Config"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗${NC} This script must be run with sudo"
    echo "Usage: sudo ./start-filebeat-fixed.sh"
    exit 1
fi

echo ""
echo "Step 1: Copying corrected Filebeat configuration..."
cp filebeat-corrected.yml /opt/homebrew/etc/filebeat/filebeat.yml
chown root:wheel /opt/homebrew/etc/filebeat/filebeat.yml
chmod 644 /opt/homebrew/etc/filebeat/filebeat.yml
echo -e "${GREEN}✓${NC} Configuration copied"

echo ""
echo "Step 2: Testing Filebeat configuration..."
if filebeat test config -c /opt/homebrew/etc/filebeat/filebeat.yml > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Configuration is valid"
else
    echo -e "${RED}✗${NC} Configuration has errors:"
    filebeat test config -c /opt/homebrew/etc/filebeat/filebeat.yml
    exit 1
fi

echo ""
echo "Step 3: Checking if Filebeat is already running..."
if pgrep -x "filebeat" > /dev/null; then
    echo -e "${YELLOW}⚠${NC} Filebeat is already running, stopping it..."
    pkill filebeat
    sleep 2
fi

echo ""
echo "Step 4: Starting Filebeat..."
filebeat -e -c /opt/homebrew/etc/filebeat/filebeat.yml > /tmp/filebeat.log 2>&1 &
FILEBEAT_PID=$!
sleep 3

if ps -p $FILEBEAT_PID > /dev/null; then
    echo -e "${GREEN}✓${NC} Filebeat started successfully (PID: $FILEBEAT_PID)"
    echo ""
    echo "Monitor logs with:"
    echo "  tail -f /tmp/filebeat.log"
    echo ""
    echo "Check Kafka messages:"
    echo "  kafka-console-consumer --bootstrap-server localhost:9092 --topic suricata-events --from-beginning --max-messages 5"
else
    echo -e "${RED}✗${NC} Filebeat failed to start"
    echo "Check logs: tail -f /tmp/filebeat.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "Filebeat is now running!"
echo "=========================================="


