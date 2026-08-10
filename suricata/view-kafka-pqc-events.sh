#!/bin/bash
# View PQC TLS events from Kafka in real-time
# Reads from Kafka topic and displays in the same format as view-pqc-events.sh

# Configuration from filebeat-updated.yml
KAFKA_BROKER="localhost:9094"
KAFKA_TOPIC="suricata-events"

echo "=========================================="
echo "PQC TLS Event Monitor (Kafka)"
echo "=========================================="
echo ""
echo "Reading from Kafka topic: $KAFKA_TOPIC"
echo "Kafka broker: $KAFKA_BROKER"
echo "Press Ctrl+C to stop"
echo ""
echo "Waiting for TLS connections..."
echo ""

# Check if kafka-console-consumer is available
if ! command -v kafka-console-consumer &> /dev/null; then
    echo "❌ Error: kafka-console-consumer not found"
    echo "Please install Kafka or ensure it's in your PATH"
    echo ""
    echo "Installation options:"
    echo "  - macOS: brew install kafka"
    echo "  - Linux: Download from https://kafka.apache.org/downloads"
    exit 1
fi

# Consume from Kafka and filter TLS events with PQC information
# Note: Kafka messages from Filebeat include metadata wrapping, so we need to handle both formats
kafka-console-consumer \
  --bootstrap-server "$KAFKA_BROKER" \
  --topic "$KAFKA_TOPIC" \
  --from-beginning 2>/dev/null | jq --unbuffered -r '
  # Handle both direct Suricata events and Filebeat-wrapped events
  if .event_type == "tls" then
    # Direct Suricata event format
    "
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Time:        \(.timestamp)
🌐 Connection:  \(.src_ip):\(.src_port) → \(.dest_ip):\(.dest_port)
🔒 TLS:         \(.tls.version // "unknown")
📝 SNI:         \(.tls.sni // "none")
🔐 PQC Posture: \(.tls.pqc.posture // "UNKNOWN")
✨ Is PQC:      \(if .tls.pqc.is_pqc then "true" else "false" end)
🛡️  Has ECH:     \(if .tls.pqc.has_ech then "true" else "false" end)
📊 Groups:      \(if .tls.pqc.supported_groups then (.tls.pqc.supported_groups | map(tostring) | join(", ")) else "" end)
📋 Group Names: \(if .tls.pqc.supported_groups_names then (.tls.pqc.supported_groups_names | join(", ")) else "" end)
🔑 Key Shares:  \(if .tls.pqc.key_share_groups_names then (.tls.pqc.key_share_groups_names | join(", ")) else "" end)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "
  else
    empty
  end
'