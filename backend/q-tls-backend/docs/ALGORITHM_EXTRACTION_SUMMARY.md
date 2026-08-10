# Algorithm Extraction Summary

## Understanding the Two Message Types

### Flow Events (What You're Seeing)
```json
{
  "event_type": "flow",
  "app_proto": "tls",
  "flow": {
    "bytes_toserver": 2956,
    "bytes_toclient": 7131,
    "total_bytes": 10087
  },
  "pqc_detection": {
    "crypto_type": "post-quantum",
    "confidence": 0.8087,
    "algorithms": {
      "supported_groups": [],      // ← EMPTY (expected)
      "key_share_groups": [],       // ← EMPTY (expected)
      "signature_algorithms": [],   // ← EMPTY (expected)
      "cipher_suites": []           // ← EMPTY (expected)
    }
  }
}
```

**Why algorithms are empty:**
- Flow events only contain connection metadata (IPs, ports, byte counts)
- They do NOT contain TLS handshake details
- This is by design in Suricata - flow events track connections, not protocols

**What you get instead:**
- Byte-based heuristic classification
- 10087 bytes > 8000 threshold → classified as "post-quantum"
- Confidence: 0.8087 (heuristic-based, not algorithm-based)

### TLS Events (What Contains Algorithms)

```json
{
  "event_type": "tls",  // ← Different event type
  "tls": {
    "version": "TLS 1.3",
    "sni": "example-pqc-server.example.com",
    "pqc": {
      "supported_groups_names": ["X25519", "secp256r1", "secp384r1"],
      "key_share_groups_names": ["X25519"],
      "posture": "CLASSICAL"
    }
  },
  "pqc_detection": {
    "crypto_type": "classical",
    "confidence": 0.95,
    "algorithms": {
      "supported_groups": ["X25519", "secp256r1", "secp384r1"],  // ← POPULATED
      "key_share_groups": ["X25519"],                             // ← POPULATED
      "signature_algorithms": [],
      "cipher_suites": []
    }
  }
}
```

**Why algorithms are populated:**
- TLS events contain the actual TLS handshake
- Suricata extracts algorithms from ClientHello
- Our code parses the `tls.pqc` structure

## The Reality

### Suricata Generates TWO Events Per TLS Connection

1. **TLS Event** (when handshake occurs)
   - Contains algorithm details
   - Sent immediately after ClientHello
   - Has `event_type: "tls"`

2. **Flow Event** (when connection closes)
   - Contains byte counts and connection metadata
   - Sent when connection ends
   - Has `event_type: "flow"` with `app_proto: "tls"`

### Your WebSocket Receives BOTH

You're seeing the **flow event**, which is the second message. The **TLS event** with algorithms was sent earlier.

## How to See Algorithm Data

### Option 1: Filter for TLS Events in Frontend

Update your frontend to display both message types:

```javascript
// Show TLS events (with algorithms)
if (message.data.event_type === 'tls') {
  // Display algorithms from message.data.pqc_detection.algorithms
}

// Show flow events (with byte-based classification)
if (message.data.event_type === 'flow') {
  // Display crypto_type and confidence
  // Note: algorithms will be empty
}
```

### Option 2: Check Kafka for TLS Events

```bash
# Look for TLS events
python3 scripts/inspect_kafka_messages.py --max-messages 50 | grep -A 20 '"event_type": "tls"'
```

### Option 3: Query MongoDB

TLS events are stored in MongoDB with full algorithm details:

```javascript
db.tls_connections.find({ 
  "event_type": "tls" 
}).limit(10)
```

## Expected Behavior

| Message Type | Event Type | Algorithms | Crypto Type | Confidence |
|--------------|------------|------------|-------------|------------|
| TLS Event | `tls` | ✅ Populated | Algorithm-based | 0.70-1.00 |
| Flow Event | `flow` | ❌ Empty | Byte-based heuristic | 0.50-0.85 |

## Why This Design?

Suricata separates concerns:
- **TLS events**: Protocol analysis (algorithms, certificates, etc.)
- **Flow events**: Connection tracking (bytes, packets, duration)

This is standard Suricata behavior and cannot be changed without modifying Suricata itself.

## Solutions

### 1. Accept Current Behavior (Recommended)

- Flow events will always have empty algorithms
- Use them for byte-based classification
- Look at TLS events for algorithm details
- Both provide valuable information

### 2. Correlate Events

Match TLS and flow events by `flow_id`:

```python
# Store TLS event algorithms by flow_id
tls_algorithms = {}

if event_type == "tls":
    tls_algorithms[flow_id] = algorithms

if event_type == "flow":
    # Look up algorithms from earlier TLS event
    algorithms = tls_algorithms.get(flow_id, {})
```

### 3. Frontend Filtering

Show only TLS events in your UI if you need algorithm details:

```javascript
// Filter for TLS events only
websocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.data.event_type === 'tls') {
    // Display this message - it has algorithms
  }
};
```

## Verification

Run the inspection script and look for both types:

```bash
python3 scripts/inspect_kafka_messages.py --max-messages 50
```

You should see:
- Multiple **flow events** with empty algorithms
- Some **TLS events** with populated algorithms

## Bottom Line

**The algorithms ARE being extracted** - but only from TLS events, not flow events. This is correct behavior. Flow events will always have empty algorithms because they don't contain TLS handshake data.

If you want to see algorithms in your WebSocket messages, you need to:
1. Look for messages with `event_type: "tls"` (not "flow")
2. Or correlate flow events with their corresponding TLS events by `flow_id`
3. Or accept that flow events use byte-based heuristics without algorithm details

## Related Documentation

- [`docs/SURICATA_PQC_STRUCTURE.md`](SURICATA_PQC_STRUCTURE.md) - Explains the TLS event structure
- [`docs/BYTE_BASED_HEURISTIC_FALLBACK.md`](BYTE_BASED_HEURISTIC_FALLBACK.md) - Explains flow event classification
- [`scripts/README_INSPECT_KAFKA.md`](../scripts/README_INSPECT_KAFKA.md) - How to inspect messages