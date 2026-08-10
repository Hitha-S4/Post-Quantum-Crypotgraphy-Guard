# 🔐 Complete PQC Testing Guide

## ✅ Your System Status

**OpenSSL Version:** 3.6.1 (with native ML-KEM/PQC support!)  
**Available Tools:** `openssl`, `nscurl`  
**Suricata PQC Detection:** ✅ Fully operational

## 🚀 Quick Start (Recommended)

### Option 1: Quick Test Script
```bash
./quick-pqc-test.sh
```

This script will:
- Test PQC connection to Cloudflare
- Check Suricata logs automatically
- Show detection statistics
- Provide next steps

### Option 2: Full Test Suite
```bash
./test-pqc-with-openssl.sh
```

Runs comprehensive tests with multiple PQC configurations.

### Option 3: macOS Native Tool
```bash
./test-pqc-with-nscurl.sh
```

Uses macOS `nscurl` (PQC support depends on macOS version).

## 📋 Available PQC Algorithms

Your OpenSSL 3.6.1 supports these ML-KEM algorithms:

### Hybrid PQC (Recommended)
- **X25519MLKEM768** - X25519 + ML-KEM-768 (Group ID: 515)
- **SecP256r1MLKEM768** - P-256 + ML-KEM-768 (Group ID: 517)
- **SecP384r1MLKEM1024** - P-384 + ML-KEM-1024
- **X448MLKEM1024** - X448 + ML-KEM-1024

### Pure PQC
- **MLKEM512** - ML-KEM-512 only (Group ID: 512)
- **MLKEM768** - ML-KEM-768 only (Group ID: 513)
- **MLKEM1024** - ML-KEM-1024 only (Group ID: 514)

## 🧪 Manual Testing Commands

### Test 1: Hybrid PQC (Most Common)
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups X25519MLKEM768 \
  -tls1_3 -brief <<< "Q"
```

**Expected Detection:** `PQC_HYBRID` with group ID `515`

### Test 2: Pure PQC
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups MLKEM768 \
  -tls1_3 -brief <<< "Q"
```

**Expected Detection:** `PQC_PURE` with group ID `513`

### Test 3: Multiple Groups (Fallback)
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups X25519MLKEM768:X25519 \
  -tls1_3 -brief <<< "Q"
```

**Expected Detection:** `PQC_HYBRID` if server supports it, otherwise `CLASSICAL`

### Test 4: Classical (Baseline)
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups X25519 \
  -tls1_3 -brief <<< "Q"
```

**Expected Detection:** `CLASSICAL` with group ID `29`

## 📊 Viewing Results

### Real-time Monitoring
```bash
./view-pqc-events.sh
```

### Find PQC Connections
```bash
# Any PQC traffic
jq 'select(.tls.pqc.is_pqc==true)' logs/eve.json

# Hybrid PQC only
jq 'select(.tls.pqc.posture=="PQC_HYBRID")' logs/eve.json

# Pure PQC only
jq 'select(.tls.pqc.posture=="PQC_PURE")' logs/eve.json
```

### Recent TLS Events
```bash
tail -50 logs/eve.json | jq 'select(.event_type=="tls") | {
  timestamp,
  dest_ip,
  sni: .tls.sni,
  posture: .tls.pqc.posture,
  groups: .tls.pqc.supported_groups[0:5]
}'
```

### Statistics
```bash
# Count by posture
jq -r 'select(.event_type=="tls") | .tls.pqc.posture' logs/eve.json | sort | uniq -c

# Find PQC group IDs
jq -r 'select(.event_type=="tls") | .tls.pqc.supported_groups[]?' logs/eve.json | grep -E "^(512|513|514|515|516|517)$" | sort | uniq -c
```

## 🎯 Understanding Detection Results

### Successful PQC Detection
```json
{
  "tls": {
    "pqc": {
      "is_pqc": true,
      "posture": "PQC_HYBRID",
      "supported_groups": [515, 29, 23],
      "supported_groups_names": ["X25519MLKEM768", "X25519", "secp256r1"],
      "key_share_groups": [515],
      "key_share_groups_names": ["X25519MLKEM768"],
      "has_ech": false
    }
  }
}
```

**This means:**
- ✅ Client offered PQC (group 515 = X25519MLKEM768)
- ✅ Server accepted PQC (key_share 515)
- ✅ Connection uses hybrid PQC encryption

### Server Doesn't Support PQC
```json
{
  "tls": {
    "pqc": {
      "is_pqc": false,
      "posture": "CLASSICAL",
      "supported_groups": [515, 29, 23],
      "key_share_groups": [29]
    }
  }
}
```

**This means:**
- ✅ Client offered PQC (group 515)
- ❌ Server chose classical (group 29 = X25519)
- ℹ️ This is normal - most servers don't support PQC yet

## 🔍 Group ID Reference

| Group ID | Name | Type | Security Level |
|----------|------|------|----------------|
| 512 | ML-KEM-512 | Pure PQC | 128-bit |
| 513 | ML-KEM-768 | Pure PQC | 192-bit |
| 514 | ML-KEM-1024 | Pure PQC | 256-bit |
| 515 | X25519-MLKEM768 | Hybrid PQC | 192-bit |
| 516 | X25519-MLKEM1024 | Hybrid PQC | 256-bit |
| 517 | P256-MLKEM768 | Hybrid PQC | 192-bit |
| 29 | X25519 | Classical | 128-bit |
| 23 | secp256r1 (P-256) | Classical | 128-bit |
| 24 | secp384r1 (P-384) | Classical | 192-bit |
| 25 | secp521r1 (P-521) | Classical | 256-bit |

## 🌐 Test Servers

### Servers with PQC Support
1. **Cloudflare** - `cloudflare.com:443`
   - Good PQC support
   - Recommended for testing

2. **Cloudflare Research** - `pq.cloudflareresearch.com:443`
   - Dedicated PQC endpoint
   - May have experimental features

3. **Google** - `www.google.com:443`
   - Limited PQC support
   - May vary by region

### Testing Strategy
```bash
# Test each server
for server in cloudflare.com pq.cloudflareresearch.com www.google.com; do
  echo "Testing $server..."
  openssl s_client -connect $server:443 -groups X25519MLKEM768 -tls1_3 -brief <<< "Q" 2>&1 | head -5
  sleep 2
done

# Check results
tail -20 logs/eve.json | jq 'select(.event_type=="tls") | {dest_ip, sni: .tls.sni, posture: .tls.pqc.posture}'
```

## 🐛 Troubleshooting

### Issue: No PQC Detected

**Check 1: Verify OpenSSL has PQC support**
```bash
openssl list -kem-algorithms | grep -i mlkem
```

Expected output should include:
- ML-KEM-512
- ML-KEM-768
- ML-KEM-1024
- X25519MLKEM768

**Check 2: Verify connection succeeded**
```bash
openssl s_client -connect cloudflare.com:443 -groups X25519MLKEM768 -tls1_3
```

Look for "Verification: OK" in output.

**Check 3: Verify Suricata is running**
```bash
ps aux | grep suricata
```

**Check 4: Check recent logs**
```bash
tail -20 logs/eve.json | jq 'select(.event_type=="tls")'
```

### Issue: Only CLASSICAL Detected

This is **normal** if:
- Server doesn't support PQC (most don't yet)
- Server chose to fallback to classical
- Network middlebox stripped PQC extensions

**Verify client offered PQC:**
```bash
jq 'select(.event_type=="tls") | {
  groups: .tls.pqc.supported_groups,
  key_share: .tls.pqc.key_share_groups
}' logs/eve.json | tail -5
```

If `supported_groups` includes 512-517 but `key_share_groups` doesn't, the server rejected PQC.

### Issue: Connection Hangs

**Solution 1: Use timeout (if available)**
```bash
# Install coreutils for gtimeout
brew install coreutils

# Use gtimeout
gtimeout 5 openssl s_client -connect cloudflare.com:443 -groups X25519MLKEM768 -tls1_3
```

**Solution 2: Use input redirection**
```bash
openssl s_client -connect cloudflare.com:443 -groups X25519MLKEM768 -tls1_3 <<< "Q"
```

**Solution 3: Use sleep + echo**
```bash
(sleep 3; echo "Q") | openssl s_client -connect cloudflare.com:443 -groups X25519MLKEM768 -tls1_3
```

## 📈 Success Criteria

You'll know PQC testing is working when:

1. **OpenSSL connects successfully**
   ```
   Verification: OK
   Protocol version: TLSv1.3
   ```

2. **Suricata logs show TLS events**
   ```bash
   tail logs/eve.json | jq 'select(.event_type=="tls")' | wc -l
   # Should show increasing count
   ```

3. **PQC groups are detected** (even if server rejects)
   ```bash
   jq '.tls.pqc.supported_groups[]?' logs/eve.json | grep -E "^51[2-7]$"
   # Should show group IDs 512-517
   ```

4. **Posture is classified correctly**
   ```bash
   jq -r '.tls.pqc.posture' logs/eve.json | sort | uniq
   # Should show: CLASSICAL, PQC_HYBRID, PQC_PURE, ECH_PROTECTED
   ```

## 🎉 Next Steps

Once you've confirmed PQC detection works:

1. **Monitor production traffic**
   ```bash
   ./view-pqc-events.sh
   ```

2. **Set up alerts** (if using SIEM)
   - Alert on `tls.pqc.is_pqc == true`
   - Track PQC adoption over time

3. **Analyze trends**
   ```bash
   # Daily PQC statistics
   jq -r 'select(.event_type=="tls") | "\(.timestamp | split("T")[0]) \(.tls.pqc.posture)"' logs/eve.json | sort | uniq -c
   ```

4. **Test your own services**
   ```bash
   # Test internal server
   openssl s_client -connect your-server.com:443 -groups X25519MLKEM768 -tls1_3
   ```

## 📚 Additional Resources

- **OpenSSL 3.6 PQC Guide:** https://www.openssl.org/docs/
- **NIST ML-KEM (FIPS 203):** https://csrc.nist.gov/pubs/fips/203/final
- **Cloudflare PQC Blog:** https://blog.cloudflare.com/post-quantum-for-all/
- **Suricata Documentation:** https://docs.suricata.io/

## 📝 Summary

Your system is **ready for PQC testing**:

✅ OpenSSL 3.6.1 with native ML-KEM support  
✅ Suricata PQC detection operational  
✅ Test scripts available  
✅ Monitoring tools configured  

**Start testing now:**
```bash
./quick-pqc-test.sh