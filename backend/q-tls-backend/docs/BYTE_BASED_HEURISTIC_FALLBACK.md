# Byte-Based Heuristic Fallback for TLS Without Handshake Data

## Problem

Kafka messages with `event_type: "flow"` and `app_proto: "tls"` were missing the TLS handshake section, resulting in:
- Empty algorithms arrays
- `crypto_type: "unknown"`
- `confidence: 0`
- No meaningful PQC classification

Example problematic message:
```json
{
  "event_type": "flow",
  "app_proto": "tls",
  "flow": {
    "bytes_toserver": 4451,
    "bytes_toclient": 2514,
    "total_bytes": 6965
  },
  "pqc_detection": {
    "status": "unknown",
    "crypto_type": "unknown",
    "confidence": 0,
    "algorithms": {
      "supported_groups": [],
      "key_share_groups": [],
      "signature_algorithms": [],
      "cipher_suites": []
    }
  }
}
```

## Root Cause

Suricata is generating flow events for TLS connections but **not including the TLS handshake details** in these events. This happens when:

1. Suricata's TLS logging is not configured for extended mode
2. Flow events are logged separately from TLS events
3. The TLS handshake was not captured (connection already established)
4. Suricata is configured to log only flow metadata

## Solution

Implemented a **byte-based heuristic fallback** that uses the total bytes transferred to estimate the crypto type when TLS handshake data is unavailable.

### Implementation

#### 1. Early Byte Extraction

Moved byte count extraction to the beginning of message processing:

```python
# Get byte counts early for heuristic detection
flow_data = message.get("flow", {})
bytes_to_server = flow_data.get("bytes_toserver", 0)
bytes_to_client = flow_data.get("bytes_toclient", 0)
total_bytes = bytes_to_server + bytes_to_client
```

#### 2. TLS Without Handshake Detection

Added special handling for TLS connections without handshake data:

```python
# Handle TLS connections without handshake data (flow events)
if not tls_data and app_proto in ["tls", "ssl", "https"]:
    logger.info("⚠️  TLS connection without handshake data - using byte-based heuristic")
    
    if total_bytes > 0:
        crypto_type, confidence = self.pqc_detector._detect_by_bytes(total_bytes)
        is_pqc_safe = crypto_type in ["post-quantum", "hybrid"]
        pqc_status = "safe" if is_pqc_safe else "vulnerable"
```

#### 3. Heuristic Thresholds

The byte-based detection uses these thresholds (from [`pqc_detector.py`](../src/ngfw_pqc_detector/services/pqc_detector.py:105)):

```python
BYTE_THRESHOLD_PQC_SAFE = 8000      # > 8000 bytes → PQC
BYTE_THRESHOLD_CLASSICAL_TLS13 = 5000  # 5000-8000 bytes → Classical TLS 1.3
# < 5000 bytes → Legacy/Classical
```

**Rationale:**
- PQC algorithms like ML-KEM-768 use larger keys (~3KB more than classical ECDH)
- Classical TLS 1.3 with ECDHE typically uses 5000-8000 bytes
- Legacy TLS or RSA key exchange uses < 5000 bytes

## Results

### Before Fix

```json
{
  "pqc_detection": {
    "status": "unknown",
    "crypto_type": "unknown",
    "confidence": 0,
    "detection_method": "hybrid_algorithm_and_bytes",
    "algorithms": {
      "supported_groups": [],
      "key_share_groups": [],
      "signature_algorithms": [],
      "cipher_suites": []
    }
  }
}
```

### After Fix

For a 6965-byte TLS connection:

```json
{
  "pqc_detection": {
    "status": "vulnerable",
    "crypto_type": "classical",
    "confidence": 0.5196,
    "detection_method": "byte_based_heuristic",
    "is_pqc_safe": false,
    "algorithms": {
      "supported_groups": [],
      "key_share_groups": [],
      "signature_algorithms": [],
      "cipher_suites": []
    }
  }
}
```

**Explanation:**
- 6965 bytes falls in the 5000-8000 range
- Classified as "classical" TLS 1.3
- Confidence ~52% (heuristic-based, not algorithm-based)
- Algorithms remain empty (no handshake data available)

## Confidence Levels

The byte-based heuristic provides different confidence levels:

| Byte Range | Classification | Confidence | Reasoning |
|------------|---------------|------------|-----------|
| > 8000 | PQC | 0.60-0.85 | Large key sizes indicate PQC |
| 5000-8000 | Classical TLS 1.3 | 0.50-0.60 | Typical ECDHE size |
| < 5000 | Legacy/Classical | 0.60 | Small key sizes |

**Note:** These are lower than algorithm-based detection (0.70-1.00) because they're heuristic estimates.

## Limitations

### 1. No Algorithm Details
Without handshake data, we cannot extract:
- Supported groups
- Key share groups
- Signature algorithms
- Cipher suites

### 2. Lower Accuracy
Byte-based detection is less accurate than algorithm-based:
- Cannot distinguish between different classical algorithms
- Cannot detect hybrid configurations
- May misclassify edge cases

### 3. False Positives/Negatives
Possible scenarios:
- Large classical connections might be classified as PQC
- Small PQC connections might be classified as classical
- Compressed or encrypted payloads affect byte counts

## Best Practices

### 1. Enable Full TLS Logging (Recommended)

Configure Suricata for extended TLS logging to get algorithm details:

```yaml
# suricata.yaml
outputs:
  - eve-log:
      types:
        - tls:
            enabled: yes
            extended: yes
            ja3-fingerprints: yes
```

See [`SURICATA_TLS_CONFIG.md`](SURICATA_TLS_CONFIG.md) for complete configuration.

### 2. Use Inspection Script

Run the inspection script to verify what data is available:

```bash
python3 scripts/inspect_kafka_messages.py --max-messages 20
```

See [`scripts/README_INSPECT_KAFKA.md`](../scripts/README_INSPECT_KAFKA.md) for usage.

### 3. Monitor Confidence Levels

- **High confidence (>0.70)**: Algorithm-based detection, reliable
- **Medium confidence (0.50-0.70)**: Byte-based heuristic, less reliable
- **Low confidence (<0.50)**: Insufficient data, treat as unknown

## Detection Method Field

The `detection_method` field indicates how classification was performed:

| Value | Meaning |
|-------|---------|
| `algorithm_based` | Used TLS handshake algorithms (most accurate) |
| `hybrid_algorithm_and_bytes` | Combined algorithms + byte heuristic (accurate) |
| `byte_based_heuristic` | Only byte counts available (less accurate) |
| `unknown` | No data available for classification |

## Troubleshooting

### Issue: All Connections Show "classical" with ~0.52 confidence

**Cause:** Only flow events without TLS handshake data

**Solution:** 
1. Check Suricata TLS logging configuration
2. Verify TLS events are being generated: `tail -f /var/log/suricata/eve.json | grep '"event_type":"tls"'`
3. Enable extended TLS logging in Suricata

### Issue: Byte counts are 0

**Cause:** Flow data not captured or connection just started

**Solution:**
- Wait for connection to complete
- Check Suricata flow logging configuration
- Verify network traffic is being captured

### Issue: Misclassification of known connections

**Cause:** Byte-based heuristic has limitations

**Solution:**
- Enable full TLS logging for accurate algorithm-based detection
- Use byte-based results as estimates only
- Consider confidence levels when making decisions

## Related Files

- [`src/ngfw_pqc_detector/services/kafka_consumer.py:134`](../src/ngfw_pqc_detector/services/kafka_consumer.py:134) - Byte-based fallback logic
- [`src/ngfw_pqc_detector/services/pqc_detector.py:337`](../src/ngfw_pqc_detector/services/pqc_detector.py:337) - Byte detection implementation
- [`docs/SURICATA_TLS_CONFIG.md`](SURICATA_TLS_CONFIG.md) - Suricata configuration guide
- [`scripts/inspect_kafka_messages.py`](../scripts/inspect_kafka_messages.py) - Message inspection tool

## Summary

The byte-based heuristic fallback provides:

✅ **Better than nothing**: Provides classification when no handshake data available  
✅ **Transparent**: Clear indication via `detection_method` field  
✅ **Confidence scoring**: Lower confidence reflects heuristic nature  
⚠️ **Limited accuracy**: Cannot replace algorithm-based detection  
⚠️ **No algorithm details**: Cannot extract specific algorithms used  

**Recommendation:** Use this as a fallback only. Configure Suricata for full TLS logging to get accurate, algorithm-based PQC detection.