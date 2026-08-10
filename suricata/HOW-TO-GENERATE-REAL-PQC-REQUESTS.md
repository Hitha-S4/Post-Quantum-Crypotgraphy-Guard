# How to Generate Real PQC TLS Requests

## Problem

Your current output shows `CLASSICAL` because the standard `curl` client doesn't support PQC algorithms yet. To generate **real PQC requests**, you need a PQC-enabled client.

## Solution Options

### Option 1: Use Chrome/Chromium with PQC Enabled (Easiest)

Google Chrome has experimental PQC support:

```bash
# Launch Chrome with PQC enabled
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --enable-features=PostQuantumKyber \
  --origin-to-force-quic-on=pq.cloudflareresearch.com:443

# Then visit in the browser:
# https://pq.cloudflareresearch.com
```

### Option 2: Build curl with PQC Support

```bash
# 1. Install liboqs (Open Quantum Safe library)
git clone https://github.com/open-quantum-safe/liboqs.git
cd liboqs
mkdir build && cd build
cmake -GNinja -DCMAKE_INSTALL_PREFIX=/usr/local ..
ninja && sudo ninja install

# 2. Build OQS-OpenSSL
git clone https://github.com/open-quantum-safe/openssl.git oqs-openssl
cd oqs-openssl
./config --prefix=/usr/local/oqs-openssl
make -j$(sysctl -n hw.ncpu)
sudo make install

# 3. Build curl with OQS-OpenSSL
git clone https://github.com/curl/curl.git
cd curl
./buildconf
./configure --with-openssl=/usr/local/oqs-openssl
make -j$(sysctl -n hw.ncpu)
sudo make install

# 4. Test with PQC
/usr/local/bin/curl --curves X25519MLKEM768 https://pq.cloudflareresearch.com -v
```

### Option 3: Use the Generated Test Files (Recommended for Testing)

You already have test ClientHello files! These contain PQC algorithms:

```bash
# The files you generated contain PQC:
ls -lh *.bin
# pqc_hybrid_client_hello.bin - Contains X25519-MLKEM768
# pqc_pure_client_hello.bin - Contains ML-KEM-768
```

To test with these:

#### Method A: Create PCAP and Replay

```bash
# Install text2pcap (part of Wireshark)
brew install wireshark

# Convert binary to PCAP
text2pcap -T 443,443 pqc_hybrid_client_hello.bin pqc_hybrid.pcap

# Replay through Suricata
./src/suricata -c suricata.yaml -r pqc_hybrid.pcap -l ./logs

# Check results
jq 'select(.event_type=="tls") | .tls.pqc' logs/eve.json
```

#### Method B: Use Python to Send

```python
#!/usr/bin/env python3
import socket
import ssl

# Read the PQC ClientHello
with open('pqc_hybrid_client_hello.bin', 'rb') as f:
    client_hello = f.read()

# Send to a server (this will fail but Suricata will see it)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('pq.cloudflareresearch.com', 443))
    sock.send(client_hello)
    sock.close()
except:
    pass  # Expected to fail, but Suricata captured it
```

### Option 4: Use Firefox with PQC (If Available)

Firefox Nightly has experimental PQC support:

```bash
# Download Firefox Nightly
# Enable in about:config:
# security.tls.enable_kyber = true

# Then visit:
# https://pq.cloudflareresearch.com
```

### Option 5: Test with BoringSSL (Google's SSL)

```bash
# Clone and build BoringSSL with PQC
git clone https://github.com/google/boringssl.git
cd boringssl
mkdir build && cd build
cmake -GNinja ..
ninja

# Use bssl tool
./tool/bssl client -connect pq.cloudflareresearch.com:443
```

## Why Your Current Requests Show CLASSICAL

Looking at your output:
```
📊 Groups:      29, 23, 24, 25
📋 Group Names: X25519, secp256r1, secp384r1, secp521r1
```

These are all **classical** ECDH groups:
- 29 = X25519 (classical)
- 23 = secp256r1 (classical)
- 24 = secp384r1 (classical)
- 25 = secp521r1 (classical)

For PQC, you need groups like:
- 515 (0x0203) = X25519-MLKEM768 (hybrid PQC)
- 513 (0x0201) = ML-KEM-768 (pure PQC)
- 514 (0x0202) = ML-KEM-1024 (pure PQC)

## Quick Test with Generated Files

The **easiest way** to test PQC detection right now:

```bash
# 1. Install Wireshark (for text2pcap)
brew install wireshark

# 2. Convert test file to PCAP
text2pcap -T 443,443 pqc_hybrid_client_hello.bin pqc_test.pcap

# 3. Run Suricata on it
./src/suricata -c suricata.yaml -r pqc_test.pcap -l ./logs

# 4. Check results
jq 'select(.event_type=="tls") | .tls.pqc' logs/eve.json
```

You should see:
```json
{
  "posture": "PQC_HYBRID",
  "is_pqc": true,
  "supported_groups": [515, 29],
  "supported_groups_names": ["X25519-MLKEM768", "X25519"]
}
```

## Verify PQC Support in Your Client

Check if your curl supports PQC:

```bash
curl --version
# Look for "OpenSSL" version

openssl version
# Standard OpenSSL doesn't support PQC yet

# Check supported curves
openssl ecparam -list_curves
# Won't show Kyber/ML-KEM unless using OQS-OpenSSL
```

## Real-World PQC Testing

For production testing, you need:

1. **PQC-enabled client** (Chrome with flag, OQS-curl, etc.)
2. **PQC-enabled server** (Cloudflare, Google, etc.)
3. **Both must negotiate PQC** in the TLS handshake

Currently, most standard tools (curl, wget, etc.) don't support PQC yet, which is why you're seeing CLASSICAL.

## Summary

**To see real PQC detection:**

1. **Easiest**: Use the generated test files with text2pcap
   ```bash
   text2pcap -T 443,443 pqc_hybrid_client_hello.bin test.pcap
   ./src/suricata -c suricata.yaml -r test.pcap -l ./logs
   ```

2. **For live traffic**: Use Chrome with `--enable-features=PostQuantumKyber`

3. **For curl**: Build curl with OQS-OpenSSL support

The PQC detection in Suricata **is working correctly** - it's detecting that your current clients are using CLASSICAL crypto, which is accurate!