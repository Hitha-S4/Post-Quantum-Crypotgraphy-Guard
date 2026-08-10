# Suricata PQC Structure Analysis

## Discovery

After inspecting actual Kafka messages, we found that Suricata **does** provide TLS algorithm data, but in a different structure than expected.

## Message Types

### 1. Flow Events (event_type: "flow")
These contain connection metadata but **no TLS handshake details**:

```json
{
  "event_type": "flow",
  "app_proto": "tls",
  "flow": {
    "bytes_toserver": 4602,
    "bytes_toclient": 2602,
    "total_bytes": 7204
  }
  // NO tls section
}
```

**Handling**: Use byte-based heuristic fallback (see [`BYTE_BASED_HEURISTIC_FALLBACK.md`](BYTE_BASED_HEURISTIC_FALLBACK.md))

### 2. TLS Events (event_type: "tls")
These contain the actual TLS handshake data in a **new `tls.pqc` structure**:

```json
{
  "event_type": "tls",
  "tls": {
    "version": "TLS 1.3",
    "sni": "example-pqc-server.example.com",
    "client_alpns": ["http/1.1"],
    "ja4": "t13d1812h1_5d04281c6031_d5fe2c511efa",
    "pqc": {
      "has_ech": false,
      "supported_groups": [29, 23, 24],
      "supported_groups_names": ["X25519", "secp256r1", "secp384r1"],
      "key_share_groups": [29],
      "key_share_groups_names": ["X25519"],
      "posture": "CLASSICAL",
      "is_pqc": false
    }
  }
}
```

## New PQC Structure

### Fields in `tls.pqc`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `has_ech` | boolean | Encrypted Client Hello support | `false` |
| `supported_groups` | array[int] | Numeric codes for supported groups | `[29, 23, 24]` |
| `supported_groups_names` | array[string] | Human-readable group names | `["X25519", "secp256r1", "secp384r1"]` |
| `key_share_groups` | array[int] | Numeric codes for key share groups | `[29]` |
| `key_share_groups_names` | array[string] | Human-readable key share names | `["X25519"]` |
| `posture` | string | PQC posture classification | `"CLASSICAL"`, `"PQC"`, `"HYBRID"` |
| `is_pqc` | boolean | Whether connection uses PQC | `false` |

### Group Code Mappings

Common TLS group codes:

| Code | Name | Type |
|------|------|------|
| 23 | secp256r1 | Classical ECDH |
| 24 | secp384r1 | Classical ECDH |
| 25 | secp521r1 | Classical ECDH |
| 29 | X25519 | Classical ECDH |
| 30 | X448 | Classical ECDH |
| 0x2F39 | mlkem512 | PQC |
| 0x2F3A | mlkem768 | PQC |
| 0x2F3B | mlkem1024 | PQC |

## Implementation Changes

### Updated `_parse_client_hello()` Method

The method now extracts algorithms from the new `tls.pqc` structure:

```python
def _parse_client_hello(self, tls_data: dict):
    pqc_data = tls_data.get("pqc", {})
    
    # Extract supported groups (prefer human-readable names)
    supported_groups = []
    if pqc_data.get("supported_groups_names"):
        supported_groups = pqc_data.get("supported_groups_names", [])
    elif pqc_data.get("supported_groups"):
        supported_groups = [str(g) for g in pqc_data.get("supported_groups", [])]
    
    # Extract key share groups (prefer human-readable names)
    key_share_groups = []
    if pqc_data.get("key_share_groups_names"):
        key_share_groups = pqc_data.get("key_share_groups_names", [])
    elif pqc_data.get("key_share_groups"):
        key_share_groups = [str(g) for g in pqc_data.get("key_share_groups", [])]
```

## Example Messages

### Classical TLS 1.3 Connection

```json
{
  "event_type": "tls",
  "src_ip": "9.109.217.201",
  "dest_ip": "104.18.11.13",
  "dest_port": 443,
  "tls": {
    "version": "TLS 1.3",
    "sni": "example-pqc-server.example.com",
    "pqc": {
      "supported_groups_names": ["X25519", "secp256r1", "secp384r1"],
      "key_share_groups_names": ["X25519"],
      "posture": "CLASSICAL",
      "is_pqc": false
    }
  }
}
```

**Detection Result:**
- Crypto Type: `classical`
- Algorithms: `["X25519", "secp256r1", "secp384r1"]`
- Key Share: `["X25519"]`
- Confidence: High (algorithm-based)

### PQC-Enabled Connection (Example)

```json
{
  "event_type": "tls",
  "tls": {
    "version": "TLS 1.3",
    "pqc": {
      "supported_groups_names": ["mlkem768", "X25519", "secp256r1"],
      "key_share_groups_names": ["mlkem768"],
      "posture": "PQC",
      "is_pqc": true
    }
  }
}
```

**Detection Result:**
- Crypto Type: `post-quantum`
- Algorithms: `["mlkem768", "X25519", "secp256r1"]`
- Key Share: `["mlkem768"]`
- Confidence: High (algorithm-based)

### Hybrid Connection (Example)

```json
{
  "event_type": "tls",
  "tls": {
    "version": "TLS 1.3",
    "pqc": {
      "supported_groups_names": ["X25519_mlkem768", "X25519", "secp256r1"],
      "key_share_groups_names": ["X25519_mlkem768"],
      "posture": "HYBRID",
      "is_pqc": true
    }
  }
}
```

**Detection Result:**
- Crypto Type: `hybrid`
- Algorithms: `["X25519_mlkem768", "X25519", "secp256r1"]`
- Key Share: `["X25519_mlkem768"]`
- Confidence: High (algorithm-based)

## Message Flow

1. **TLS Handshake Occurs**
   - Client sends ClientHello with supported algorithms
   - Suricata captures and analyzes the handshake

2. **Suricata Generates TLS Event**
   - `event_type: "tls"`
   - Includes `tls.pqc` structure with algorithm details
   - Sent to Kafka immediately

3. **Connection Completes**
   - Suricata generates flow event
   - `event_type: "flow"` with `app_proto: "tls"`
   - Contains byte counts but no algorithm details

4. **Our System Processes Both**
   - TLS events: Full algorithm-based detection
   - Flow events: Byte-based heuristic fallback

## Benefits of New Structure

✅ **Human-Readable Names**: `"X25519"` instead of `29`  
✅ **Pre-Classified**: Suricata provides `posture` field  
✅ **Complete Data**: Both numeric codes and names available  
✅ **ECH Support**: Indicates Encrypted Client Hello capability  
✅ **Clear PQC Flag**: `is_pqc` boolean for quick checks  

## Suricata Configuration

This structure appears to be from a newer version of Suricata with PQC detection capabilities. Ensure you have:

```yaml
# suricata.yaml
app-layer:
  protocols:
    tls:
      enabled: yes
      ja3-fingerprints: yes
      ja4-fingerprints: yes  # New: JA4 fingerprinting
      
outputs:
  - eve-log:
      types:
        - tls:
            enabled: yes
            extended: yes
```

## Verification

To verify your Suricata is generating these events:

```bash
# Check for TLS events with PQC data
tail -f /var/log/suricata/eve.json | jq 'select(.event_type=="tls") | .tls.pqc'

# Or use our inspection script
python3 scripts/inspect_kafka_messages.py --max-messages 20
```

## Related Files

- [`src/ngfw_pqc_detector/services/kafka_consumer.py:354`](../src/ngfw_pqc_detector/services/kafka_consumer.py:354) - Updated parsing logic
- [`scripts/inspect_kafka_messages.py`](../scripts/inspect_kafka_messages.py) - Message inspection tool
- [`docs/BYTE_BASED_HEURISTIC_FALLBACK.md`](BYTE_BASED_HEURISTIC_FALLBACK.md) - Fallback for flow events

## Summary

The algorithms are now properly extracted from the `tls.pqc` structure in TLS events. Flow events without this data use byte-based heuristics as a fallback.