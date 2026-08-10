#!/bin/bash
# Check PQC detection status and Chrome configuration

echo "=========================================="
echo "PQC Detection Status Check"
echo "=========================================="
echo ""

# Check recent TLS connections
echo "1. Recent TLS Connections (last 10):"
echo "---"
jq -c 'select(.event_type=="tls") | 
    {time: .timestamp, sni: .tls.sni, posture: .tls.pqc.posture, 
     groups: .tls.pqc.supported_groups}' logs/eve.json 2>/dev/null | tail -10 | jq .

echo ""
echo "2. PQC Statistics:"
echo "---"
echo "Total TLS connections:"
jq -r 'select(.event_type=="tls")' logs/eve.json 2>/dev/null | wc -l | tr -d ' '

echo "By posture:"
jq -r 'select(.event_type=="tls") | .tls.pqc.posture' logs/eve.json 2>/dev/null | 
    sort | uniq -c | awk '{printf "  %-15s: %d\n", $2, $1}'

echo ""
echo "3. Looking for PQC group IDs:"
echo "---"
echo "Checking for Kyber/ML-KEM groups (512-517, 0x0200-0x0205)..."

# Check if any connections have PQC groups
PQC_GROUPS=$(jq -r 'select(.event_type=="tls") | .tls.pqc.supported_groups[]?' logs/eve.json 2>/dev/null | 
    grep -E "^(512|513|514|515|516|517)$" | wc -l | tr -d ' ')

if [ "$PQC_GROUPS" -gt 0 ]; then
    echo "✅ Found $PQC_GROUPS PQC group references!"
    echo ""
    echo "Connections with PQC groups:"
    jq 'select(.event_type=="tls" and (.tls.pqc.supported_groups[]? | 
        select(. >= 512 and . <= 517))) | 
        {sni: .tls.sni, groups: .tls.pqc.supported_groups_names}' logs/eve.json 2>/dev/null
else
    echo "❌ No PQC groups (512-517) found in traffic"
fi

echo ""
echo "4. Chrome PQC Verification:"
echo "---"
echo "To verify Chrome has PQC enabled:"
echo ""
echo "A. Check Chrome flags:"
echo "   1. Open: chrome://flags"
echo "   2. Search for: PostQuantumKyber"
echo "   3. Should be: Enabled"
echo ""
echo "B. Launch Chrome with PQC:"
echo "   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\"
echo "     --enable-features=PostQuantumKyber \\"
echo "     --user-data-dir=/tmp/chrome-pqc"
echo ""
echo "C. Test sites:"
echo "   - https://pq.cloudflareresearch.com"
echo "   - https://www.cloudflare.com"
echo ""

echo ""
echo "5. Alternative: Check if server supports PQC:"
echo "---"
echo "Test with OpenSSL (if you have OQS version):"
echo "  openssl s_client -connect pq.cloudflareresearch.com:443 -msg | grep -i kyber"
echo ""

echo ""
echo "6. Current Chrome connections:"
echo "---"
echo "Recent Chrome user-agent connections:"
jq -c 'select(.event_type=="tls" and .tls.sni) | 
    {time: .timestamp, sni: .tls.sni, groups: .tls.pqc.supported_groups}' logs/eve.json 2>/dev/null | 
    tail -5 | jq .

echo ""
echo "=========================================="
echo "Troubleshooting"
echo "=========================================="
echo ""
echo "If still no PQC detected:"
echo ""
echo "1. Verify Chrome version supports PQC:"
echo "   chrome://version"
echo "   (Need Chrome 116+ for experimental PQC)"
echo ""
echo "2. Try Firefox Nightly instead:"
echo "   about:config → security.tls.enable_kyber = true"
echo ""
echo "3. Check if site supports PQC:"
echo "   curl -v https://pq.cloudflareresearch.com 2>&1 | grep -i supported"
echo ""
echo "4. Monitor logs while browsing:"
echo "   ./view-pqc-events.sh"
echo "   (Then visit https://pq.cloudflareresearch.com in Chrome)"
echo ""
echo "5. Check for group 515 (0x0203 = X25519-MLKEM768):"
echo "   tail -f logs/eve.json | jq 'select(.tls.pqc.supported_groups[]? == 515)'"
echo ""