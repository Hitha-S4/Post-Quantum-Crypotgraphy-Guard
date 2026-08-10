# Critical Fix: PQC Detection Independence from JA3

## Problem Identified

The PQC detection was not working because the Supported Groups extension parsing was **dependent on JA3 fingerprinting being enabled**. 

### Root Cause

In [`src/app-layer-ssl.c`](src/app-layer-ssl.c:1066), the code that parses the Supported Groups extension (0x000a) was inside a conditional block:

```c
if ((ssl_state->current_flags & SSL_AL_FLAG_STATE_CLIENT_HELLO) && ja3_elliptic_curves) {
    // Parse groups and add to PQC detector
}
```

The `ja3_elliptic_curves` buffer is only allocated when JA3 fingerprinting is enabled (line 1270-1284). Since JA3 was not explicitly enabled in the configuration, this buffer was NULL, causing the entire Supported Groups parsing to be skipped.

## Solution Implemented

Made PQC detection **completely independent** of JA3 fingerprinting:

### Change 1: Supported Groups Extension (lines 1066-1093)

**Before:**
- Only parsed groups if `ja3_elliptic_curves` was not NULL
- PQC detection was tied to JA3 being enabled

**After:**
- Always parse groups for ClientHello
- Add to JA3 buffer only if JA3 is enabled
- Always add to PQC detector (with NULL check)

```c
if ((ssl_state->current_flags & SSL_AL_FLAG_STATE_CLIENT_HELLO)) {
    // ... parse groups ...
    if (TLSDecodeValueIsGREASE(elliptic_curve) != 1) {
        // Add to JA3 if enabled
        if (ja3_elliptic_curves) {
            int rc = Ja3BufferAddValue(&ja3_elliptic_curves, elliptic_curve);
            if (rc != 0)
                return -1;
        }
        
        // Always add to PQC detector
        if (ssl_state->curr_connp->hs != NULL) {
            SCTLSHandshakeAddSupportedGroup(ssl_state->curr_connp->hs, elliptic_curve);
        }
    }
}
```

### Change 2: Key Share Extension (line 1405)

Added NULL check for safety:

```c
if (TLSDecodeValueIsGREASE(group) != 1 && ssl_state->curr_connp->hs != NULL) {
    SCTLSHandshakeAddKeyShareGroup(ssl_state->curr_connp->hs, group);
}
```

## Testing the Fix

### 1. Rebuild Suricata

```bash
rm src/app-layer-ssl.o
make -j$(sysctl -n hw.ncpu)
```

### 2. Install and Restart (requires sudo)

```bash
sudo make install
sudo pkill -9 suricata
sudo src/suricata -c /usr/local/etc/suricata/suricata.yaml -i en0 -v
```

### 3. Generate TLS Traffic

```bash
# In another terminal
curl -v https://github.com
curl -v https://stackoverflow.com
curl -v https://www.reddit.com
```

### 4. Check Results

```bash
tail -f /usr/local/var/log/suricata/eve.json | jq 'select(.event_type=="tls") | .tls'
```

## Expected Output

You should now see PQC data in TLS events:

```json
{
  "sni": "github.com",
  "version": "TLS 1.3",
  "ja4": "t13d4907h2_0d8feac7bc37_7395dae3b2f3",
  "client_alpns": ["h2", "http/1.1"],
  "pqc": {
    "posture": "CLASSICAL",
    "is_pqc": false,
    "has_ech": false,
    "supported_groups": [29, 23, 24, 25, 256, 257, 258, 259, 260],
    "key_share_groups": [29]
  }
}
```

## Key Points

1. **PQC detection now works regardless of JA3 configuration**
2. **Supported Groups are always parsed for ClientHello messages**
3. **JA3 fingerprinting remains optional and independent**
4. **NULL checks prevent crashes if handshake structure is not allocated**

## Files Modified

- [`src/app-layer-ssl.c`](src/app-layer-ssl.c) - Lines 1066-1093 and 1405

## Related Documentation

- [PQC-TLS-DETECTION.md](PQC-TLS-DETECTION.md) - Main PQC detection documentation
- [FIX-EMPTY-GROUPS.md](FIX-EMPTY-GROUPS.md) - Previous fix attempts
- [FINAL-FIX-SUMMARY.md](FINAL-FIX-SUMMARY.md) - Summary of all fixes