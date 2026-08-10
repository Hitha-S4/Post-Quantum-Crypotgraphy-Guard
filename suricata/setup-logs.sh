#!/bin/bash
# Setup log directory for Suricata

echo "📁 Creating Suricata log directory..."
sudo mkdir -p /usr/local/var/log/suricata
sudo chmod 755 /usr/local/var/log/suricata

echo "✅ Log directory created: /usr/local/var/log/suricata"
echo ""
echo "Now you can start Suricata with:"
echo "  sudo src/suricata -c ./suricata.yaml -i en0 -v"