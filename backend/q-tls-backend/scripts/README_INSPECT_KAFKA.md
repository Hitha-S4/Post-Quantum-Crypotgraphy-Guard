# Kafka Message Inspector

This script inspects raw Kafka messages to understand the actual data structure and identify why algorithms might be empty.

## Usage

### Basic Usage (uses settings from .env)

```bash
python3 scripts/inspect_kafka_messages.py
```

Or using the shell wrapper:

```bash
./scripts/inspect_kafka_messages.sh
```

### With Custom Parameters

```bash
# Inspect 20 messages
python3 scripts/inspect_kafka_messages.py --max-messages 20

# Use different Kafka server
python3 scripts/inspect_kafka_messages.py --bootstrap-servers localhost:9092

# Use different topic
python3 scripts/inspect_kafka_messages.py --topic my-tls-logs

# Combine options
python3 scripts/inspect_kafka_messages.py --max-messages 50 --topic suricata-events
```

## What It Does

1. **Connects to Kafka** using settings from `.env` file
2. **Reads messages** from the configured topic
3. **Analyzes each message** for:
   - Event type (tls, flow, etc.)
   - App protocol (tls, tcp, etc.)
   - Presence of `tls` section
   - TLS algorithm fields (supported_groups, key_share, signature_algorithms)
   - Flow data (byte counts)
4. **Prints detailed information** about each message
5. **Provides summary** of findings

## Expected Output

### If TLS Data is Present

```
================================================================================
MESSAGE #1
================================================================================
Event Type: tls
App Proto: tls
Connection: 192.168.1.100 → 104.18.11.13:443
Has 'tls' section: True

TLS Section Keys: ['version', 'sni', 'supported_groups', 'key_share', 'signature_algorithms']
  - supported_groups: True
    Value: ['x25519', 'secp256r1', 'secp384r1']
  - key_share: True
    Value: ['x25519']
  - signature_algorithms: True
    Value: ['ecdsa_secp256r1_sha256', 'rsa_pss_rsae_sha256']
  - ja3: True
    Hash: abc123...

Flow Data:
  - Bytes to server: 2227
  - Bytes to client: 4851
  - Total bytes: 7078
```

### If TLS Data is Missing

```
================================================================================
MESSAGE #1
================================================================================
Event Type: flow
App Proto: tls
Connection: 9.109.217.201 → 104.18.11.13:443
Has 'tls' section: False

Flow Data:
  - Bytes to server: 4451
  - Bytes to client: 2514
  - Total bytes: 6965

⚠️  WARNING: No messages contain TLS algorithm data!
   This means Suricata is NOT capturing TLS handshake details.
   You need to enable extended TLS logging in Suricata configuration.
```

## Troubleshooting

### Connection Error

```
❌ Kafka Error: NoBrokersAvailable
```

**Solution**: Check that Kafka is running and the bootstrap servers in `.env` are correct.

### No Messages Received

```
Waiting for messages (30s timeout)...
Total messages inspected: 0
```

**Solution**: 
1. Check that traffic is flowing through Suricata
2. Verify the topic name in `.env` is correct
3. Try changing `KAFKA_AUTO_OFFSET_RESET` to "latest" in `.env`

### Messages Have No TLS Section

```
Has 'tls' section: False
```

**Solution**: This is the root cause of empty algorithms. See [`docs/SURICATA_TLS_CONFIG.md`](../docs/SURICATA_TLS_CONFIG.md) for Suricata configuration.

## Configuration

The script uses settings from your `.env` file:

```env
KAFKA_BOOTSTRAP_SERVERS="localhost:9094"
KAFKA_TOPIC_TLS_LOGS="suricata-events"
```

You can override these with command-line arguments if needed.

## Next Steps

After running this script:

1. **If TLS data is present**: The system should work correctly
2. **If TLS data is missing**: Configure Suricata as described in [`docs/SURICATA_TLS_CONFIG.md`](../docs/SURICATA_TLS_CONFIG.md)
3. **If only flow events**: Check if Suricata is configured to log TLS events separately

## Related Files

- [`scripts/inspect_kafka_messages.py`](inspect_kafka_messages.py) - Main inspection script
- [`scripts/inspect_kafka_messages.sh`](inspect_kafka_messages.sh) - Shell wrapper
- [`docs/SURICATA_TLS_CONFIG.md`](../docs/SURICATA_TLS_CONFIG.md) - Suricata configuration guide
- [`src/ngfw_pqc_detector/core/config.py`](../src/ngfw_pqc_detector/core/config.py) - Settings configuration