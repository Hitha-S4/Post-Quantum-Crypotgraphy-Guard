#!/bin/bash
# Test PQC detection in Suricata with various test cases

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "PQC Detection Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Suricata is built
if [ ! -f "$PROJECT_ROOT/src/suricata" ]; then
    echo -e "${RED}Error: Suricata not built. Run ./autogen.sh && ./configure && make${NC}"
    exit 1
fi

# Create test directories
TEST_DIR="$PROJECT_ROOT/test-pqc"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo -e "${BLUE}Step 1: Generating test ClientHello messages...${NC}"
python3 "$SCRIPT_DIR/generate-pqc-test-traffic.py"
echo ""

# Check if files were generated
if [ ! -f "pqc_hybrid_client_hello.bin" ]; then
    echo -e "${RED}Error: Failed to generate test files${NC}"
    exit 1
fi

echo -e "${BLUE}Step 2: Creating test rules...${NC}"
cat > test-pqc.rules << 'EOF'
# PQC Test Rules
alert tls any any -> any any (msg:"TEST: Any PQC Detected"; tls.is_pqc; sid:9000001; rev:1;)
alert tls any any -> any any (msg:"TEST: Pure PQC"; tls.pqc_posture:"PQC_PURE"; sid:9000002; rev:1;)
alert tls any any -> any any (msg:"TEST: Hybrid PQC"; tls.pqc_posture:"PQC_HYBRID"; sid:9000003; rev:1;)
alert tls any any -> any any (msg:"TEST: Classical Only"; tls.pqc_posture:"CLASSICAL"; sid:9000004; rev:1;)
alert tls any any -> any any (msg:"TEST: ECH Protected"; tls.pqc_posture:"ECH_PROTECTED"; sid:9000005; rev:1;)
EOF
echo "Created test-pqc.rules"
echo ""

echo -e "${BLUE}Step 3: Testing with real PQC-enabled servers...${NC}"
echo ""

# Test servers that support PQC
TEST_SERVERS=(
    "pq.cloudflareresearch.com:443"
    "www.google.com:443"
)

echo "Testing connectivity to PQC servers..."
for server in "${TEST_SERVERS[@]}"; do
    host="${server%:*}"
    port="${server#*:}"
    
    echo -n "  Testing $host:$port... "
    if timeout 5 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${GREEN}✓ Reachable${NC}"
    else
        echo -e "${YELLOW}✗ Not reachable (may need VPN or different network)${NC}"
    fi
done
echo ""

echo -e "${BLUE}Step 4: Live capture test (10 seconds)...${NC}"
echo "This will capture TLS traffic to PQC-enabled servers"
echo ""

# Create a minimal suricata config for testing
cat > test-suricata.yaml << 'EOF'
%YAML 1.1
---
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    EXTERNAL_NET: "!$HOME_NET"

default-rule-path: .
rule-files:
  - test-pqc.rules

outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: eve.json
      types:
        - alert:
            payload: yes
            payload-buffer-size: 4kb
            payload-printable: yes
            packet: yes
        - tls:
            extended: yes

app-layer:
  protocols:
    tls:
      enabled: yes
      detection-ports:
        dp: 443
EOF

echo "Starting live capture for 10 seconds..."
echo "Try visiting: https://pq.cloudflareresearch.com or https://www.google.com"
echo ""

# Run Suricata in live capture mode (if interface available)
if command -v ip &> /dev/null; then
    INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
    if [ -n "$INTERFACE" ]; then
        echo "Capturing on interface: $INTERFACE"
        timeout 10 sudo "$PROJECT_ROOT/src/suricata" \
            -c test-suricata.yaml \
            -i "$INTERFACE" \
            -l . \
            2>/dev/null || true
        
        if [ -f "eve.json" ]; then
            echo ""
            echo -e "${GREEN}Capture complete!${NC}"
            echo ""
            
            # Analyze results
            TLS_COUNT=$(jq -r 'select(.event_type=="tls")' eve.json 2>/dev/null | wc -l)
            PQC_COUNT=$(jq -r 'select(.event_type=="tls" and .tls.pqc.is_pqc==true)' eve.json 2>/dev/null | wc -l)
            
            echo "Results:"
            echo "  Total TLS connections: $TLS_COUNT"
            echo "  PQC connections: $PQC_COUNT"
            
            if [ "$PQC_COUNT" -gt 0 ]; then
                echo ""
                echo -e "${GREEN}✓ PQC detection is working!${NC}"
                echo ""
                echo "Sample PQC events:"
                jq -r 'select(.event_type=="tls" and .tls.pqc.is_pqc==true) | 
                    "  - \(.tls.sni // "unknown") → \(.tls.pqc.posture)"' eve.json 2>/dev/null | head -5
            else
                echo ""
                echo -e "${YELLOW}No PQC connections detected in this capture${NC}"
                echo "This might be because:"
                echo "  1. No TLS 1.3 connections were made"
                echo "  2. Servers don't support PQC yet"
                echo "  3. Client doesn't advertise PQC support"
            fi
        fi
    else
        echo -e "${YELLOW}No network interface found for live capture${NC}"
    fi
else
    echo -e "${YELLOW}Skipping live capture (requires root and network interface)${NC}"
fi

echo ""
echo -e "${BLUE}Step 5: Testing with curl (if available)...${NC}"

if command -v curl &> /dev/null; then
    echo "Testing PQC-enabled servers with curl..."
    
    for server in "pq.cloudflareresearch.com" "www.google.com"; do
        echo -n "  Testing $server... "
        
        # Start Suricata in background
        sudo "$PROJECT_ROOT/src/suricata" \
            -c test-suricata.yaml \
            -i lo \
            -l . \
            >/dev/null 2>&1 &
        SURICATA_PID=$!
        sleep 2
        
        # Make request
        curl -s -o /dev/null "https://$server" --max-time 5 2>/dev/null || true
        sleep 1
        
        # Stop Suricata
        sudo kill $SURICATA_PID 2>/dev/null || true
        wait $SURICATA_PID 2>/dev/null || true
        
        # Check results
        if [ -f "eve.json" ]; then
            PQC_DETECTED=$(jq -r "select(.event_type==\"tls\" and .tls.sni==\"$server\") | .tls.pqc.posture" eve.json 2>/dev/null | head -1)
            if [ -n "$PQC_DETECTED" ]; then
                echo -e "${GREEN}✓ Detected: $PQC_DETECTED${NC}"
            else
                echo -e "${YELLOW}✗ No PQC detected${NC}"
            fi
        fi
    done
else
    echo -e "${YELLOW}curl not available, skipping${NC}"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "Generated test files:"
ls -lh *.bin 2>/dev/null || echo "  No binary files generated"
echo ""
echo "Test artifacts in: $TEST_DIR"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review eve.json for detailed PQC detection results"
echo "2. Use: jq 'select(.event_type==\"tls\") | .tls.pqc' eve.json"
echo "3. Monitor live traffic: $PROJECT_ROOT/view-pqc-events.sh"
echo "4. Check alerts: tail -f fast.log"
echo ""
echo "For manual testing:"
echo "  # Generate test traffic"
echo "  python3 $SCRIPT_DIR/generate-pqc-test-traffic.py"
echo ""
echo "  # Test with OpenSSL (if PQC-enabled)"
echo "  openssl s_client -connect pq.cloudflareresearch.com:443 -msg"
echo ""
echo "  # Run Suricata on PCAP"
echo "  $PROJECT_ROOT/src/suricata -c suricata.yaml -r test.pcap -l ./logs"
echo ""