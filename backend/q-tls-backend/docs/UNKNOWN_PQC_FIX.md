# Unknown PQC Algorithm Detection Fix

## Problem

When Suricata detects an unknown PQC algorithm (e.g., `Unknown-0x11EC`), the system was incorrectly classifying it as `vulnerable` with posture `UNKNOWN_PQC` instead of recognizing it as `PQC_SAFE`.

### Example Issue

```json
{
  "tls": {
    "pqc": {
      "posture": "UNKNOWN_PQC",
      "is_pqc": true,
      "supported_groups_names": ["Unknown-0x11EC"]
    }
  }
}
```

The system was treating this as vulnerable because:
1. The algorithm name contains "Unknown"
2. The [`classify_exchange_groups()`](../src/ngfw_pqc_detector/services/pqc_detector.py:258) method defaulted unknown algorithms to `classical_groups`
3. This resulted in `has_pqc: false` and status `vulnerable`

## Solution

### 1. Enhanced `classify_exchange_groups()` Method

**File**: [`src/ngfw_pqc_detector/services/pqc_detector.py`](../src/ngfw_pqc_detector/services/pqc_detector.py:258)

Added support for Suricata's `is_pqc` flag:

```python
def classify_exchange_groups(
    self, 
    supported_groups: List[str], 
    key_share_groups: List[str], 
    is_pqc_from_suricata: bool = False  # NEW PARAMETER
) -> dict:
```

**Key Changes**:
- Added `is_pqc_from_suricata` parameter to trust Suricata's PQC detection
- Added `unknown_groups` list to track unknown algorithms separately
- When an algorithm name contains "unknown":
  - If `is_pqc_from_suricata` is `True`, classify as PQC group
  - Otherwise, classify as classical group
- Return `unknown_groups` in the result dictionary

### 2. Updated Kafka Consumer Logic

**File**: [`src/ngfw_pqc_detector/services/kafka_consumer.py`](../src/ngfw_pqc_detector/services/kafka_consumer.py:251)

**Key Changes**:

1. **Extract Suricata's `is_pqc` flag**:
```python
is_pqc_from_suricata = pqc_data.get("is_pqc", False)
```

2. **Pass flag to classification**:
```python
exchange_groups_classification = self.pqc_detector.classify_exchange_groups(
    client_hello_data.supported_groups,
    client_hello_data.key_share_groups,
    is_pqc_from_suricata  # Pass Suricata's detection
)
```

3. **Override detection for unknown PQC algorithms**:
```python
# If we have unknown algorithms but Suricata detected PQC, trust Suricata
if (
    crypto_type == CryptoType.UNKNOWN
    and is_pqc_from_suricata
    and suricata_posture == "UNKNOWN_PQC"
):
    is_pqc_safe = True
    crypto_type = CryptoType.PQC
    confidence = 0.7  # Medium confidence
    logger.info("   ℹ️  Unknown algorithm detected as PQC by Suricata - treating as PQC-safe")
```

## Detection Flow

```
┌─────────────────────────────────────┐
│ Suricata detects TLS connection     │
│ with unknown algorithm (0x11EC)     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Suricata sets:                      │
│ - posture: "UNKNOWN_PQC"            │
│ - is_pqc: true                      │
│ - supported_groups_names:           │
│   ["Unknown-0x11EC"]                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Kafka Consumer extracts is_pqc flag│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ PQC Detector classifies groups      │
│ with is_pqc_from_suricata=true      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Unknown algorithm classified as     │
│ PQC group (not classical)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Detection result:                   │
│ - crypto_type: "post-quantum"       │
│ - status: "safe"                    │
│ - confidence: 0.7                   │
│ - has_pqc: true                     │
└─────────────────────────────────────┘
```

## Result

After the fix, connections with unknown PQC algorithms are correctly classified:

```json
{
  "pqc_detection": {
    "status": "safe",
    "crypto_type": "post-quantum",
    "confidence": 0.7,
    "is_pqc_safe": true,
    "posture": "UNKNOWN_PQC",
    "exchange_groups": {
      "pqc_groups": ["Unknown-0x11EC"],
      "unknown_groups": ["Unknown-0x11EC"],
      "classical_groups": [],
      "has_pqc": true
    }
  }
}
```

## Benefits

1. **Trust Suricata's Detection**: When Suricata identifies PQC usage, we respect that determination
2. **Better Unknown Algorithm Handling**: Unknown algorithms are tracked separately and classified based on context
3. **Improved Accuracy**: Reduces false negatives for emerging or proprietary PQC algorithms
4. **Confidence Scoring**: Medium confidence (0.7) reflects uncertainty about unknown algorithms while still marking them as PQC-safe

## Testing

To test the fix:

1. Send a TLS connection with an unknown PQC algorithm through Suricata
2. Verify Suricata sets `is_pqc: true` and `posture: "UNKNOWN_PQC"`
3. Check that the system classifies it as:
   - `status: "safe"`
   - `crypto_type: "post-quantum"`
   - `has_pqc: true`
   - Algorithm appears in both `pqc_groups` and `unknown_groups`

## Related Files

- [`src/ngfw_pqc_detector/services/pqc_detector.py`](../src/ngfw_pqc_detector/services/pqc_detector.py) - PQC detection logic
- [`src/ngfw_pqc_detector/services/kafka_consumer.py`](../src/ngfw_pqc_detector/services/kafka_consumer.py) - Kafka message processing
- [`docs/SURICATA_PQC_STRUCTURE.md`](./SURICATA_PQC_STRUCTURE.md) - Suricata PQC data structure