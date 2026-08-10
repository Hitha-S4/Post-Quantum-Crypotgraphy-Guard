# PQC Classification Enhancement

## Overview
This document describes the enhancements made to add exchange groups, algorithms, and PQC classification logic to the Kafka response in WebSocket.

## Changes Made

### 1. PQC Detector Service (`src/ngfw_pqc_detector/services/pqc_detector.py`)

#### Added PQC_KEY_EXCHANGE_GROUPS Policy
A new policy table has been added to define PQC key exchange groups for classification:

```python
PQC_KEY_EXCHANGE_GROUPS = {
    "kyber512",
    "kyber768",
    "kyber1024",
    "mlkem512",
    "mlkem768",
    "mlkem1024",
    "hybrid_x25519_kyber768",
    "hybrid_secp256r1_kyber768",
    "x25519_kyber768",
    "secp256r1_kyber768",
    "p256_kyber768",
}
```

#### New Method: `classify_exchange_groups()`
Classifies exchange groups into three categories:
- **PQC Groups**: Pure post-quantum groups (e.g., kyber768, mlkem768)
- **Hybrid Groups**: Hybrid classical + PQC groups (e.g., x25519_kyber768)
- **Classical Groups**: Traditional groups (e.g., x25519, secp256r1)

**Returns:**
```python
{
    "pqc_groups": List[str],
    "hybrid_groups": List[str],
    "classical_groups": List[str],
    "total_groups": int,
    "has_pqc": bool
}
```

#### New Method: `get_algorithm_details()`
Extracts comprehensive algorithm information from ClientHello:

**Returns:**
```python
{
    "supported_groups": List[str],
    "key_share_groups": List[str],
    "signature_algorithms": List[str],
    "cipher_suites": List[dict]
}
```

### 2. Kafka Consumer Service (`src/ngfw_pqc_detector/services/kafka_consumer.py`)

#### Enhanced `_process_message()` Method
Now includes:
- Exchange groups classification
- Algorithm details extraction
- Enhanced logging for PQC and hybrid groups

#### Updated `_create_enriched_message()` Method
Added two new optional parameters:
- `exchange_groups: Optional[dict]` - Exchange groups classification
- `algorithms: Optional[dict]` - Algorithm details

The enriched WebSocket message now includes:

```python
"pqc_detection": {
    "status": "safe/vulnerable/unknown",
    "crypto_type": "classical/post-quantum/hybrid/unknown",
    "confidence": float,
    "detection_method": str,
    "is_pqc_safe": bool,
    
    # NEW: Exchange Groups Classification
    "exchange_groups": {
        "pqc_groups": List[str],
        "hybrid_groups": List[str],
        "classical_groups": List[str],
        "total_groups": int,
        "has_pqc": bool
    },
    
    # NEW: Algorithm Details
    "algorithms": {
        "supported_groups": List[str],
        "key_share_groups": List[str],
        "signature_algorithms": List[str],
        "cipher_suites": List[dict]
    }
}
```

## WebSocket Response Format

### Complete Example Response

```json
{
    "type": "kafka_message",
    "timestamp": "2026-02-10T09:00:00.000Z",
    "data": {
        "src_ip": "192.168.1.100",
        "src_port": 54321,
        "dest_ip": "93.184.216.34",
        "dest_port": 443,
        "proto": "TCP",
        "flow_id": 123456,
        "event_type": "tls",
        "app_proto": "tls",
        
        "flow": {
            "bytes_toserver": 5000,
            "bytes_toclient": 3500,
            "total_bytes": 8500,
            "state": "established"
        },
        
        "pqc_detection": {
            "status": "safe",
            "crypto_type": "hybrid",
            "confidence": 0.85,
            "detection_method": "hybrid_algorithm_and_bytes",
            "is_pqc_safe": true,
            
            "exchange_groups": {
                "pqc_groups": ["kyber768"],
                "hybrid_groups": ["x25519_kyber768"],
                "classical_groups": ["x25519", "secp256r1"],
                "total_groups": 4,
                "has_pqc": true
            },
            
            "algorithms": {
                "supported_groups": ["x25519_kyber768", "kyber768", "x25519", "secp256r1"],
                "key_share_groups": ["x25519_kyber768"],
                "signature_algorithms": ["ecdsa_secp256r1_sha256", "rsa_pss_rsae_sha256"],
                "cipher_suites": [
                    {
                        "code": "0xFE30",
                        "name": "TLS_MLKEM768_X25519_AES_128_GCM_SHA256",
                        "crypto_type": "hybrid"
                    }
                ]
            }
        },
        
        "tls": {
            "version": "TLS 1.3",
            "sni": "example.com",
            "cipher_suite": "TLS_MLKEM768_X25519_AES_128_GCM_SHA256",
            "ja3": "abc123..."
        }
    }
}
```

## PQC Classification Logic

### Core Algorithm

The PQC classification follows this logic:

1. **Extract TLS Signals:**
   - `tls.pqc.key_share_groups`
   - `tls.pqc.supported_groups`
   - `tls.pqc.signature_algorithms`
   - `tls.pqc.cipher_suites`

2. **Apply PQC_KEY_EXCHANGE_GROUPS Policy:**
   - Check if groups match PQC policy
   - Classify as PQC, Hybrid, or Classical

3. **Determine PQC Status:**
   - **Safe**: Uses PQC or Hybrid algorithms
   - **Vulnerable**: Uses only Classical algorithms
   - **Unknown**: Insufficient data

4. **Calculate Confidence:**
   - Algorithm-based detection (primary)
   - Byte-based heuristic (secondary)
   - Combined confidence when both agree

## Testing

A comprehensive test script has been created at `scripts/test_pqc_classification.py` that tests:

1. PQC_KEY_EXCHANGE_GROUPS policy
2. Exchange groups classification (Pure PQC, Hybrid, Classical, Mixed)
3. Algorithm details extraction
4. Full detection with classification

To run the tests:
```bash
python scripts/test_pqc_classification.py
```

## Benefits

1. **Enhanced Visibility**: Clients can now see detailed breakdown of exchange groups
2. **Better Classification**: Clear distinction between PQC, Hybrid, and Classical groups
3. **Algorithm Transparency**: Full visibility into supported algorithms
4. **Policy-Based**: Uses defined PQC_KEY_EXCHANGE_GROUPS policy for consistent classification
5. **Backward Compatible**: New fields are optional and don't break existing clients

## Usage Example

### Frontend/Client Side

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/kafka-stream');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'kafka_message') {
        const pqc = message.data.pqc_detection;
        
        // Check PQC status
        console.log('PQC Safe:', pqc.is_pqc_safe);
        console.log('Crypto Type:', pqc.crypto_type);
        
        // Display exchange groups
        console.log('PQC Groups:', pqc.exchange_groups.pqc_groups);
        console.log('Hybrid Groups:', pqc.exchange_groups.hybrid_groups);
        
        // Show algorithms
        console.log('Supported Groups:', pqc.algorithms.supported_groups);
        console.log('Key Shares:', pqc.algorithms.key_share_groups);
    }
};
```

## Future Enhancements

1. Add support for more PQC algorithms (e.g., FrodoKEM, BIKE)
2. Implement algorithm strength scoring
3. Add compliance checking against security policies
4. Create visualization for algorithm distribution
5. Add historical trending for PQC adoption

## References

- NIST Post-Quantum Cryptography Standardization
- ML-KEM (FIPS 203) - Module-Lattice-Based Key-Encapsulation Mechanism
- ML-DSA (FIPS 204) - Module-Lattice-Based Digital Signature Algorithm
- TLS 1.3 RFC 8446