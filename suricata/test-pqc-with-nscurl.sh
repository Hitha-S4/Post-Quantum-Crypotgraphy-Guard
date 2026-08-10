#!/bin/bash
# Test PQC TLS connections using macOS nscurl with TLS diagnostics

echo "🍎 Testing PQC TLS Connections with nscurl (macOS)"
echo "=================================================="
echo ""

# Test servers that might support PQC
TEST_URLS=(
    "https://cloudflare.com"
    "https://www.google.com"
    "https://pq.cloudflareresearch.com"
)

echo "📋 About nscurl:"
echo "  - Native macOS networking tool"
echo "  - Uses system TLS stack (may support PQC if macOS does)"
echo "  - Can show TLS diagnostics with --tls-diagnostics"
echo ""

for URL in "${TEST_URLS[@]}"; do
    echo "🧪 Testing: $URL"
    echo "----------------------------------------"
    echo ""
    
    # Test with TLS diagnostics
    echo "Command: nscurl --tls-diagnostics -o /dev/null \"$URL\""
    echo ""
    nscurl --tls-diagnostics -o /dev/null "$URL" 2>&1 | head -30
    echo ""
    echo "✅ Check Suricata logs for any PQC detection"
    echo ""
    sleep 2
done

echo "📊 Additional nscurl Tests"
echo "=========================="
echo ""

# Test with verbose output
echo "🧪 Verbose connection test:"
echo "Command: nscurl -i --tls-diagnostics \"https://cloudflare.com\" 2>&1 | head -50"
echo ""
nscurl -i --tls-diagnostics "https://cloudflare.com" 2>&1 | head -50
echo ""

echo "📊 View Results"
echo "==============="
echo "Run these commands to see PQC detections:"
echo ""
echo "  # View all PQC events:"
echo "  ./view-pqc-events.sh"
echo ""
echo "  # Check for PQC traffic:"
echo "  jq 'select(.tls.pqc.is_pqc==true)' logs/eve.json"
echo ""
echo "  # See latest TLS events:"
echo "  tail -20 logs/eve.json | jq 'select(.event_type==\"tls\") | {dest_ip, dest_port, pqc: .tls.pqc}'"
echo ""
echo "⚠️  Note: nscurl uses macOS system TLS stack"
echo "    PQC support depends on macOS version and configuration"
echo "    OpenSSL method (test-pqc-with-openssl.sh) is more reliable"
echo ""