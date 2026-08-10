# Kafka Monitoring Guide for PQC Enforcement

This guide explains how to monitor PQC enforcement when Suricata logs are pushed to Kafka.

## Do I Need to Create the Kafka Topic?

**Short Answer: Usually NO** - Suricata will auto-create the topic if your Kafka broker allows it.

**Details:**

1. **Auto-creation (Default):** Most Kafka brokers have `auto.create.topics.enable=true` by default. When Suricata starts sending messages to `suricata-events`, Kafka will automatically create the topic.

2. **Manual creation (Recommended for Production):** For better control over partitions and replication, create the topic manually:

```bash
# Create topic with 3 partitions and replication factor 1
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --create \
  --topic suricata-events \
  --partitions 3 \
  --replication-factor 1

# Verify topic was created
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --list | grep suricata-events

# Check topic details
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --describe \
  --topic suricata-events
```

3. **If auto-creation is disabled:** You'll see errors in Suricata logs like:
   ```
   Error: Topic suricata-events not found
   ```
   In this case, create the topic manually using the commands above.

4. **Check if topic exists:**
```bash
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --list
```

## Kafka Configuration

Your Suricata is configured to send events to Kafka:

```yaml
output.kafka:
  enabled: true
  hosts: ["localhost:9094"]
  topic: "suricata-events"
  partition.round_robin:
    reachable_only: false
  required_acks: 1
  compression: gzip
  max_message_bytes: 1000000
```

## Method 1: Using Kafka Console Consumer

### Check All Messages

```bash
# Connect to Kafka and consume messages from the beginning
kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events \
  --from-beginning

# Or consume only new messages
kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events
```

### Filter for PQC-Related Events

```bash
# Filter for TLS events with PQC posture
kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events \
  --from-beginning | jq 'select(.event_type=="tls") | {timestamp, src_ip, dest_ip, pqc_posture: .tls.pqc_posture}'

# Filter for non-PQC alerts
kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events \
  --from-beginning | jq 'select(.alert.signature_id==1000001 or .alert.signature_id==1000010)'

# Count PQC vs Classical connections
kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events \
  --from-beginning | jq -r 'select(.event_type=="tls") | .tls.pqc_posture' | sort | uniq -c
```

## Method 2: Using kafkacat (kcat)

### Install kafkacat

```bash
# Ubuntu/Debian
sudo apt-get install kafkacat

# macOS
brew install kafkacat

# Or use kcat (newer name)
brew install kcat
```

### Monitor Messages

```bash
# Consume messages in real-time
kafkacat -b localhost:9094 -t suricata-events -C

# With JSON formatting
kafkacat -b localhost:9094 -t suricata-events -C | jq .

# Filter for PQC events
kafkacat -b localhost:9094 -t suricata-events -C | \
  jq 'select(.event_type=="tls" and .tls.pqc_posture != null)'

# Monitor dropped non-PQC connections
kafkacat -b localhost:9094 -t suricata-events -C | \
  jq 'select(.alert.signature=="Dropping non-PQC TLS connection")'
```

## Method 3: Using Python Consumer

### Install Dependencies

```bash
pip install kafka-python
```

### Python Script to Monitor PQC Events

```python
#!/usr/bin/env python3
from kafka import KafkaConsumer
import json
from collections import Counter

# Create consumer
consumer = KafkaConsumer(
    'suricata-events',
    bootstrap_servers=['localhost:9094'],
    auto_offset_reset='latest',  # or 'earliest' to read from beginning
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("Monitoring PQC events from Kafka...")
print("-" * 80)

pqc_stats = Counter()

try:
    for message in consumer:
        event = message.value
        
        # Filter for TLS events
        if event.get('event_type') == 'tls':
            tls = event.get('tls', {})
            pqc_posture = tls.get('pqc_posture')
            
            if pqc_posture:
                pqc_stats[pqc_posture] += 1
                
                print(f"\n[{event.get('timestamp')}]")
                print(f"  {event.get('src_ip')}:{event.get('src_port')} -> "
                      f"{event.get('dest_ip')}:{event.get('dest_port')}")
                print(f"  PQC Posture: {pqc_posture}")
                
                if pqc_posture == 'CLASSICAL':
                    print(f"  ⚠️  NON-PQC CONNECTION DETECTED")
                
                # Print stats every 10 events
                if sum(pqc_stats.values()) % 10 == 0:
                    print(f"\n--- Statistics ---")
                    for posture, count in pqc_stats.items():
                        print(f"  {posture}: {count}")
        
        # Filter for PQC-related alerts
        elif event.get('event_type') == 'alert':
            alert = event.get('alert', {})
            sig_id = alert.get('signature_id')
            
            # Check for PQC enforcement alerts (1000001-1000032)
            if 1000001 <= sig_id <= 1000032:
                print(f"\n🚨 [{event.get('timestamp')}]")
                print(f"  Alert: {alert.get('signature')}")
                print(f"  Action: {alert.get('action')}")
                print(f"  {event.get('src_ip')} -> {event.get('dest_ip')}")

except KeyboardInterrupt:
    print("\n\nFinal Statistics:")
    print("-" * 80)
    for posture, count in pqc_stats.items():
        print(f"{posture}: {count}")
    consumer.close()
```

Save as `monitor_pqc_kafka.py` and run:

```bash
python3 monitor_pqc_kafka.py
```

## Method 4: Using Kafka Streams or KSQL

### KSQL Queries

```sql
-- Create stream from Kafka topic
CREATE STREAM suricata_events (
  timestamp VARCHAR,
  event_type VARCHAR,
  src_ip VARCHAR,
  dest_ip VARCHAR,
  tls STRUCT<pqc_posture VARCHAR>
) WITH (
  KAFKA_TOPIC='suricata-events',
  VALUE_FORMAT='JSON'
);

-- Query for non-PQC connections
SELECT timestamp, src_ip, dest_ip, tls->pqc_posture
FROM suricata_events
WHERE event_type = 'tls' 
  AND tls->pqc_posture = 'CLASSICAL'
EMIT CHANGES;

-- Count PQC postures
SELECT tls->pqc_posture, COUNT(*) as count
FROM suricata_events
WHERE event_type = 'tls'
GROUP BY tls->pqc_posture
EMIT CHANGES;
```

## Method 5: Verify Kafka Integration

### Check if Messages are Being Sent

```bash
# Check topic exists
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --list | grep suricata-events

# Check topic details
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --describe \
  --topic suricata-events

# Check consumer group lag
kafka-consumer-groups.sh \
  --bootstrap-server localhost:9094 \
  --describe \
  --group suricata-consumer-group
```

### Check Suricata Kafka Output Status

```bash
# Check Suricata logs for Kafka errors
tail -f /var/log/suricata/suricata.log | grep -i kafka

# Check stats
tail -f /var/log/suricata/stats.log | grep -i kafka
```

## Expected Message Format

### TLS Event with PQC Posture

```json
{
  "timestamp": "2026-02-09T12:00:00.000000+0000",
  "flow_id": 123456789,
  "event_type": "tls",
  "src_ip": "192.168.1.10",
  "src_port": 54321,
  "dest_ip": "93.184.216.34",
  "dest_port": 443,
  "proto": "TCP",
  "tls": {
    "version": "TLS 1.3",
    "pqc_posture": "CLASSICAL",
    "pqc_details": {
      "supported_groups": ["x25519", "secp256r1"],
      "key_share_groups": ["x25519"],
      "has_pqc_groups": false,
      "has_classical_groups": true
    },
    "sni": "example.com"
  }
}
```

### Alert for Dropped Non-PQC Connection

```json
{
  "timestamp": "2026-02-09T12:00:01.000000+0000",
  "flow_id": 123456790,
  "event_type": "alert",
  "src_ip": "192.168.1.10",
  "dest_ip": "93.184.216.34",
  "alert": {
    "action": "blocked",
    "gid": 1,
    "signature_id": 1000010,
    "signature": "Dropping non-PQC TLS connection",
    "category": "Policy Violation",
    "severity": 2
  },
  "tls": {
    "pqc_posture": "CLASSICAL"
  }
}
```

## Monitoring Dashboard Queries

### Real-time PQC Statistics

```bash
# Create a simple monitoring script
cat > monitor_pqc_stats.sh << 'EOF'
#!/bin/bash

echo "PQC TLS Monitoring Dashboard"
echo "=============================="
echo ""

while true; do
  clear
  echo "Last 100 TLS connections:"
  echo ""
  
  kafkacat -b localhost:9094 -t suricata-events -C -e -o -100 | \
    jq -r 'select(.event_type=="tls") | .tls.pqc_posture' | \
    sort | uniq -c | \
    awk '{printf "%-20s: %5d\n", $2, $1}'
  
  echo ""
  echo "Dropped connections in last minute:"
  kafkacat -b localhost:9094 -t suricata-events -C -e -o -100 | \
    jq -r 'select(.alert.signature_id==1000010)' | wc -l
  
  echo ""
  echo "Press Ctrl+C to exit"
  sleep 5
done
EOF

chmod +x monitor_pqc_stats.sh
./monitor_pqc_stats.sh
```

## Troubleshooting

### No Messages in Kafka

1. **Check Suricata Kafka output is enabled:**
   ```bash
   grep -A 10 "output.kafka" /etc/suricata/suricata.yaml
   ```

2. **Check Suricata is running:**
   ```bash
   ps aux | grep suricata
   ```

3. **Check network connectivity:**
   ```bash
   telnet localhost 9094
   ```

4. **Check Suricata logs:**
   ```bash
   tail -f /var/log/suricata/suricata.log | grep -i "kafka\|error"
   ```

### Messages Not Showing PQC Data

1. **Verify PQC detection is working:**
   ```bash
   # Check local eve.json first
   tail -f /var/log/suricata/eve.json | jq 'select(.tls.pqc_posture != null)'
   ```

2. **Check if TLS traffic is being processed:**
   ```bash
   kafkacat -b localhost:9094 -t suricata-events -C | \
     jq 'select(.event_type=="tls")' | head -5
   ```

## Integration with Monitoring Tools

### Grafana Dashboard

Create a Grafana dashboard using Kafka data source:
- Panel 1: PQC Posture Distribution (Pie Chart)
- Panel 2: Non-PQC Connections Over Time (Time Series)
- Panel 3: Dropped Connections (Counter)
- Panel 4: Top Non-PQC Destinations (Table)

### Elasticsearch Integration

If you're using Logstash to forward Kafka to Elasticsearch:

```ruby
input {
  kafka {
    bootstrap_servers => "localhost:9094"
    topics => ["suricata-events"]
    codec => json
  }
}

filter {
  if [event_type] == "tls" {
    mutate {
      add_tag => ["tls"]
    }
    if [tls][pqc_posture] == "CLASSICAL" {
      mutate {
        add_tag => ["non-pqc"]
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "suricata-pqc-%{+YYYY.MM.dd}"
  }
}
```

## Quick Reference Commands

```bash
# Real-time monitoring
kafkacat -b localhost:9094 -t suricata-events -C | jq .

# Count PQC types
kafkacat -b localhost:9094 -t suricata-events -C -e | \
  jq -r 'select(.tls.pqc_posture) | .tls.pqc_posture' | sort | uniq -c

# Find dropped connections
kafkacat -b localhost:9094 -t suricata-events -C | \
  jq 'select(.alert.signature_id==1000010)'

# Monitor specific IP
kafkacat -b localhost:9094 -t suricata-events -C | \
  jq 'select(.src_ip=="192.168.1.10" or .dest_ip=="192.168.1.10")'