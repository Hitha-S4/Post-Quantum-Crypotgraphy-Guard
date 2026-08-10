#!/bin/bash
# Quick PQC Detection Test

echo "=========================================="
echo "PQC Detection Quick Test"
echo "=========================================="
echo ""

# Check if Suricata exists
if [ ! -f "src/suricata" ]; then
    echo "Error: Suricata not found. Run 'make' first."
    exit 1
fi

# Create logs directory
mkdir -p logs

echo "Testing PQC detection with real servers..."
echo ""
echo "This will:"
echo "1. Start Suricata in background"
echo "2. Make requests to PQC-enabled servers"
echo "3. Check EVE JSON for PQC detection"
echo ""

# Get the default network interface
if command -v route &> /dev/null; then
    INTERFACE=$(route -n get default 2>/dev/null | grep interface | awk '{print $2}')
elif command -v ip &> /dev/null; then
    INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
else
    INTERFACE="en0"  # Default for macOS
fi

echo "Using network interface: $INTERFACE"
echo ""

# Start Suricata in background
echo "Starting Suricata..."
sudo ./src/suricata -c suricata.yaml -i "$INTERFACE" -l ./logs >/dev/null 2>&1 &
SURICATA_PID=$!

# Wait for Suricata to start
sleep 3

if ! ps -p $SURICATA_PID > /dev/null; then
    echo "Error: Suricata failed to start"
    echo "Try running manually: sudo ./src/suricata -c suricata.yaml -i $INTERFACE -l ./logs"
    exit 1
fi

echo "Suricata started (PID: $SURICATA_PID)"
echo ""

# Make requests to PQC-enabled servers
echo "Making requests to PQC-enabled servers..."
echo "  - Cloudflare PQC Research"
curl -s -o /dev/null --max-time 5 https://pq.cloudflareresearch.com 2>/dev/null || true
sleep 1

echo "  - Google"
curl -s -o /dev/null --max-time 5 https://www.google.com 2>/dev/null || true
sleep 1

echo "  - Example.com (classical)"
curl -s -o /dev/null --max-time 5 https://example.com 2>/dev/null || true
sleep 2

echo ""
echo "Stopping Suricata..."
sudo kill $SURICATA_PID 2>/dev/null
wait $SURICATA_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo "Results"
echo "=========================================="
echo ""

# Check if eve.json exists
if [ ! -f "logs/eve.json" ]; then
    echo "No eve.json found. Suricata may not have captured any traffic."
    echo ""
    echo "Try running manually:"
    echo "  sudo ./src/suricata -c suricata.yaml -i $INTERFACE -l ./logs"
    exit 1
fi

# Count TLS events
TLS_COUNT=$(jq -r 'select(.event_type=="tls")' logs/eve.json 2>/dev/null | wc -l | tr -d ' ')
echo "Total TLS connections captured: $TLS_COUNT"

if [ "$TLS_COUNT" -eq 0 ]; then
    echo ""
    echo "No TLS connections captured. This could mean:"
    echo "  1. Network interface is incorrect"
    echo "  2. Permissions issue (need sudo)"
    echo "  3. No traffic was generated"
    echo ""
    echo "Try running Suricata manually and then browse to HTTPS sites"
    exit 0
fi

# Check for PQC field
PQC_COUNT=$(jq -r 'select(.event_type=="tls" and .tls.pqc)' logs/eve.json 2>/dev/null | wc -l | tr -d ' ')
echo "TLS connections with PQC data: $PQC_COUNT"

if [ "$PQC_COUNT" -eq 0 ]; then
    echo ""
    echo "⚠️  No PQC data found in TLS events"
    echo ""
    echo "This means PQC detection may not be enabled. Check:"
    echo "  1. Rust support: ./src/suricata --build-info | grep -i rust"
    echo "  2. TLS config in suricata.yaml"
    exit 0
fi

echo ""
echo "✅ PQC Detection is Working!"
echo ""

# Show PQC postures detected
echo "PQC Postures Detected:"
jq -r 'select(.event_type=="tls" and .tls.pqc) | .tls.pqc.posture' logs/eve.json 2>/dev/null | sort | uniq -c | awk '{printf "  %-15s: %d\n", $2, $1}'

echo ""
echo "Sample PQC Connections:"
jq -c 'select(.event_type=="tls" and .tls.pqc.is_pqc==true) | 
    {sni: .tls.sni, posture: .tls.pqc.posture, groups: .tls.pqc.supported_groups_names}' logs/eve.json 2>/dev/null | head -3 | jq .

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "View all PQC events:"
echo "  jq 'select(.event_type==\"tls\") | .tls.pqc' logs/eve.json"
echo ""
echo "Monitor in real-time:"
echo "  ./view-pqc-events.sh"
echo ""
echo "See full documentation:"
echo "  cat PQC-TESTING-WITHOUT-KEYWORDS.md"
echo ""