#!/bin/bash
# View PQC TLS events from Suricata logs in real-time

echo "=========================================="
echo "PQC TLS Event Monitor"
echo "=========================================="
echo ""
echo "Watching logs/eve.json for TLS events with PQC detection..."
echo "Press Ctrl+C to stop"
echo ""
echo "Waiting for TLS connections..."
echo ""

# Monitor for TLS events and display PQC information
tail -f logs/eve.json | jq --unbuffered -r '
  select(.event_type=="tls") |
  "
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Time:        \(.timestamp)
🌐 Connection:  \(.src_ip):\(.src_port) → \(.dest_ip):\(.dest_port)
🔒 TLS:         \(.tls.version // "unknown")
📝 SNI:         \(.tls.sni // "none")
🔐 PQC Posture: \(.tls.pqc.posture // "UNKNOWN")
✨ Is PQC:      \(.tls.pqc.is_pqc // false)
🛡️  Has ECH:     \(.tls.pqc.has_ech // false)
📊 Groups:      \(.tls.pqc.supported_groups // [] | join(", "))
📋 Group Names: \(.tls.pqc.supported_groups_names // [] | join(", "))
🔑 Key Shares:  \(.tls.pqc.key_share_groups_names // [] | join(", "))
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  "
'