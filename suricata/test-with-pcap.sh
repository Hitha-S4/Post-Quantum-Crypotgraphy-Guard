#!/bin/bash
# Test PQC detection using generated ClientHello files

echo "=========================================="
echo "PQC Detection Test with PCAP Files"
echo "=========================================="
echo ""

# Check if text2pcap is available
if ! command -v text2pcap &> /dev/null; then
    echo "❌ text2pcap not found"
    echo ""
    echo "Install Wireshark to get text2pcap:"
    echo "  brew install wireshark"
    echo ""
    exit 1
fi

# Check if test files exist
if [ ! -f "pqc_hybrid_client_hello.bin" ]; then
    echo "❌ Test files not found"
    echo ""
    echo "Generate them first:"
    echo "  python3 scripts/generate-pqc-test-traffic.py"
    echo ""
    exit 1
fi

echo "Converting test files to PCAP format..."
echo ""

# Convert each test file to PCAP
declare -A test_files
test_files["pqc_hybrid_client_hello.bin"]="Hybrid PQC (X25519-MLKEM768)"
test_files["pqc_pure_client_hello.bin"]="Pure PQC (ML-KEM-768)"
test_files["classical_client_hello.bin"]="Classical (X25519)"

mkdir -p test-pcaps

for file in "${!test_files[@]}"; do
    desc="${test_files[$file]}"
    pcap_file="test-pcaps/${file%.bin}.pcap"
    
    echo "→ Converting: $file"
    echo "  Description: $desc"
    
    # Convert to PCAP
    text2pcap -q -T 443,443 "$file" "$pcap_file" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "  ✓ Created: $pcap_file"
    else
        echo "  ✗ Failed to convert"
    fi
    echo ""
done

echo "=========================================="
echo "Running Suricata Tests"
echo "=========================================="
echo ""

# Test each PCAP
for file in "${!test_files[@]}"; do
    desc="${test_files[$file]}"
    pcap_file="test-pcaps/${file%.bin}.pcap"
    
    if [ ! -f "$pcap_file" ]; then
        continue
    fi
    
    echo "Testing: $desc"
    echo "File: $pcap_file"
    echo ""
    
    # Run Suricata on the PCAP
    ./src/suricata -c suricata.yaml -r "$pcap_file" -l ./logs >/dev/null 2>&1
    
    # Check results
    if [ -f "logs/eve.json" ]; then
        # Get the PQC detection result
        result=$(jq -r 'select(.event_type=="tls") | .tls.pqc.posture' logs/eve.json 2>/dev/null | tail -1)
        is_pqc=$(jq -r 'select(.event_type=="tls") | .tls.pqc.is_pqc' logs/eve.json 2>/dev/null | tail -1)
        groups=$(jq -r 'select(.event_type=="tls") | .tls.pqc.supported_groups_names | join(", ")' logs/eve.json 2>/dev/null | tail -1)
        
        if [ -n "$result" ]; then
            echo "  ✅ Detection Result:"
            echo "     Posture: $result"
            echo "     Is PQC: $is_pqc"
            echo "     Groups: $groups"
        else
            echo "  ⚠️  No TLS event detected"
        fi
    else
        echo "  ✗ No eve.json generated"
    fi
    
    echo ""
    echo "---"
    echo ""
done

echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""

if [ -f "logs/eve.json" ]; then
    echo "All PQC detections:"
    jq -c 'select(.event_type=="tls") | 
        {posture: .tls.pqc.posture, is_pqc: .tls.pqc.is_pqc, 
         groups: .tls.pqc.supported_groups_names}' logs/eve.json 2>/dev/null | 
    while read -r line; do
        echo "  $line"
    done
    
    echo ""
    echo "Count by posture:"
    jq -r 'select(.event_type=="tls") | .tls.pqc.posture' logs/eve.json 2>/dev/null | 
        sort | uniq -c | awk '{printf "  %-15s: %d\n", $2, $1}'
fi

echo ""
echo "PCAP files saved in: test-pcaps/"
echo "Logs saved in: logs/"
echo ""
echo "To view full results:"
echo "  jq 'select(.event_type==\"tls\") | .tls.pqc' logs/eve.json"
echo ""