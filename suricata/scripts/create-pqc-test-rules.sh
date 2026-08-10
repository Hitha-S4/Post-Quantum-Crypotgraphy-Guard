#!/bin/bash
# Create comprehensive PQC test rules for Suricata

RULES_FILE="${1:-rules/pqc-test.rules}"

echo "Creating PQC test rules in: $RULES_FILE"

cat > "$RULES_FILE" << 'EOF'
# Post-Quantum Cryptography (PQC) Test Rules
# These rules test PQC detection capabilities in Suricata
#
# SID Range: 9000001-9000100 (test rules)

# ============================================================================
# Basic PQC Detection Rules
# ============================================================================

# Alert on any PQC usage
alert tls any any -> any any (msg:"TEST: PQC TLS Connection Detected"; \
    tls.is_pqc; \
    classtype:protocol-command-decode; \
    sid:9000001; rev:1;)

# Alert on pure PQC (Kyber/ML-KEM only)
alert tls any any -> any any (msg:"TEST: Pure PQC Connection (Kyber Only)"; \
    tls.pqc_posture:"PQC_PURE"; \
    classtype:protocol-command-decode; \
    sid:9000002; rev:1;)

# Alert on hybrid PQC (Kyber + Classical)
alert tls any any -> any any (msg:"TEST: Hybrid PQC Connection (Kyber+ECDH)"; \
    tls.pqc_posture:"PQC_HYBRID"; \
    classtype:protocol-command-decode; \
    sid:9000003; rev:1;)

# Alert on classical-only (no PQC)
alert tls any any -> any any (msg:"TEST: Classical TLS Only (No PQC)"; \
    tls.pqc_posture:"CLASSICAL"; \
    classtype:protocol-command-decode; \
    sid:9000004; rev:1;)

# Alert on Encrypted Client Hello (ECH)
alert tls any any -> any any (msg:"TEST: Encrypted Client Hello Detected"; \
    tls.pqc_posture:"ECH_PROTECTED"; \
    classtype:protocol-command-decode; \
    sid:9000005; rev:1;)

# Alert on unknown PQC
alert tls any any -> any any (msg:"TEST: Unknown PQC Algorithm Detected"; \
    tls.pqc_posture:"UNKNOWN_PQC"; \
    classtype:protocol-command-decode; \
    sid:9000006; rev:1;)

# ============================================================================
# Specific Algorithm Detection
# ============================================================================

# ML-KEM-512 (Pure)
alert tls any any -> any any (msg:"TEST: ML-KEM-512 Detected"; \
    tls.is_pqc; \
    content:"|02 00|"; depth:2; \
    classtype:protocol-command-decode; \
    sid:9000010; rev:1;)

# ML-KEM-768 (Pure)
alert tls any any -> any any (msg:"TEST: ML-KEM-768 Detected"; \
    tls.is_pqc; \
    content:"|02 01|"; depth:2; \
    classtype:protocol-command-decode; \
    sid:9000011; rev:1;)

# ML-KEM-1024 (Pure)
alert tls any any -> any any (msg:"TEST: ML-KEM-1024 Detected"; \
    tls.is_pqc; \
    content:"|02 02|"; depth:2; \
    classtype:protocol-command-decode; \
    sid:9000012; rev:1;)

# X25519-MLKEM768 (Hybrid)
alert tls any any -> any any (msg:"TEST: X25519-MLKEM768 Hybrid Detected"; \
    tls.pqc_posture:"PQC_HYBRID"; \
    content:"|02 03|"; depth:2; \
    classtype:protocol-command-decode; \
    sid:9000013; rev:1;)

# X25519-MLKEM1024 (Hybrid)
alert tls any any -> any any (msg:"TEST: X25519-MLKEM1024 Hybrid Detected"; \
    tls.pqc_posture:"PQC_HYBRID"; \
    content:"|02 04|"; depth:2; \
    classtype:protocol-command-decode; \
    sid:9000014; rev:1;)

# P256-MLKEM768 (Hybrid)
alert tls any any -> any any (msg:"TEST: P256-MLKEM768 Hybrid Detected"; \
    tls.pqc_posture:"PQC_HYBRID"; \
    content:"|02 05|"; depth:2; \
    classtype:protocol-command-decode; \
    sid:9000015; rev:1;)

# ============================================================================
# Traffic Direction Rules
# ============================================================================

# PQC from internal to external
alert tls $HOME_NET any -> $EXTERNAL_NET 443 (msg:"TEST: Outbound PQC Connection"; \
    tls.is_pqc; \
    flow:to_server,established; \
    classtype:protocol-command-decode; \
    sid:9000020; rev:1;)

# PQC from external to internal
alert tls $EXTERNAL_NET any -> $HOME_NET any (msg:"TEST: Inbound PQC Connection"; \
    tls.is_pqc; \
    flow:to_client,established; \
    classtype:protocol-command-decode; \
    sid:9000021; rev:1;)

# ============================================================================
# Compliance and Monitoring Rules
# ============================================================================

# Monitor PQC adoption rate (limit to once per hour per source)
alert tls any any -> $EXTERNAL_NET 443 (msg:"TEST: PQC Adoption Tracking"; \
    tls.is_pqc; \
    threshold:type limit, track by_src, count 1, seconds 3600; \
    classtype:protocol-command-decode; \
    sid:9000030; rev:1;)

# Detect non-PQC connections to sensitive destinations
alert tls $HOME_NET any -> $EXTERNAL_NET 443 (msg:"TEST: Non-PQC to External (Policy Violation)"; \
    tls.pqc_posture:"CLASSICAL"; \
    metadata:policy security-baseline; \
    classtype:policy-violation; \
    sid:9000031; rev:1;)

# Track hybrid vs pure PQC usage
alert tls any any -> any any (msg:"TEST: Hybrid PQC Usage Statistics"; \
    tls.pqc_posture:"PQC_HYBRID"; \
    threshold:type limit, track by_src, count 1, seconds 3600; \
    classtype:protocol-command-decode; \
    sid:9000032; rev:1;)

alert tls any any -> any any (msg:"TEST: Pure PQC Usage Statistics"; \
    tls.pqc_posture:"PQC_PURE"; \
    threshold:type limit, track by_src, count 1, seconds 3600; \
    classtype:protocol-command-decode; \
    sid:9000033; rev:1;)

# ============================================================================
# Known PQC-Enabled Services
# ============================================================================

# Cloudflare PQC Research
alert tls any any -> any 443 (msg:"TEST: Cloudflare PQC Research Connection"; \
    tls.sni; content:"pq.cloudflareresearch.com"; \
    tls.is_pqc; \
    classtype:protocol-command-decode; \
    sid:9000040; rev:1;)

# Google PQC
alert tls any any -> any 443 (msg:"TEST: Google PQC Connection"; \
    tls.sni; content:"google.com"; \
    tls.is_pqc; \
    classtype:protocol-command-decode; \
    sid:9000041; rev:1;)

# ============================================================================
# Anomaly Detection
# ============================================================================

# Large key share (potential PQC)
alert tls any any -> any any (msg:"TEST: Unusually Large Key Share (Potential PQC)"; \
    tls.pqc_posture:"UNKNOWN_PQC"; \
    classtype:protocol-command-decode; \
    sid:9000050; rev:1;)

# ECH without PQC
alert tls any any -> any any (msg:"TEST: ECH Used Without PQC"; \
    tls.pqc_posture:"ECH_PROTECTED"; \
    classtype:protocol-command-decode; \
    sid:9000051; rev:1;)

# TLS 1.3 without PQC (informational)
alert tls any any -> any any (msg:"TEST: TLS 1.3 Without PQC Support"; \
    tls.version:"1.3"; \
    tls.pqc_posture:"CLASSICAL"; \
    threshold:type limit, track by_src, count 1, seconds 3600; \
    classtype:protocol-command-decode; \
    sid:9000052; rev:1;)

# ============================================================================
# Performance Testing Rules
# ============================================================================

# Count all TLS connections for baseline
alert tls any any -> any any (msg:"TEST: TLS Connection Baseline"; \
    flow:established; \
    threshold:type limit, track by_src, count 1, seconds 60; \
    noalert; \
    classtype:protocol-command-decode; \
    sid:9000060; rev:1;)

# Count PQC connections for comparison
alert tls any any -> any any (msg:"TEST: PQC Connection Count"; \
    tls.is_pqc; \
    threshold:type limit, track by_src, count 1, seconds 60; \
    noalert; \
    classtype:protocol-command-decode; \
    sid:9000061; rev:1;)

# ============================================================================
# Debug Rules (Verbose)
# ============================================================================

# Log all PQC postures for debugging
alert tls any any -> any any (msg:"TEST: PQC Posture Debug - Pure"; \
    tls.pqc_posture:"PQC_PURE"; \
    metadata:debug enabled; \
    noalert; \
    sid:9000070; rev:1;)

alert tls any any -> any any (msg:"TEST: PQC Posture Debug - Hybrid"; \
    tls.pqc_posture:"PQC_HYBRID"; \
    metadata:debug enabled; \
    noalert; \
    sid:9000071; rev:1;)

alert tls any any -> any any (msg:"TEST: PQC Posture Debug - Classical"; \
    tls.pqc_posture:"CLASSICAL"; \
    metadata:debug enabled; \
    noalert; \
    sid:9000072; rev:1;)

alert tls any any -> any any (msg:"TEST: PQC Posture Debug - ECH"; \
    tls.pqc_posture:"ECH_PROTECTED"; \
    metadata:debug enabled; \
    noalert; \
    sid:9000073; rev:1;)

alert tls any any -> any any (msg:"TEST: PQC Posture Debug - Unknown"; \
    tls.pqc_posture:"UNKNOWN_PQC"; \
    metadata:debug enabled; \
    noalert; \
    sid:9000074; rev:1;)

# ============================================================================
# End of PQC Test Rules
# ============================================================================
# Next available SID: 9000075
EOF

echo "✓ Created $RULES_FILE with comprehensive PQC test rules"
echo ""
echo "Rule categories:"
echo "  - Basic PQC detection (9000001-9000006)"
echo "  - Specific algorithms (9000010-9000015)"
echo "  - Traffic direction (9000020-9000021)"
echo "  - Compliance monitoring (9000030-9000033)"
echo "  - Known services (9000040-9000041)"
echo "  - Anomaly detection (9000050-9000052)"
echo "  - Performance testing (9000060-9000061)"
echo "  - Debug rules (9000070-9000074)"
echo ""
echo "To use these rules:"
echo "  1. Add to suricata.yaml rule-files section"
echo "  2. Or use: suricata -c suricata.yaml -S $RULES_FILE"
echo ""