#!/bin/bash
# Test PQC TLS connections using OpenSSL 3.6.1 with native ML-KEM support

echo "🔐 Testing PQC TLS Connections with OpenSSL"
echo "============================================"
echo ""

# Test server (Cloudflare supports PQC)
TEST_SERVER="cloudflare.com"
PORT="443"

echo "📋 Available PQC Groups in OpenSSL 3.6.1:"
echo "  - X25519MLKEM768 (Hybrid PQC - recommended)"
echo "  - SecP256r1MLKEM768 (Hybrid PQC)"
echo "  - SecP384r1MLKEM1024 (Hybrid PQC)"
echo "  - X448MLKEM1024 (Hybrid PQC)"
echo "  - MLKEM512 (Pure PQC)"
echo "  - MLKEM768 (Pure PQC)"
echo "  - MLKEM1024 (Pure PQC)"
echo ""

# Test 1: Hybrid PQC (X25519 + ML-KEM-768)
echo "🧪 Test 1: Hybrid PQC (X25519MLKEM768)"
echo "--------------------------------------"
echo "This should be detected as PQC_HYBRID in Suricata"
echo ""
echo "Command: openssl s_client -connect ${TEST_SERVER}:${PORT} -groups X25519MLKEM768 -tls1_3 -brief"
echo ""
openssl s_client -connect ${TEST_SERVER}:${PORT} -groups X25519MLKEM768 -tls1_3 -brief <<< "Q" 2>&1 | head -20
echo ""
echo "✅ Check Suricata logs for PQC_HYBRID detection"
echo ""

# Test 2: Pure PQC (ML-KEM-768 only)
echo "🧪 Test 2: Pure PQC (MLKEM768)"
echo "------------------------------"
echo "This should be detected as PQC_PURE in Suricata"
echo ""
echo "Command: openssl s_client -connect ${TEST_SERVER}:${PORT} -groups MLKEM768 -tls1_3 -brief"
echo ""
openssl s_client -connect ${TEST_SERVER}:${PORT} -groups MLKEM768 -tls1_3 -brief <<< "Q" 2>&1 | head -20
echo ""
echo "✅ Check Suricata logs for PQC_PURE detection"
echo ""

# Test 3: Multiple PQC groups
echo "🧪 Test 3: Multiple PQC Groups"
echo "-------------------------------"
echo "This tests with multiple hybrid PQC options"
echo ""
echo "Command: openssl s_client -connect ${TEST_SERVER}:${PORT} -groups X25519MLKEM768:SecP256r1MLKEM768:X25519 -tls1_3 -brief"
echo ""
openssl s_client -connect ${TEST_SERVER}:${PORT} -groups X25519MLKEM768:SecP256r1MLKEM768:X25519 -tls1_3 -brief <<< "Q" 2>&1 | head -20
echo ""
echo "✅ Check Suricata logs for PQC_HYBRID detection"
echo ""

# Test 4: Classical only (for comparison)
echo "🧪 Test 4: Classical Only (X25519)"
echo "----------------------------------"
echo "This should be detected as CLASSICAL in Suricata"
echo ""
echo "Command: openssl s_client -connect ${TEST_SERVER}:${PORT} -groups X25519 -tls1_3 -brief"
echo ""
openssl s_client -connect ${TEST_SERVER}:${PORT} -groups X25519 -tls1_3 -brief <<< "Q" 2>&1 | head -20
echo ""
echo "✅ Check Suricata logs for CLASSICAL detection"
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