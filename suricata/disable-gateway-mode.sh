#!/bin/bash
# Disable Gateway Mode
# Returns network to normal configuration

echo "=========================================="
echo "Disable Gateway Mode"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: This script must be run as root"
    echo "   Please run: sudo ./disable-gateway-mode.sh"
    exit 1
fi

echo "Disabling gateway mode..."
echo ""

echo "Step 1: Disabling IP forwarding..."
sysctl -w net.inet.ip.forwarding=0
echo "✅ IP forwarding disabled"

echo ""
echo "Step 2: Disabling packet filter (NAT)..."
pfctl -d 2>/dev/null
echo "✅ Packet filter disabled"

echo ""
echo "=========================================="
echo "✅ Gateway Mode Disabled"
echo "=========================================="
echo ""
echo "📝 IMPORTANT:"
echo ""
echo "Remember to reconfigure your other devices back to"
echo "the original gateway:"
echo ""
echo "  Change Gateway from: 9.79.193.4"
echo "  Back to: 9.79.192.1"
echo ""
echo "On each device:"
echo "  - Go to network settings"
echo "  - Change Router/Gateway to: 9.79.192.1"
echo "  - Reconnect to network"
echo ""


