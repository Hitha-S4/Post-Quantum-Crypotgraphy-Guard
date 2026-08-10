#!/bin/bash
# Quick Start Guide for PQC Testing in Suricata

set -e

echo "=========================================="
echo "PQC Testing Quick Start"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}This script will help you test PQC detection in Suricata${NC}"
echo ""
echo "What would you like to do?"
echo ""
echo "1) Generate test PQC ClientHello messages"
echo "2) Create PQC test rules"
echo "3) Run full PQC detection test suite"
echo "4) Test with live traffic (requires root)"
echo "5) View PQC events from logs"
echo "6) Show PQC testing documentation"
echo "7) All of the above"
echo ""
read -p "Enter your choice (1-7): " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}Generating test ClientHello messages...${NC}"
        python3 "$SCRIPT_DIR/scripts/generate-pqc-test-traffic.py"
        ;;
    2)
        echo ""
        echo -e "${GREEN}Creating PQC test rules...${NC}"
        bash "$SCRIPT_DIR/scripts/create-pqc-test-rules.sh"
        ;;
    3)
        echo ""
        echo -e "${GREEN}Running full test suite...${NC}"
        bash "$SCRIPT_DIR/scripts/test-pqc-detection.sh"
        ;;
    4)
        echo ""
        echo -e "${GREEN}Testing with live traffic...${NC}"
        echo "This requires root privileges and will capture for 30 seconds"
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            sudo "$SCRIPT_DIR/src/suricata" -c suricata.yaml -i eth0 -l ./logs &
            SURICATA_PID=$!
            echo "Suricata started (PID: $SURICATA_PID)"
            echo "Visit PQC-enabled sites like:"
            echo "  - https://pq.cloudflareresearch.com"
            echo "  - https://www.google.com"
            echo ""
            echo "Capturing for 30 seconds..."
            sleep 30
            sudo kill $SURICATA_PID
            echo ""
            echo "Analyzing results..."
            bash "$SCRIPT_DIR/view-pqc-events.sh"
        fi
        ;;
    5)
        echo ""
        echo -e "${GREEN}Viewing PQC events...${NC}"
        bash "$SCRIPT_DIR/view-pqc-events.sh"
        ;;
    6)
        echo ""
        echo -e "${GREEN}Opening documentation...${NC}"
        if [ -f "$SCRIPT_DIR/PQC-TEST-GUIDE.md" ]; then
            less "$SCRIPT_DIR/PQC-TEST-GUIDE.md"
        else
            cat "$SCRIPT_DIR/PQC-TLS-DETECTION.md"
        fi
        ;;
    7)
        echo ""
        echo -e "${GREEN}Running complete setup...${NC}"
        echo ""
        
        # Step 1: Generate test messages
        echo -e "${BLUE}[1/4] Generating test ClientHello messages...${NC}"
        python3 "$SCRIPT_DIR/scripts/generate-pqc-test-traffic.py"
        echo ""
        
        # Step 2: Create rules
        echo -e "${BLUE}[2/4] Creating PQC test rules...${NC}"
        bash "$SCRIPT_DIR/scripts/create-pqc-test-rules.sh"
        echo ""
        
        # Step 3: Run tests
        echo -e "${BLUE}[3/4] Running test suite...${NC}"
        bash "$SCRIPT_DIR/scripts/test-pqc-detection.sh"
        echo ""
        
        # Step 4: Show summary
        echo -e "${BLUE}[4/4] Setup complete!${NC}"
        echo ""
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Quick Reference"
echo "=========================================="
echo ""
echo "Test with real servers:"
echo "  curl --curves X25519MLKEM768 https://pq.cloudflareresearch.com"
echo ""
echo "Generate test traffic:"
echo "  python3 scripts/generate-pqc-test-traffic.py"
echo ""
echo "Run Suricata on PCAP:"
echo "  ./src/suricata -c suricata.yaml -r test.pcap -l ./logs"
echo ""
echo "View PQC events:"
echo "  ./view-pqc-events.sh"
echo "  # or"
echo "  jq 'select(.event_type==\"tls\") | .tls.pqc' logs/eve.json"
echo ""
echo "Check alerts:"
echo "  tail -f logs/fast.log"
echo ""
echo "Documentation:"
echo "  - PQC-TLS-DETECTION.md (architecture and implementation)"
echo "  - PQC-TEST-GUIDE.md (testing guide)"
echo ""
echo -e "${GREEN}Happy testing!${NC}"
echo ""