# 🔐 Generate Real PQC Traffic for Testing

## ✅ Great News!

Your **OpenSSL 3.6.1** has **native PQC support** with ML-KEM algorithms! You can generate real PQC traffic right now.

## 🚀 Quick Start

### Method 1: OpenSSL (Recommended - Most Reliable)

```bash
# Make executable
chmod +x test-pqc-with-openssl.sh

# Run PQC tests
./test-pqc-with-openssl.sh
```

This will test:
- ✅ **Hybrid PQC** (X25519MLKEM768) - Should detect as `PQC_HYBRID`
- ✅ **Pure PQC** (MLKEM768) - Should detect as `PQC_PURE`
- ✅ **Classical** (X25519) - Should detect as `CLASSICAL`

### Method 2: nscurl (macOS Native)

```bash
# Make executable
chmod +x test-pqc-with-nscurl.sh

# Run tests
./test-pqc-with-nscurl.sh
```

**Note:** nscurl uses macOS system TLS stack. PQC support depends on your macOS version.

## 📋 Available PQC Algorithms in Your OpenSSL

### Hybrid PQC (Classical + Quantum-Resistant)
- **X25519MLKEM768** - X25519 + ML-KEM-768 (recommended)
- **SecP256r1MLKEM768** - P-256 + ML-KEM-768
- **SecP384r1MLKEM1024** - P-384 + ML-KEM-1024
- **X448MLKEM1024** - X448 + ML-KEM-1024

### Pure PQC (Quantum-Resistant Only)
- **MLKEM512** - ML-KEM-512 (128-bit security)
- **MLKEM768** - ML-KEM-768 (192-bit security)
- **MLKEM1024** - ML-KEM-1024 (256-bit security)

## 🧪 Manual Testing Commands

### Test Hybrid PQC (X25519 + ML-KEM-768)
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups X25519MLKEM768 \
  -tls1_3 -brief <<< "Q"
```

**Expected Suricata Detection:** `PQC_HYBRID`

### Test Pure PQC (ML-KEM-768 only)
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups MLKEM768 \
  -tls1_3 -brief <<< "Q"
```

**Expected Suricata Detection:** `PQC_PURE`

### Test Multiple PQC Groups
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups X25519MLKEM768:SecP256r1MLKEM768:X25519 \
  -tls1_3 -brief <<< "Q"
```

**Expected Suricata Detection:** `PQC_HYBRID`

### Test Classical (for comparison)
```bash
openssl s_client -connect cloudflare.com:443 \
  -groups X25519 \
  -tls1_3 -brief <<< "Q"
```

**Expected Suricata Detection:** `CLASSICAL`

## 📊 View Detection Results

### Real-time Monitoring
```bash
./view-pqc-events.sh
```

### Check for PQC Traffic
```bash
# Find any PQC connections
jq 'select(.tls.pqc.is_pqc==true)' logs/eve.json

# See latest TLS events with PQC info
tail -50 logs/eve.json | jq 'select(.event_type=="tls") | {
  timestamp,
  dest_ip,
  dest_port,
  is_pqc: .tls.pqc.is_pqc,
  posture: .tls.pqc.posture,
  groups: .tls.pqc.supported_groups
}'
```

### Check Detection Statistics
```bash
# Count by posture
jq -r 'select(.event_type=="tls") | .tls.pqc.posture' logs/eve.json | sort | uniq -c

# Find hybrid PQC
jq 'select(.tls.pqc.posture=="PQC_HYBRID")' logs/eve.json

# Find pure PQC
jq 'select(.tls.pqc.posture=="PQC_PURE")' logs/eve.json
```

## 🎯 Test Servers

### Servers with PQC Support
1. **Cloudflare** - `cloudflare.com:443`
   - Good PQC support
   - Recommended for testing

2. **Cloudflare Research** - `pq.cloudflareresearch.com:443`
   - Dedicated PQC testing endpoint
   - May have experimental features

3. **Google** - `www.google.com:443`
   - May support PQC depending on configuration

## 🔍 Understanding the Output

### OpenSSL Output
```
Connecting to cloudflare.com:443
Protocol version: TLSv1.3
Ciphersuite: TLS_AES_256_GCM_SHA384
Peer certificate: CN=cloudflare.com
Verification: OK
Supported groups: X25519MLKEM768:X25519:prime256v1
```

### Suricata Detection
```json
{
  "tls": {
    "pqc": {
      "is_pqc": true,
      "posture": "PQC_HYBRID",
      "supported_groups": [515, 29, 23],
      "key_share_groups": [515],
      "has_ech": false
    }
  }
}
```

**Group IDs:**
- `515` = X25519MLKEM768 (Hybrid PQC)
- `29` = X25519 (Classical)
- `23` = P-256 (Classical)

## ⚠️ Important Notes

### Server Support Required
- Both **client AND server** must support PQC
- If server doesn't support PQC, it will fallback to classical
- Cloudflare has good PQC support

### TLS 1.3 Required
- PQC key exchange requires TLS 1.3
- Always use `-tls1_3` flag with OpenSSL

### Timeout Handling
- Use `timeout 5` to prevent hanging connections
- Or use `<<< "Q"` to send quit command

### Detection Timing
- Suricata detects during TLS handshake
- Check logs immediately after connection
- Use `tail -f logs/eve.json` for real-time viewing

## 🐛 Troubleshooting

### No PQC Detected?

1. **Check if connection succeeded:**
   ```bash
   openssl s_client -connect cloudflare.com:443 -groups X25519MLKEM768 -tls1_3
   ```

2. **Verify Suricata is running:**
   ```bash
   ps aux | grep suricata
   ```

3. **Check recent TLS events:**
   ```bash
   tail -20 logs/eve.json | jq 'select(.event_type=="tls")'
   ```

4. **Look for the specific connection:**
   ```bash
   jq 'select(.dest_ip=="104.16.132.229")' logs/eve.json | tail -5
   ```

### Server Doesn't Support PQC?

If server falls back to classical:
```json
{
  "tls": {
    "pqc": {
      "is_pqc": false,
      "posture": "CLASSICAL",
      "supported_groups": [515, 29],  // Client offered PQC
      "key_share_groups": [29]        // Server chose classical
    }
  }
}
```

This is **normal** - it means:
- ✅ Your client supports PQC (offered group 515)
- ✅ Suricata detected the PQC offer
- ❌ Server doesn't support PQC (chose group 29)

## 📚 Additional Resources

- **OpenSSL PQC Documentation:** https://www.openssl.org/docs/man3.0/man7/ossl-guide-quic-multi-stream.html
- **ML-KEM Specification:** NIST FIPS 203
- **Cloudflare PQC:** https://blog.cloudflare.com/post-quantum-for-all/

## 🎉 Success Criteria

You'll know it's working when you see:

```bash
$ jq 'select(.tls.pqc.is_pqc==true)' logs/eve.json
{
  "timestamp": "2026-02-09T11:00:00.000000+0530",
  "event_type": "tls",
  "tls": {
    "pqc": {
      "is_pqc": true,
      "posture": "PQC_HYBRID",
      "supported_groups": [515, 29, 23],
      "key_share_groups": [515]
    }
  }
}
```

**That's real PQC traffic being detected!** 🎊