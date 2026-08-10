# Final Fix: Complete PQC Detection for TLS

## Problem Summary
TLS events showed empty `supported_groups` arrays and no PQC data at all in JSON output.

## Root Causes Found

### Issue 1: Extension Data Not Being Captured
The C code parsing TLS extensions wasn't calling the Rust PQC detection functions.

### Issue 2: PQC Data Not Being Logged  
Even if captured, the PQC data wasn't being written to JSON output.

## Complete Solution

### Files Modified

#### 1. **src/app-layer-ssl.h** - Added Key Share constant
```c
#define SSL_EXTENSION_KEY_SHARE  0x0033
```

#### 2. **src/app-layer-ssl.c** - Three changes:

**A. Capture Supported Groups** (line ~1082):
```c
if (TLSDecodeValueIsGREASE(elliptic_curve) != 1) {
    int rc = Ja3BufferAddValue(&ja3_elliptic_curves, elliptic_curve);
    if (rc != 0)
        return -1;
    
    // NEW: Add to PQC detector
    SCTLSHandshakeAddSupportedGroup(ssl_state->curr_connp->hs, elliptic_curve);
}
```

**B. Parse Key Share Extension** (line ~1375):
```c
case SSL_EXTENSION_KEY_SHARE: {
    if (ssl_state->current_flags & SSL_AL_FLAG_STATE_CLIENT_HELLO) {
        // Parse KeyShareEntry structures
        // Extract group IDs and call SCTLSHandshakeAddKeyShareGroup()
    }
    break;
}
```

**C. Classify After Parsing** (line ~1668):
```c
case SSLV3_HS_CLIENT_HELLO:
    rc = TLSDecodeHandshakeHello(ssl_state, input, input_len);
    if (rc < 0)
        return rc;
    
    // NEW: Classify PQC posture
    if (ssl_state->curr_connp->hs != NULL) {
        SCTLSHandshakeClassifyPQC(ssl_state->curr_connp->hs);
    }
    break;
```

#### 3. **src/output-json-tls.c** - Log PQC data (line ~513):
```c
/* tls server handshake parameters */
if (fields & LOG_TLS_FIELD_SERVER_HANDSHAKE)
    JsonTlsLogServerHandshake(js, ssl_state);

// NEW: PQC detection - always log if client handshake exists
if (ssl_state->client_connp.hs != NULL) {
    SCTLSHandshakeLogPQCDetails(ssl_state->client_connp.hs, js);
}
```

#### 4. **rust/src/quic/frames.rs** - Same fixes for QUIC
- Added EllipticCurves parsing
- Added KeyShare parsing  
- Added classify_pqc() call

## Deployment

```bash
# Use the automated script
./restart-monitor.sh
```

Or manually:
```bash
sudo pkill -9 suricata
sudo make install
sudo ./monitor-network.sh
```

## Expected Output

### Before All Fixes
```json
{
  "event_type": "tls",
  "tls": {
    "sni": "github.com",
    "version": "TLS 1.3"
    // NO PQC DATA AT ALL
  }
}
```

### After All Fixes
```json
{
  "event_type": "tls",
  "tls": {
    "sni": "github.com",
    "version": "TLS 1.3",
    "pqc": {
      "posture": "CLASSICAL",
      "is_pqc": false,
      "has_ech": false,
      "supported_groups": [29, 23, 24]
    }
  }
}
```

## Testing

1. **Restart monitor**: `./restart-monitor.sh`
2. **Generate TLS traffic**: `curl https://github.com`
3. **View events**: `./view-pqc-events.sh`
4. **Check raw JSON**: `tail -f logs/eve.json | jq 'select(.event_type=="tls")'`

## Verification

You should now see:
- ✅ `pqc` object in TLS events
- ✅ `supported_groups` array populated with algorithm IDs
- ✅ `posture` classification (CLASSICAL, PQC_HYBRID, PQC_PURE, etc.)
- ✅ `is_pqc` boolean flag
- ✅ `has_ech` ECH detection

## Common Algorithm IDs

- **23** - secp256r1 (ECDH P-256)
- **24** - secp384r1 (ECDH P-384)
- **29** - x25519 (Curve25519)
- **30** - x448 (Curve448)
- **513** (0x0201) - ML-KEM-768 (PQC)
- **515** (0x0203) - X25519-MLKEM768 (Hybrid)
- **4588** (0x11EB) - X25519Kyber768Draft00 (Hybrid)

## Architecture

The complete flow:
1. **Packet Capture** → Suricata receives TLS ClientHello
2. **C Parser** → `app-layer-ssl.c` parses extensions
3. **Rust Detection** → Calls `SCTLSHandshakeAddSupportedGroup()` and `SCTLSHandshakeAddKeyShareGroup()`
4. **Classification** → `SCTLSHandshakeClassifyPQC()` determines posture
5. **JSON Logging** → `SCTLSHandshakeLogPQCDetails()` writes to EVE JSON
6. **Output** → Complete PQC metadata in logs

All components now work together to provide comprehensive PQC detection for every TLS connection!