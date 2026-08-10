# Kafka Consumer Stuck - Troubleshooting Guide

## Issue: kafka-console-consumer Hangs/Stuck

When you run:
```bash
kafka-console-consumer \
  --bootstrap-server localhost:9094 \
  --topic suricata-events \
  --from-beginning
```

And it appears stuck with no output, here's what to check:

## Quick Diagnostics

### 1. Check if Topic Exists and Has Data

```bash
# List all topics
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --list

# Check topic details (partitions, replicas)
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --describe \
  --topic suricata-events

# Check if topic has any messages
kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9094 \
  --topic suricata-events
```

**Expected output if topic has data:**
```
suricata-events:0:1234
suricata-events:1:5678
suricata-events:2:9012
```

If all show `:0`, the topic is empty (no messages yet).

### 2. Check Network Connectivity

```bash
# Test connection to Kafka broker
telnet localhost 9094

# Or using nc
nc -zv localhost 9094

# Check if port is reachable
timeout 5 bash -c 'cat < /dev/null > /dev/tcp/localhost/9094' && echo "Port is open" || echo "Port is closed"
```

### 3. Check if Suricata is Running and Sending Data

```bash
# Check if Suricata is running
ps aux | grep suricata

# Check Suricata logs for Kafka errors
tail -100 /var/log/suricata/suricata.log | grep -i kafka

# Check if Kafka output is enabled in config
grep -A 10 "output.kafka" /etc/suricata/suricata.yaml

# Check Suricata stats for Kafka
tail -f /var/log/suricata/stats.log | grep -i kafka
```

### 4. Try Alternative Consumer Methods

**Method A: Use kafkacat (more verbose)**
```bash
# Install kafkacat if not present
# macOS: brew install kafkacat
# Ubuntu: sudo apt-get install kafkacat

# Try consuming with kafkacat
kafkacat -b localhost:9094 -t suricata-events -C -o beginning

# With debug output
kafkacat -b localhost:9094 -t suricata-events -C -o beginning -d broker,topic
```

**Method B: Consume only new messages (not from beginning)**
```bash
# This will wait for new messages
kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events
```

**Method C: Add timeout**
```bash
# Exit after 10 seconds if no messages
timeout 10 kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events \
  --from-beginning
```

### 5. Check Consumer Group Status

```bash
# List consumer groups
kafka-consumer-groups.sh \
  --bootstrap-server localhost:9094 \
  --list

# Check specific consumer group
kafka-consumer-groups.sh \
  --bootstrap-server localhost:9094 \
  --describe \
  --group console-consumer-12345  # Replace with actual group ID
```

## Common Causes and Solutions

### Cause 1: Topic is Empty (No Messages Yet)

**Symptoms:**
- Consumer connects but shows no output
- `GetOffsetShell` shows all partitions at offset 0

**Solution:**
```bash
# Generate some traffic to trigger Suricata events
curl https://example.com

# Or generate TLS traffic
openssl s_client -connect example.com:443 -brief

# Check if messages appear
kafkacat -b localhost:9094 -t suricata-events -C
```

### Cause 2: Suricata Not Sending to Kafka

**Symptoms:**
- Topic exists but is empty
- Suricata logs show Kafka errors

**Solution:**
```bash
# Check Suricata Kafka configuration
cat /etc/suricata/suricata.yaml | grep -A 15 "output.kafka"

# Ensure it's enabled:
# output.kafka:
#   enabled: true

# Restart Suricata
sudo systemctl restart suricata

# Or reload config
sudo kill -USR2 $(pidof suricata)

# Monitor logs
tail -f /var/log/suricata/suricata.log | grep -i kafka
```

### Cause 3: Network/Firewall Issues

**Symptoms:**
- Connection timeout
- "Connection refused" errors

**Solution:**
```bash
# Check firewall rules
sudo iptables -L -n | grep 9094

# Check if broker is listening
sudo netstat -tlnp | grep 9094

# Try from different network/machine
ssh other-machine "kafkacat -b localhost:9094 -L"
```

### Cause 4: Authentication/SSL Issues

**Symptoms:**
- Connection established but no data
- SSL/TLS errors in logs

**Solution:**
```bash
# Check if broker requires SSL/SASL
# Add security config if needed:

kafka-console-consumer.sh \
  --bootstrap-server localhost:9094 \
  --topic suricata-events \
  --consumer-property security.protocol=SSL \
  --consumer-property ssl.truststore.location=/path/to/truststore.jks \
  --consumer-property ssl.truststore.password=password
```

### Cause 5: Wrong Topic Name

**Symptoms:**
- Consumer waits indefinitely
- Topic doesn't exist

**Solution:**
```bash
# List all topics to verify name
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --list

# Check Suricata config for exact topic name
grep "topic:" /etc/suricata/suricata.yaml
```

## Step-by-Step Debugging

### Step 1: Verify Kafka Broker is Reachable
```bash
echo "Testing connection..."
timeout 5 bash -c 'cat < /dev/null > /dev/tcp/localhost/9094' && \
  echo "✓ Broker is reachable" || \
  echo "✗ Cannot reach broker"
```

### Step 2: Check Topic Exists
```bash
echo "Checking topic..."
kafka-topics.sh \
  --bootstrap-server localhost:9094 \
  --list | grep -q "suricata-events" && \
  echo "✓ Topic exists" || \
  echo "✗ Topic does not exist"
```

### Step 3: Check Topic Has Messages
```bash
echo "Checking for messages..."
OFFSETS=$(kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9094 \
  --topic suricata-events 2>/dev/null)

if echo "$OFFSETS" | grep -v ":0$" > /dev/null; then
  echo "✓ Topic has messages"
  echo "$OFFSETS"
else
  echo "✗ Topic is empty (no messages yet)"
fi
```

### Step 4: Check Suricata is Sending
```bash
echo "Checking Suricata..."
if ps aux | grep -v grep | grep suricata > /dev/null; then
  echo "✓ Suricata is running"
  
  # Check if Kafka output is enabled
  if grep -q "enabled: true" /etc/suricata/suricata.yaml; then
    echo "✓ Kafka output is enabled"
  else
    echo "✗ Kafka output may be disabled"
  fi
else
  echo "✗ Suricata is not running"
fi
```

### Step 5: Generate Test Traffic
```bash
echo "Generating test traffic..."
curl -s https://example.com > /dev/null && echo "✓ Generated HTTPS traffic"

# Wait a moment for Suricata to process
sleep 2

# Try consuming again
echo "Attempting to consume messages..."
timeout 5 kafkacat -b localhost:9094 -t suricata-events -C -e -o beginning
```

## Quick Fix Script

Save this as `test_kafka.sh`:

```bash
#!/bin/bash

BROKER="localhost:9094"
TOPIC="suricata-events"

echo "=== Kafka Connectivity Test ==="
echo ""

# Test 1: Broker connectivity
echo "1. Testing broker connectivity..."
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${BROKER%:*}/${BROKER#*:}" 2>/dev/null; then
    echo "   ✓ Broker is reachable"
else
    echo "   ✗ Cannot reach broker"
    exit 1
fi

# Test 2: List topics
echo ""
echo "2. Listing topics..."
TOPICS=$(kafka-topics.sh --bootstrap-server $BROKER --list 2>/dev/null)
if echo "$TOPICS" | grep -q "$TOPIC"; then
    echo "   ✓ Topic '$TOPIC' exists"
else
    echo "   ✗ Topic '$TOPIC' not found"
    echo "   Available topics:"
    echo "$TOPICS" | sed 's/^/     /'
    exit 1
fi

# Test 3: Check for messages
echo ""
echo "3. Checking for messages..."
OFFSETS=$(kafka-run-class.sh kafka.tools.GetOffsetShell \
    --broker-list $BROKER \
    --topic $TOPIC 2>/dev/null)

if echo "$OFFSETS" | grep -v ":0$" > /dev/null; then
    echo "   ✓ Topic has messages:"
    echo "$OFFSETS" | sed 's/^/     /'
else
    echo "   ⚠ Topic is empty"
    echo "   Generating test traffic..."
    curl -s https://example.com > /dev/null
    sleep 3
    
    OFFSETS=$(kafka-run-class.sh kafka.tools.GetOffsetShell \
        --broker-list $BROKER \
        --topic $TOPIC 2>/dev/null)
    
    if echo "$OFFSETS" | grep -v ":0$" > /dev/null; then
        echo "   ✓ Messages appeared after generating traffic"
    else
        echo "   ✗ Still no messages - check Suricata configuration"
    fi
fi

# Test 4: Try consuming
echo ""
echo "4. Attempting to consume messages..."
echo "   (Will timeout after 5 seconds if no messages)"
timeout 5 kafkacat -b $BROKER -t $TOPIC -C -e -o beginning 2>/dev/null | head -5

echo ""
echo "=== Test Complete ==="
```

Run it:
```bash
chmod +x test_kafka.sh
./test_kafka.sh
```

## If Still Stuck

1. **Check Suricata is actually processing traffic:**
   ```bash
   tail -f /var/log/suricata/eve.json
   ```
   If you see events here but not in Kafka, it's a Kafka output issue.

2. **Enable Kafka debug logging in Suricata:**
   Edit `/etc/suricata/suricata.yaml`:
   ```yaml
   logging:
     outputs:
       - console:
           enabled: yes
           level: debug
   ```
   Restart Suricata and check logs.

3. **Try a different consumer:**
   ```bash
   # Python consumer
   pip install kafka-python
   python3 -c "
   from kafka import KafkaConsumer
   consumer = KafkaConsumer('suricata-events',
       bootstrap_servers=['localhost:9094'],
       auto_offset_reset='earliest')
   for msg in consumer:
       print(msg.value)
       break
   "
   ```

4. **Check Kafka broker logs** (if you have access):
   ```bash
   # On Kafka broker machine
   tail -f /var/log/kafka/server.log | grep suricata-events