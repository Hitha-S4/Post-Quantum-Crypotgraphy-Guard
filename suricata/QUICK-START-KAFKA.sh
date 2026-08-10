#!/bin/bash
# Complete Setup Script for Suricata + Kafka Streaming
# Just copy and paste each section into your terminal

echo "=========================================="
echo "Suricata + Kafka Streaming Setup"
echo "=========================================="
echo ""
echo "Follow these steps in order. Copy and paste each command."
echo ""

cat << 'EOF'

# ============================================
# STEP 1: Install Kafka and Filebeat
# ============================================

brew install kafka filebeat

# ============================================
# STEP 2: Start Kafka Services
# ============================================

# Start Zookeeper (required for Kafka)
brew services start zookeeper

# Wait a few seconds for Zookeeper to start
sleep 5

# Start Kafka
brew services start kafka

# Wait for Kafka to start
sleep 10

# ============================================
# STEP 3: Create Kafka Topic
# ============================================

kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic suricata-events \
  --partitions 3 \
  --replication-factor 1

# Verify topic was created
kafka-topics --list --bootstrap-server localhost:9092

# ============================================
# STEP 4: Configure Filebeat
# ============================================

# Backup original config
sudo cp /opt/homebrew/etc/filebeat/filebeat.yml /opt/homebrew/etc/filebeat/filebeat.yml.backup

# Create new Filebeat configuration
sudo tee /opt/homebrew/etc/filebeat/filebeat.yml > /dev/null << 'FILEBEAT_CONFIG'
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /Users/abisheks/Desktop/Bobathon/suricata/logs/eve.json
  json.keys_under_root: true
  json.add_error_key: true
  json.overwrite_keys: true
  fields:
    log_type: suricata
  fields_under_root: true

output.kafka:
  hosts: ["localhost:9092"]
  topic: "suricata-events"
  partition.round_robin:
    reachable_only: false
  required_acks: 1
  compression: gzip
  max_message_bytes: 1000000
  client_id: "filebeat-suricata"

logging.level: info
logging.to_files: true
logging.files:
  path: /opt/homebrew/var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
FILEBEAT_CONFIG

# Test Filebeat configuration
filebeat test config -c /opt/homebrew/etc/filebeat/filebeat.yml

# Test Kafka connection
filebeat test output -c /opt/homebrew/etc/filebeat/filebeat.yml

# ============================================
# STEP 5: Start Suricata (in Terminal 1)
# ============================================

# Open a new terminal and run:
cd /Users/abisheks/Desktop/Bobathon/suricata
sudo ./src/suricata -c suricata.yaml -i en0 -v

# ============================================
# STEP 6: Start Filebeat (in Terminal 2)
# ============================================

# Open another terminal and run:
sudo filebeat -e -c /opt/homebrew/etc/filebeat/filebeat.yml

# ============================================
# STEP 7: Generate Test Traffic (in Terminal 3)
# ============================================

# Open another terminal and run:
ping -c 10 google.com
curl http://example.com
curl http://httpbin.org/get

# ============================================
# STEP 8: View Kafka Messages (in Terminal 4)
# ============================================

# Open another terminal and run:
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic suricata-events \
  --from-beginning

# Or with pretty JSON formatting:
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic suricata-events \
  --from-beginning | jq

# ============================================
# VERIFICATION COMMANDS
# ============================================

# Check if Kafka is running
brew services list | grep kafka

# Check Kafka topics
kafka-topics --list --bootstrap-server localhost:9092

# Check topic details
kafka-topics --describe --bootstrap-server localhost:9092 --topic suricata-events

# Check Suricata logs
tail -f /Users/abisheks/Desktop/Bobathon/suricata/logs/eve.json

# Check Filebeat logs
tail -f /opt/homebrew/var/log/filebeat/filebeat

# Count messages in Kafka
kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic suricata-events

# ============================================
# STOP SERVICES (when done)
# ============================================

# Stop Suricata (Ctrl+C in Terminal 1)

# Stop Filebeat (Ctrl+C in Terminal 2)

# Stop Kafka services
brew services stop kafka
brew services stop zookeeper

# ============================================
# RESTART SERVICES (if needed)
# ============================================

# Start everything
brew services start zookeeper
sleep 5
brew services start kafka
sleep 10

# In separate terminals:
# Terminal 1: sudo ./src/suricata -c suricata.yaml -i en0 -v
# Terminal 2: sudo filebeat -e -c /opt/homebrew/etc/filebeat/filebeat.yml

EOF