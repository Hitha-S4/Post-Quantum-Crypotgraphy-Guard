# Algorithm Extraction Fix for Non-TLS Events

## Problem

When receiving Kafka messages with `event_type: "flow"` (instead of `event_type: "tls"`), the algorithms field was empty even though the message contained TLS data:

```json
{
  "event_type": "flow",
  "app_proto": "tls",
  "tls": {
    "version": "TLS 1.3",
    "supported_groups": ["x25519", "secp256r1"],
    "key_share": ["x25519"],
    "signature_algorithms": ["ecdsa_secp256r1_sha256"]
  }
}
```

Result was:
```json
"algorithms": {
  "supported_groups": [],
  "key_share_groups": [],
  "signature_algorithms": [],
  "cipher_suites": []
}
```

## Root Cause

The code only extracted algorithm details when processing TLS events through the `_parse_client_hello()` method. Flow events with TLS data were treated as "non-TLS" and skipped algorithm extraction.

## Solution

Added a new method `_extract_tls_info_from_message()` that extracts TLS information directly from the Kafka message, regardless of event type:

### New Method in [`kafka_consumer.py`](../src/ngfw_pqc_detector/services/kafka_consumer.py:434)

```python
def _extract_tls_info_from_message(self, message: dict) -> Optional[dict]:
    """
    Extract TLS information directly from Kafka message
    
    Args:
        message: Original Kafka message
        
    Returns:
        Dictionary with TLS information or None
    """
    tls_data = message.get("tls", {})
    
    if not tls_data:
        return None
    
    tls_info = {
        "version": tls_data.get("version", "unknown"),
        "sni": tls_data.get("sni", None),
        "cipher_suite": tls_data.get("cipher_suite_name", "unknown"),
        "ja3": tls_data.get("ja3", {}).get("hash", None) if tls_data.get("ja3") else None,
    }
    
    # Extract supported groups if available
    supported_groups = tls_data.get("supported_groups", [])
    key_share_groups = tls_data.get("key_share", [])
    signature_algorithms = tls_data.get("signature_algorithms", [])
    
    if supported_groups or key_share_groups or signature_algorithms:
        tls_info["supported_groups"] = supported_groups
        tls_info["key_share_groups"] = key_share_groups
        tls_info["signature_algorithms"] = signature_algorithms
    
    return tls_info
```

### Updated Non-TLS Flow Handling

```python
# Extract TLS info directly from message if available
tls_info = self._extract_tls_info_from_message(message)

# Extract algorithms from TLS info if available
algorithms = None
if tls_info and any(k in tls_info for k in ["supported_groups", "key_share_groups", "signature_algorithms"]):
    algorithms = {
        "supported_groups": tls_info.get("supported_groups", []),
        "key_share_groups": tls_info.get("key_share_groups", []),
        "signature_algorithms": tls_info.get("signature_algorithms", []),
        "cipher_suites": []
    }

# Create enriched message with algorithms
enriched_message = self._create_enriched_message(
    message=message,
    crypto_type="unknown",
    pqc_status="unknown",
    confidence=0.0,
    bytes_to_server=bytes_to_server,
    bytes_to_client=bytes_to_client,
    total_bytes=total_bytes,
    algorithms=algorithms,
    tls_info=tls_info,
)
```

## Result

Now flow events with TLS data will properly populate the algorithms field:

```json
{
  "pqc_detection": {
    "status": "unknown",
    "crypto_type": "unknown",
    "confidence": 0,
    "algorithms": {
      "supported_groups": ["x25519", "secp256r1"],
      "key_share_groups": ["x25519"],
      "signature_algorithms": ["ecdsa_secp256r1_sha256"],
      "cipher_suites": []
    }
  },
  "tls": {
    "version": "TLS 1.3",
    "sni": "example.com",
    "cipher_suite": "TLS_AES_128_GCM_SHA256",
    "supported_groups": ["x25519", "secp256r1"],
    "key_share_groups": ["x25519"],
    "signature_algorithms": ["ecdsa_secp256r1_sha256"]
  }
}
```

## Benefits

1. **Complete Data**: Algorithms are now extracted from all messages with TLS data
2. **Event Type Agnostic**: Works for both "tls" and "flow" event types
3. **Backward Compatible**: Doesn't break existing TLS event processing
4. **Consistent Format**: Same algorithm structure regardless of event type

## Testing

The fix handles these scenarios:

1. **TLS Events**: Continue to work as before with full ClientHello parsing
2. **Flow Events with TLS Data**: Now extract algorithms from TLS section
3. **Non-TLS Events**: Return empty algorithms (expected behavior)
4. **Partial TLS Data**: Extract whatever is available

## Related Files

- [`src/ngfw_pqc_detector/services/kafka_consumer.py`](../src/ngfw_pqc_detector/services/kafka_consumer.py:147) - Algorithm extraction for flow events
- [`src/ngfw_pqc_detector/services/kafka_consumer.py`](../src/ngfw_pqc_detector/services/kafka_consumer.py:434) - New extraction method
- [`src/ngfw_pqc_detector/services/kafka_consumer.py`](../src/ngfw_pqc_detector/services/kafka_consumer.py:346) - Updated signature