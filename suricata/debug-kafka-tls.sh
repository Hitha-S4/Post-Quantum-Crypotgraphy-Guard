#!/bin/bash
# Debug script to see the actual TLS event structure from Kafka

KAFKA_BROKER="localhost:9094"
KAFKA_TOPIC="suricata-events"

echo "Fetching a few TLS events to inspect structure..."
echo ""

kafka-console-consumer \
  --bootstrap-server "$KAFKA_BROKER" \
  --topic "$KAFKA_TOPIC" \
  --max-messages 50 \
  --from-beginning 2>/dev/null | jq 'select(.event_type == "tls") | {
    timestamp,
    src_ip,
    src_port,
    dest_ip,
    dest_port,
    tls: .tls
  }' | head -100