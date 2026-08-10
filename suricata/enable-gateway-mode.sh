#!/bin/bash
# Enable Gateway Mode for Network-Wide Monitoring
# This will route all network traffic through your Mac

echo "=========================================="
echo "Enable Gateway Mode"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: This script must be run as root"
    echo "   Please run: sudo ./enable-gateway-mode.sh"
    exit 1
fi

echo "Network Configuration:"
echo "  Your Mac IP: 9.79.193.4"
echo "  Current Gateway: 9.79.192.1"
echo "  Network: 9.79.192.0/23"
echo ""
echo "⚠️  This will configure your Mac as a network gateway."
echo "   Other devices will need to be reconfigured to use"
echo "   your Mac (9.79.193.4) as their gateway."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Step 1: Enabling IP forwarding..."
sysctl -w net.inet.ip.forwarding=1

if [ $? -eq 0 ]; then
    echo "✅ IP forwarding enabled"
else
    echo "❌ Failed to enable IP forwarding"
    exit 1
fi

echo ""
echo "Step 2: Configuring NAT (Network Address Translation)..."

# Create PF configuration
cat > /tmp/suricata-nat.conf << 'EOF'
# Suricata Gateway Mode NAT Configuration
# Allow all traffic and enable NAT
nat on en0 from 9.79.192.0/23 to any -> (en0)
pass in all
pass out all
EOF

# Load the configuration
pfctl -f /tmp/suricata-nat.conf 2>/dev/null
pfctl -e 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ NAT configured and enabled"
else
    echo "⚠️  NAT may already be enabled"
fi

echo ""
echo "=========================================="
echo "✅ Gateway Mode Enabled!"
echo "=========================================="
echo ""
echo "📝 NEXT STEPS:"
echo ""
echo "1. Configure other devices to use this Mac as gateway:"
echo ""
echo "   On each device (phone, tablet, laptop, etc.):"
echo "   - Go to WiFi/Network settings"
echo "   - Find your network connection"
echo "   - Change these settings:"
echo ""
echo "     Gateway/Router: 9.79.193.4  (was: 9.79.192.1)"
echo "     DNS Server: 9.79.192.1  (keep as is)"
echo ""
echo "2. Device-specific instructions:"
echo ""
echo "   iPhone/iPad:"
echo "   - Settings → WiFi → (i) next to network"
echo "   - Configure IP → Manual"
echo "   - Change Router to: 9.79.193.4"
echo ""
echo "   Android:"
echo "   - Settings → WiFi → Long press network → Modify"
echo "   - Advanced → IP Settings → Static"
echo "   - Change Gateway to: 9.79.193.4"
echo ""
echo "   Windows:"
echo "   - Control Panel → Network → Adapter Settings"
echo "   - Properties → IPv4 → Properties"
echo "   - Change Default Gateway to: 9.79.193.4"
echo ""
echo "   Mac:"
echo "   - System Settings → Network → Advanced"
echo "   - TCP/IP → Router: 9.79.193.4"
echo ""
echo "3. Test connectivity on other devices:"
echo "   - Try browsing the web"
echo "   - Run: ping 8.8.8.8"
echo ""
echo "4. Start/restart Suricata monitoring:"
echo "   sudo ./monitor-network.sh"
echo ""
echo "5. You should now see traffic from ALL devices!"
echo ""
echo "=========================================="
echo ""
echo "To disable gateway mode later, run:"
echo "  sudo ./disable-gateway-mode.sh"
echo ""


