#!/bin/bash
# Real-time alert viewer for Suricata
# Shows alerts as they happen

echo "=========================================="
echo "Suricata Live Alert Monitor"
echo "=========================================="
echo ""
echo "Watching: logs/fast.log"
echo "Press Ctrl+C to stop"
echo ""
echo "Waiting for alerts..."
echo "=========================================="
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Touch the file if it doesn't exist
touch logs/fast.log

# Follow the fast.log file in real-time
tail -f logs/fast.log


