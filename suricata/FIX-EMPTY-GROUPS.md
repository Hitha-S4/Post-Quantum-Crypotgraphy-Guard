# Fix for Empty Groups Array in PQC Detection

## Problem
TLS events were being captured but the `supported_groups` array was always empty, preventing proper PQC classification.

## Root Cause
The TLS extension parsing code in `src/app-layer-ssl.c` was not calling the PQC detection functions to record:
1. **Supported Groups** (extension 0x000a) - which algorithms the client supports
2. **Key Share** (extension 0x0033) - which algorithms the client is actively using

## Solution

### Files Modified

#### 1. `src/app-layer-ssl.h`
Added Key Share extension constant:
```c
#define SSL_EXTENSION_KEY_SHARE  0x0033
```

#### 2. `src/app-layer-ssl.c`

**Added Supported Groups parsing** (line ~1082):
```c
// In TLSDecodeHSHelloExtensionEllipticCurves function
if (TLSDecodeValueIsGREASE(elliptic_curve) != 1) {
    int rc = Ja3BufferAddValue(&ja3_elliptic_curves, elliptic_curve);
    if (rc != 0)
        return -1;
    
    // Add to PQC detector
    SCTLSHandshakeAddSupportedGroup(ssl_state->curr_connp->hs, elliptic_curve);
}
```

**Added Key Share extension parsing** (line ~1375):
```c
case SSL_EXTENSION_KEY_SHARE: {
    /* Parse Key Share extension for PQC detection */
    if (ssl_state->current_flags & SSL_AL_FLAG_STATE_CLIENT_HELLO) {
        const uint8_t *ks_input = input;
        if (ext_len >= 2) {
            uint16_t shares_len = (uint16_t)(ks_input[0] << 8) | ks_input[1];
            ks_input += 2;
            uint16_t processed = 0;
            
            while (processed < shares_len && processed + 4 <= ext_len - 2) {
                uint16_t group = (uint16_t)(ks_input[0] << 8) | ks_input[1];
                ks_input += 2;
                uint16_t ke_len = (uint16_t)(ks_input[0] << 8) | ks_input[1];
                ks_input += 2;
                
                if (TLSDecodeValueIsGREASE(group) != 1) {
                    SCTLSHandshakeAddKeyShareGroup(ssl_state->curr_connp->hs, group);
                }
                
                if (processed + 4 + ke_len <= ext_len - 2) {
                    ks_input += ke_len;
                    processed += 4 + ke_len;
                } else {
                    break;
                }
            }
        }
    }
    input += ext_len;
    break;
}
```

**Added PQC classification call** (line ~1668):
```c
case SSLV3_HS_CLIENT_HELLO:
    // ... existing code ...
    rc = TLSDecodeHandshakeHello(ssl_state, input, input_len);
    if (rc < 0)
        return rc;
    
    /* Classify PQC posture after parsing ClientHello */
    if (ssl_state->curr_connp->hs != NULL) {
        SCTLSHandshakeClassifyPQC(ssl_state->curr_connp->hs);
    }
    break;
```

#### 3. `rust/src/quic/frames.rs`
Also updated QUIC TLS parsing (for QUIC connections) to parse the same extensions.

## How to Apply

```bash
# Run the restart script
./restart-monitor.sh
```

Or manually:
```bash
# Stop old monitor
sudo pkill -9 suricata

# Install updated binary
sudo make install

# Restart monitor
sudo ./monitor-network.sh
```

## Expected Result

**Before Fix:**
```json
{
  "pqc": {
    "posture": "UNKNOWN",
    "is_pqc": false,
    "has_ech": false,
    "supported_groups": []  ← Empty!
  }
}
```

**After Fix:**
```json
{
  "pqc": {
    "posture": "CLASSICAL",
    "is_pqc": false,
    "has_ech": false,
    "supported_groups": [29, 23, 24]  ← Populated with x25519, secp256r1, secp384r1
  }
}
```

## Testing

1. Restart the monitor with the new binary
2. Browse some HTTPS websites
3. Run `./view-pqc-events.sh` to see events
4. Verify that `supported_groups` now contains algorithm IDs

## Common Algorithm IDs

- **23** (0x0017) - secp256r1 (classical ECDH)
- **24** (0x0018) - secp384r1 (classical ECDH)
- **25** (0x0019) - secp521r1 (classical ECDH)
- **29** (0x001d) - x25519 (classical ECDH)
- **30** (0x001e) - x448 (classical ECDH)
- **513** (0x0201) - ML-KEM-768 (PQC pure)
- **515** (0x0203) - X25519-MLKEM768 (PQC hybrid)

## Technical Details

The fix integrates PQC detection into Suricata's existing TLS parsing pipeline:

1. **Extension Parsing**: When TLS ClientHello is parsed, each extension is processed
2. **Supported Groups**: Extension 0x000a lists all algorithms the client supports
3. **Key Share**: Extension 0x0033 lists algorithms the client is actively proposing
4. **Classification**: After parsing, `classify_pqc()` determines the connection's posture
5. **Logging**: Results are included in EVE JSON output

This ensures that every TLS connection is properly analyzed for PQC compliance.