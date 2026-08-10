#!/bin/bash
# Network-Wide Monitoring Setup for Suricata
# This configures your MacBook as a transparent monitoring gateway

echo "=========================================="
echo "Suricata Network-Wide Monitoring Setup"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This is an ADVANCED configuration!"
echo ""
echo "This will configure your MacBook to monitor ALL devices"
echo "on your network by setting it up as a gateway."
echo ""
echo "Network Information:"
echo "  Your IP: 9.79.193.4"
echo "  Gateway: 9.79.192.1"
echo "  Network: 9.79.192.0/23"
echo "  Interface: en0"
echo ""
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: This script must be run as root"
    echo "   Please run: sudo ./setup-network-monitoring.sh"
    exit 1
fi

echo "📋 Setup Options:"
echo ""
echo "1. Enable Promiscuous Mode (Recommended - Passive)"
echo "   - Captures all packets visible on the network segment"
echo "   - Requires network switch with port mirroring OR hub"
echo "   - Safe, passive monitoring"
echo "   - Won't affect network operation"
echo ""
echo "2. Gateway Mode (Advanced - Active)"
echo "   - Routes all network traffic through this Mac"
echo "   - Requires reconfiguring other devices"
echo "   - Can monitor AND filter traffic"
echo "   - Risk of network disruption if misconfigured"
echo ""
echo "3. ARP Spoofing (Expert - Man-in-the-Middle)"
echo "   - Intercepts traffic between devices and gateway"
echo "   - Requires additional tools (arpspoof/ettercap)"
echo "   - Advanced technique"
echo "   - Legal/ethical considerations"
echo ""
read -p "Choose option (1/2/3) or 'q' to quit: " choice

case $choice in
    1)
        echo ""
        echo "=========================================="
        echo "Option 1: Promiscuous Mode"
        echo "=========================================="
        echo ""
        echo "Enabling promiscuous mode on en0..."
        
        # Enable promiscuous mode
        ifconfig en0 promisc
        
        if [ $? -eq 0 ]; then
            echo "✅ Promiscuous mode enabled on en0"
            echo ""
            echo "📝 IMPORTANT NOTES:"
            echo ""
            echo "1. This only captures packets that reach your network card"
            echo "2. On a switched network, you'll only see:"
            echo "   - Broadcast traffic"
            echo "   - Multicast traffic"
            echo "   - Traffic to/from this Mac"
            echo ""
            echo "3. To see ALL network traffic, you need:"
            echo "   - Port mirroring on your switch (SPAN port)"
            echo "   - OR connect through a network hub (not switch)"
            echo "   - OR use ARP spoofing (option 3)"
            echo ""
            echo "4. Check your switch/router documentation for:"
            echo "   - 'Port Mirroring'"
            echo "   - 'SPAN' (Switched Port Analyzer)"
            echo "   - 'Monitor Port'"
            echo ""
            echo "✅ Setup complete! Run: sudo ./monitor-network.sh"
        else
            echo "❌ Failed to enable promiscuous mode"
            echo "   Your network card may not support this feature"
        fi
        ;;
        
    2)
        echo ""
        echo "=========================================="
        echo "Option 2: Gateway Mode Setup"
        echo "=========================================="
        echo ""
        echo "⚠️  WARNING: This will change your network configuration!"
        echo ""
        read -p "Are you sure? This can break your network! (yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            echo "Setup cancelled."
            exit 0
        fi
        
        echo ""
        echo "Setting up gateway mode..."
        echo ""
        
        # Enable IP forwarding
        echo "1. Enabling IP forwarding..."
        sysctl -w net.inet.ip.forwarding=1
        
        # Enable NAT
        echo "2. Configuring NAT (Network Address Translation)..."
        cat > /tmp/pf-nat.conf << 'EOF'
# NAT configuration for Suricata monitoring
nat on en0 from 9.79.192.0/23 to any -> (en0)
pass in all
pass out all
EOF
        
        pfctl -f /tmp/pf-nat.conf
        pfctl -e
        
        echo ""
        echo "✅ Gateway mode configured!"
        echo ""
        echo "📝 NEXT STEPS:"
        echo ""
        echo "1. Configure other devices to use this Mac as gateway:"
        echo "   - Set default gateway to: 9.79.193.4"
        echo "   - Keep DNS as: 9.79.192.1 (or your router)"
        echo ""
        echo "2. On each device you want to monitor:"
        echo "   - Go to network settings"
        echo "   - Change gateway from 9.79.192.1 to 9.79.193.4"
        echo "   - Save and reconnect"
        echo ""
        echo "3. Start monitoring:"
        echo "   sudo ./monitor-network.sh"
        echo ""
        echo "⚠️  To disable gateway mode later:"
        echo "   sudo pfctl -d"
        echo "   sudo sysctl -w net.inet.ip.forwarding=0"
        ;;
        
    3)
        echo ""
        echo "=========================================="
        echo "Option 3: ARP Spoofing (Man-in-the-Middle)"
        echo "=========================================="
        echo ""
        echo "⚠️  LEGAL WARNING:"
        echo ""
        echo "ARP spoofing can be considered a network attack."
        echo "Only use this on networks you own or have explicit"
        echo "permission to monitor."
        echo ""
        echo "This requires additional tools:"
        echo "  - arpspoof (from dsniff package)"
        echo "  - OR ettercap"
        echo ""
        echo "Installation:"
        echo "  brew install dsniff"
        echo "  brew install ettercap"
        echo ""
        echo "Usage example with arpspoof:"
        echo "  # Terminal 1: Spoof gateway"
        echo "  sudo arpspoof -i en0 -t 9.79.192.1 <target_ip>"
        echo ""
        echo "  # Terminal 2: Spoof target"
        echo "  sudo arpspoof -i en0 -t <target_ip> 9.79.192.1"
        echo ""
        echo "  # Terminal 3: Monitor traffic"
        echo "  sudo ./monitor-network.sh"
        echo ""
        echo "This is an advanced technique. Please research thoroughly"
        echo "before attempting."
        ;;
        
    q|Q)
        echo "Setup cancelled."
        exit 0
        ;;
        
    *)
        echo "Invalid option. Setup cancelled."
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="


