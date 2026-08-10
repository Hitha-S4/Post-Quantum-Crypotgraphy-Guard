# Suricata to Kafka Streaming Guide

Complete guide for streaming Suricata logs to Apache Kafka.

---

## Overview

Suricata outputs JSON events to `logs/eve.json`. To stream these to Kafka, we'll use **Filebeat** (recommended) or alternative methods.

---

## Method 1: Filebeat (Recommended)

### Why Filebeat?
- ✅ Purpose-built for log shipping
- ✅ Lightweight and efficient
- ✅ Built-in Kafka support
- ✅ Handles backpressure and retries
- ✅ Production-ready

### Step 1: Install Filebeat

```bash
brew install filebeat
```

### Step 2: Configure Filebeat

Create or edit `/opt/homebrew/etc/filebeat/filebeat.yml`:

```yaml
# ==================== Filebeat inputs ====================
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /Users/abisheks/Desktop/Bobathon/suricata/logs/eve.json
  
  # Parse JSON events
  json.keys_under_root: true
  json.add_error_key: true
  json.overwrite_keys: true
  
  # Add custom fields
  fields:
    log_type: suricata
    environment: production
  fields_under_root: true

# ==================== Filebeat modules ====================
filebeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false

# ==================== Elasticsearch template setting ====================
setup.template.settings:
  index.number_of_shards: 1

# ==================== Kafka output ====================
output.kafka:
  # Kafka broker addresses
  hosts: ["localhost:9092"]
  
  # Kafka topic
  topic: "suricata-events"
  
  # Partitioning strategy
  partition.round_robin:
    reachable_only: false
  
  # Reliability settings
  required_acks: 1
  compression: gzip
  max_message_bytes: 1000000
  
  # Client ID
  client_id: "filebeat-suricata"
  
  # Kafka version (adjust to your Kafka version)
  version: "2.8.0"

# ==================== Processors ====================
processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~

# ==================== Logging ====================
logging.level: info
logging.to_files: true
logging.files:
  path: /opt/homebrew/var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
```

### Step 3: Start Kafka (if not running)

```bash
# Start Zookeeper
brew services start zookeeper

# Start Kafka
brew services start kafka
```

Or manually:
```bash
# Terminal 1: Start Zookeeper
zookeeper-server-start /opt/homebrew/etc/kafka/zookeeper.properties

# Terminal 2: Start Kafka
kafka-server-start /opt/homebrew/etc/kafka/server.properties
```

### Step 4: Create Kafka Topic

```bash
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic suricata-events \
  --partitions 3 \
  --replication-factor 1
```

Verify topic:
```bash
kafka-topics --list --bootstrap-server localhost:9092
```

### Step 5: Start Suricata

```bash
sudo ./src/suricata -c suricata.yaml -i en0 -v
```

### Step 6: Start Filebeat

```bash
# Test configuration
filebeat test config -c /opt/homebrew/etc/filebeat/filebeat.yml

# Test output to Kafka
filebeat test output -c /opt/homebrew/etc/filebeat/filebeat.yml

# Start Filebeat
sudo filebeat -e -c /opt/homebrew/etc/filebeat/filebeat.yml
```

Or run as service:
```bash
brew services start filebeat
```

### Step 7: Verify Events in Kafka

```bash
# Consume messages from Kafka topic
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic suricata-events \
  --from-beginning \
  --max-messages 10
```

---

## Method 2: Logstash

### Install Logstash

```bash
brew install logstash
```

### Configure Logstash

Create `logstash-suricata.conf`:

```ruby
input {
  file {
    path => "/Users/abisheks/Desktop/Bobathon/suricata/logs/eve.json"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    codec => json
    type => "suricata"
  }
}

filter {
  # Add timestamp
  date {
    match => [ "timestamp", "ISO8601" ]
  }
  
  # Add host information
  mutate {
    add_field => {
      "[@metadata][kafka_topic]" => "suricata-events"
    }
  }
}

output {
  kafka {
    bootstrap_servers => "localhost:9092"
    topic_id => "%{[@metadata][kafka_topic]}"
    codec => json
    compression_type => "gzip"
  }
  
  # Also output to stdout for debugging
  stdout {
    codec => rubydebug
  }
}
```

### Run Logstash

```bash
logstash -f logstash-suricata.conf
```

---

## Method 3: Python Script

### Install Dependencies

```bash
pip3 install kafka-python
```

### Create Script

Create `suricata_to_kafka.py`:

```python
#!/usr/bin/env python3
"""
Stream Suricata eve.json logs to Kafka
"""
import json
import time
import sys
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configuration
KAFKA_BROKERS = ['localhost:9092']
KAFKA_TOPIC = 'suricata-events'
EVE_LOG_PATH = '/Users/abisheks/Desktop/Bobathon/suricata/logs/eve.json'

def create_producer():
    """Create Kafka producer with error handling"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            compression_type='gzip',
            acks=1,
            retries=3,
            max_in_flight_requests_per_connection=5
        )
        print(f"✅ Connected to Kafka at {KAFKA_BROKERS}")
        return producer
    except KafkaError as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        sys.exit(1)

def tail_file(filename, producer):
    """Tail file and send new lines to Kafka"""
    print(f"📖 Tailing {filename}...")
    
    with open(filename, 'r') as f:
        # Go to end of file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            
            if line:
                try:
                    # Parse JSON event
                    event = json.loads(line.strip())
                    
                    # Send to Kafka
                    future = producer.send(KAFKA_TOPIC, event)
                    
                    # Wait for send to complete (optional)
                    record_metadata = future.get(timeout=10)
                    
                    print(f"✅ Sent event: {event.get('event_type', 'unknown')} "
                          f"to partition {record_metadata.partition} "
                          f"at offset {record_metadata.offset}")
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️  Invalid JSON: {e}")
                except KafkaError as e:
                    print(f"❌ Kafka error: {e}")
            else:
                # No new data, sleep briefly
                time.sleep(0.1)

def main():
    """Main function"""
    print("🚀 Starting Suricata to Kafka streamer...")
    
    # Create Kafka producer
    producer = create_producer()
    
    try:
        # Start tailing file
        tail_file(EVE_LOG_PATH, producer)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping...")
    finally:
        producer.flush()
        producer.close()
        print("✅ Shutdown complete")

if __name__ == '__main__':
    main()
```

### Run Script

```bash
chmod +x suricata_to_kafka.py
python3 suricata_to_kafka.py
```

---

## Method 4: Redis Bridge

### Configure Suricata for Redis Output

Edit [`suricata.yaml`](suricata.yaml:100):

```yaml
- eve-log:
    enabled: yes
    filetype: redis
    redis:
      server: 127.0.0.1
      port: 6379
      async: true
      mode: lpush
      key: suricata
```

### Install Redis

```bash
brew install redis
brew services start redis
```

### Use Redis to Kafka Connector

Use Kafka Connect with Redis Source Connector or create a simple bridge script.

---

## Testing & Verification

### 1. Generate Test Traffic

```bash
# Terminal 1: Run Suricata
sudo ./src/suricata -c suricata.yaml -i en0 -v

# Terminal 2: Generate traffic
ping -c 10 google.com
curl http://example.com
```

### 2. Check Suricata Logs

```bash
# View eve.json
tail -f logs/eve.json | jq

# View fast.log
tail -f logs/fast.log
```

### 3. Verify Kafka Messages

```bash
# Count messages
kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic suricata-events

# Consume and format with jq
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic suricata-events \
  --from-beginning | jq
```

### 4. Monitor Filebeat

```bash
# Check Filebeat logs
tail -f /opt/homebrew/var/log/filebeat/filebeat

# Check Filebeat status
brew services info filebeat
```

---

## Performance Tuning

### Filebeat Optimization

```yaml
# In filebeat.yml
filebeat.inputs:
- type: log
  # Increase buffer size
  harvester_buffer_size: 32768
  
  # Increase max bytes per message
  max_bytes: 10485760

output.kafka:
  # Increase workers
  worker: 2
  
  # Batch settings
  bulk_max_size: 2048
  
  # Compression
  compression: gzip
```

### Kafka Topic Configuration

```bash
# Create topic with better performance settings
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic suricata-events \
  --partitions 6 \
  --replication-factor 1 \
  --config compression.type=gzip \
  --config retention.ms=604800000
```

---

## Monitoring

### Filebeat Metrics

```bash
# Enable monitoring in filebeat.yml
monitoring.enabled: true
monitoring.elasticsearch:
  hosts: ["localhost:9200"]
```

### Kafka Metrics

```bash
# Check consumer lag
kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group filebeat-suricata

# Check topic details
kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic suricata-events
```

---

## Troubleshooting

### Filebeat Not Sending Data

```bash
# Check Filebeat logs
tail -f /opt/homebrew/var/log/filebeat/filebeat

# Test configuration
filebeat test config

# Test Kafka connection
filebeat test output
```

### Kafka Connection Issues

```bash
# Check if Kafka is running
brew services list | grep kafka

# Test Kafka connectivity
kafka-broker-api-versions --bootstrap-server localhost:9092
```

### Suricata Not Generating Logs

```bash
# Check Suricata is running
ps aux | grep suricata

# Check logs directory
ls -lh logs/

# Test configuration
./src/suricata -T -c suricata.yaml
```

---

## Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/filebeat.service`:

```ini
[Unit]
Description=Filebeat
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/filebeat -c /etc/filebeat/filebeat.yml
Restart=always

[Install]
WantedBy=multi-user.target
```

### macOS LaunchDaemon

Filebeat installed via Homebrew includes a launch daemon. Use:

```bash
brew services start filebeat
```

---

## Summary

**Recommended Setup:**
1. ✅ Run Suricata with default file output
2. ✅ Use Filebeat to stream to Kafka
3. ✅ Configure Kafka with appropriate partitions
4. ✅ Monitor with Kafka consumer groups

**Quick Start Commands:**

```bash
# Terminal 1: Start Kafka
brew services start zookeeper
brew services start kafka

# Terminal 2: Start Suricata
sudo ./src/suricata -c suricata.yaml -i en0 -v

# Terminal 3: Start Filebeat
sudo filebeat -e -c /opt/homebrew/etc/filebeat/filebeat.yml

# Terminal 4: Monitor Kafka
kafka-console-consumer --bootstrap-server localhost:9092 --topic suricata-events
```

---

**Your Suricata logs are now streaming to Kafka! 🎉**