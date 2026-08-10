#!/bin/bash
# Quick PQC test with OpenSSL - generates real PQC ClientHello messages

echo "🔐 Quick PQC Test with OpenSSL 3.6.1"
echo "====================================="
echo ""

# Check if Suricata is running
if ! pgrep -x "suricata" > /dev/null; then
    echo "⚠️  WARNING: Suricata doesn't appear to be running!"
    echo "   Start it with: sudo suricata -c suricata.yaml -i en0"
    echo ""
fi

echo "📋 Testing PQC with Cloudflare..."
echo ""

# Test 1: Hybrid PQC
echo "🧪 Test 1: Hybrid PQC (X25519MLKEM768)"
echo "--------------------------------------"
echo "Connecting to cloudflare.com with PQC support..."
echo ""

# Use gtimeout if available (brew install coreutils), otherwise just run
if command -v gtimeout &> /dev/null; then
    gtimeout 3 openssl s_client -connect cloudflare.com:443 -groups X25519MLKEM768 -tls1_3 -brief <<< "Q" 2>&1 | grep -E "Connecting|Protocol|Ciphersuite|Supported groups|Verification" | head -10
else
    (sleep 3; echo "Q") | openssl s_client -connect cloudflare.com:443 -groups X25519MLKEM768 -tls1_3 -brief 2>&1 | grep -E "Connecting|Protocol|Ciphersuite|Supported groups|Verification" | head -10
fi

echo ""
echo "✅ Connection attempted with PQC groups"
echo ""

# Wait a moment for Suricata to process
sleep 2

# Check logs
echo "📊 Checking Suricata logs for recent TLS events..."
echo ""

RECENT_TLS=$(tail -50 logs/eve.json | jq -r 'select(.event_type=="tls" and (.dest_ip | contains("104.16") or contains("104.18"))) | "\(.timestamp | split(".")[0]) | \(.tls.sni // .dest_ip) | Posture: \(.tls.pqc.posture) | Groups: \(.tls.pqc.supported_groups[0:3])"' | tail -5)

if [ -z "$RECENT_TLS" ]; then
    echo "⚠️  No recent Cloudflare TLS events found in logs"
    echo ""
    echo "Showing last 5 TLS events instead:"
    tail -50 logs/eve.json | jq -r 'select(.event_type=="tls") | "\(.timestamp | split(".")[0]) | \(.tls.sni // .dest_ip) | Posture: \(.tls.pqc.posture)"' | tail -5
else
    echo "$RECENT_TLS"
fi

echo ""
echo "🔍 Checking for PQC-specific group IDs..."
echo ""

# Check for PQC group IDs (512-517)
PQC_GROUPS=$(tail -100 logs/eve.json | jq -r 'select(.event_type=="tls" and .tls.pqc.supported_groups) | .tls.pqc.supported_groups[]' | grep -E "^(512|513|514|515|516|517)$" | sort -u)

if [ -z "$PQC_GROUPS" ]; then
    echo "❌ No PQC group IDs (512-517) detected yet"
    echo ""
    echo "This could mean:"
    echo "  1. Server doesn't support PQC (fell back to classical)"
    echo "  2. OpenSSL didn't send PQC groups (check OpenSSL version)"
    echo "  3. Connection didn't complete"
else
    echo "✅ PQC group IDs detected: $PQC_GROUPS"
    echo ""
    echo "Group ID mapping:"
    echo "  512 = ML-KEM-512 (Pure PQC)"
    echo "  513 = ML-KEM-768 (Pure PQC)"
    echo "  514 = ML-KEM-1024 (Pure PQC)"
    echo "  515 = X25519-MLKEM768 (Hybrid PQC)"
    echo "  516 = X25519-MLKEM1024 (Hybrid PQC)"
    echo "  517 = P256-MLKEM768 (Hybrid PQC)"
fi

echo ""
echo "📈 Overall Statistics"
echo "===================="
echo ""
jq -r 'select(.event_type=="tls") | .tls.pqc.posture' logs/eve.json | sort | uniq -c | sort -rn

echo ""
echo "💡 Next Steps"
echo "============"
echo ""
echo "To see real-time PQC events:"
echo "  ./view-pqc-events.sh"
echo ""
echo "To find any PQC connections:"
echo "  jq 'select(.tls.pqc.is_pqc==true)' logs/eve.json"
echo ""
echo "To run full test suite:"
echo "  ./test-pqc-with-openssl.sh"
echo ""