#!/bin/bash
# Suricata Network Monitoring Script
# This script starts Suricata to monitor all network traffic on en0

echo "=========================================="
echo "Suricata Network Traffic Monitor"
echo "=========================================="
echo ""
echo "Interface: en0 (9.79.193.4)"
echo "Log Directory: logs/"
echo "Configuration: suricata.yaml"
echo "Rules: signatures.rules"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""
echo "Logs will be written to:"
echo "  - logs/fast.log (Quick alerts)"
echo "  - logs/eve.json (Detailed JSON events)"
echo "  - logs/stats.log (Statistics)"
echo ""
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  WARNING: Not running as root!"
    echo "   Network monitoring requires root privileges."
    echo "   Please run: sudo ./monitor-network.sh"
    echo ""
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Clear old logs (optional - comment out if you want to keep history)
echo "Clearing old logs..."
rm -f logs/*.log logs/*.json

# Start Suricata
echo "Starting Suricata network monitor..."
echo ""

./src/suricata -c suricata.yaml -i en0 -l logs -v

echo ""
echo "Monitoring stopped."
echo "Check logs/ directory for captured events."


