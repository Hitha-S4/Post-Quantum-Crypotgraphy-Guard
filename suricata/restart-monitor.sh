#!/bin/bash

# Restart PQC Monitor Script
# This script stops the old monitor, installs the new Suricata binary, and restarts monitoring

echo "🔄 Restarting PQC Monitor with updated binary..."
echo ""

# Stop any running Suricata instances
echo "1️⃣ Stopping existing Suricata processes..."
sudo pkill -9 suricata 2>/dev/null || true
sleep 2

# Install the new binary
echo "2️⃣ Installing updated Suricata binary..."
sudo make install

if [ $? -ne 0 ]; then
    echo "❌ Installation failed. Please check for errors above."
    exit 1
fi

echo "3️⃣ Cleaning up old logs..."
rm -rf logs/*

echo "4️⃣ Starting monitor..."
sudo ./monitor-network.sh

echo ""
echo "✅ Monitor restarted with PQC extension parsing enabled!"
echo "   Run './view-pqc-events.sh' in another terminal to see PQC events"