# PQC TLS Testing Guide

This guide explains how to create and test Post-Quantum Cryptography (PQC) compatible TLS requests in Suricata.

## Overview

Suricata's PQC detection identifies TLS connections based on:
- **Supported Groups Extension (0x000a)**: Lists key exchange algorithms the client supports
- **Key Share Extension (0x0033)**: Contains actual key exchange data
- **Encrypted Client Hello (0xfe0d)**: ECH extension

## PQC Algorithm IDs

### Pure PQC (Kyber/ML-KEM)
- `0x0200` (512) - ML-KEM-512
- `0x0201` (513) - ML-KEM-768
- `0x0202` (514) - ML-KEM-1024

### Hybrid PQC (Kyber + Classical)
- `0x0203` (515) - X25519-MLKEM768
- `0x0204` (516) - X25519-MLKEM1024
- `0x0205` (517) - P256-MLKEM768

### Classical ECDH
- `0x001d` (29) - X25519
- `0x0017` (23) - secp256r1 (P-256)

## Testing Methods

### Method 1: Using OpenSSL with PQC Support

#### Prerequisites
Build OpenSSL with OQS (Open Quantum Safe) provider:

```bash
# Install liboqs
git clone https://github.com/open-quantum-safe/liboqs.git
cd liboqs
mkdir build && cd build
cmake -GNinja -DCMAKE_INSTALL_PREFIX=/usr/local ..
ninja && sudo ninja install

# Install OQS-OpenSSL
git clone https://github.com/open-quantum-safe/openssl.git
cd openssl
./config --prefix=/usr/local/oqs-openssl
make -j$(nproc)
sudo make install
```

#### Generate PQC TLS Requests

**Pure PQC (Kyber only):**
```bash
/usr/local/oqs-openssl/bin/openssl s_client \
  -connect example.com:443 \
  -curves kyber768 \
  -msg -debug
```

**Hybrid PQC (X25519 + Kyber):**
```bash
/usr/local/oqs-openssl/bin/openssl s_client \
  -connect example.com:443 \
  -curves X25519MLKEM768:kyber768:X25519 \
  -msg -debug
```

**Classical only:**
```bash
openssl s_client \
  -connect example.com:443 \
  -curves X25519:prime256v1 \
  -msg -debug
```

### Method 2: Using curl with PQC Support

```bash
# Build curl with OQS-OpenSSL
git clone https://github.com/curl/curl.git
cd curl
./buildconf
./configure --with-openssl=/usr/local/oqs-openssl
make -j$(nproc)
sudo make install

# Test with PQC
curl --curves X25519MLKEM768 https://example.com -v
```

### Method 3: Using Python with Cryptography Library

```python
#!/usr/bin/env python3
"""
Generate PQC TLS ClientHello for testing
"""
import socket
import struct

def create_pqc_client_hello(hostname, groups, key_share_groups=None):
    """
    Create a TLS 1.3 ClientHello with PQC support
    
    Args:
        hostname: Server hostname for SNI
        groups: List of supported group IDs (e.g., [515, 29] for hybrid)
        key_share_groups: List of groups to include in key_share (optional)
    """
    
    # TLS 1.3 ClientHello structure
    client_hello = bytearray()
    
    # Handshake header
    client_hello.extend(b'\x16')  # Content Type: Handshake
    client_hello.extend(b'\x03\x01')  # Legacy version: TLS 1.0
    
    # Placeholder for length (will be filled later)
    length_pos = len(client_hello)
    client_hello.extend(b'\x00\x00')
    
    # Handshake Type: ClientHello
    client_hello.extend(b'\x01')
    
    # Placeholder for handshake length
    hs_length_pos = len(client_hello)
    client_hello.extend(b'\x00\x00\x00')
    
    # Client Version: TLS 1.2 (for compatibility)
    client_hello.extend(b'\x03\x03')
    
    # Random (32 bytes)
    import os
    client_hello.extend(os.urandom(32))
    
    # Session ID (empty)
    client_hello.extend(b'\x00')
    
    # Cipher Suites (TLS 1.3 suites)
    cipher_suites = [
        0x1301,  # TLS_AES_128_GCM_SHA256
        0x1302,  # TLS_AES_256_GCM_SHA384
        0x1303,  # TLS_CHACHA20_POLY1305_SHA256
    ]
    client_hello.extend(struct.pack('!H', len(cipher_suites) * 2))
    for suite in cipher_suites:
        client_hello.extend(struct.pack('!H', suite))
    
    # Compression Methods (none)
    client_hello.extend(b'\x01\x00')
    
    # Extensions
    extensions = bytearray()
    
    # SNI Extension (0x0000)
    sni_ext = bytearray()
    sni_ext.extend(struct.pack('!H', 0x0000))  # Extension type
    sni_data = bytearray()
    sni_data.extend(struct.pack('!H', len(hostname) + 5))  # List length
    sni_data.extend(b'\x00')  # Name type: hostname
    sni_data.extend(struct.pack('!H', len(hostname)))
    sni_data.extend(hostname.encode())
    sni_ext.extend(struct.pack('!H', len(sni_data)))
    sni_ext.extend(sni_data)
    extensions.extend(sni_ext)
    
    # Supported Groups Extension (0x000a) - THE KEY FOR PQC DETECTION
    groups_ext = bytearray()
    groups_ext.extend(struct.pack('!H', 0x000a))  # Extension type
    groups_data = bytearray()
    groups_data.extend(struct.pack('!H', len(groups) * 2))
    for group in groups:
        groups_data.extend(struct.pack('!H', group))
    groups_ext.extend(struct.pack('!H', len(groups_data)))
    groups_ext.extend(groups_data)
    extensions.extend(groups_ext)
    
    # Supported Versions Extension (0x002b)
    versions_ext = bytearray()
    versions_ext.extend(struct.pack('!H', 0x002b))
    versions_ext.extend(struct.pack('!H', 3))  # Length
    versions_ext.extend(b'\x02')  # Length of versions
    versions_ext.extend(b'\x03\x04')  # TLS 1.3
    extensions.extend(versions_ext)
    
    # Key Share Extension (0x0033) - Optional but important
    if key_share_groups:
        keyshare_ext = bytearray()
        keyshare_ext.extend(struct.pack('!H', 0x0033))
        keyshare_data = bytearray()
        
        for group in key_share_groups:
            keyshare_data.extend(struct.pack('!H', group))
            # Generate dummy key exchange data
            if group in [0x0200, 0x0201, 0x0202]:  # Pure Kyber
                key_size = 800  # Approximate Kyber public key size
            elif group in [0x0203, 0x0204, 0x0205]:  # Hybrid
                key_size = 832  # X25519 (32) + Kyber (800)
            else:  # Classical
                key_size = 32
            
            keyshare_data.extend(struct.pack('!H', key_size))
            keyshare_data.extend(os.urandom(key_size))
        
        keyshare_ext.extend(struct.pack('!H', len(keyshare_data) + 2))
        keyshare_ext.extend(struct.pack('!H', len(keyshare_data)))
        keyshare_ext.extend(keyshare_data)
        extensions.extend(keyshare_ext)
    
    # Add extensions to ClientHello
    client_hello.extend(struct.pack('!H', len(extensions)))
    client_hello.extend(extensions)
    
    # Fill in lengths
    total_length = len(client_hello) - length_pos - 2
    struct.pack_into('!H', client_hello, length_pos, total_length)
    
    hs_length = len(client_hello) - hs_length_pos - 3
    struct.pack_into('!I', client_hello, hs_length_pos, hs_length)[1:]
    
    return bytes(client_hello)


# Example usage
if __name__ == "__main__":
    # Test 1: Hybrid PQC (X25519-MLKEM768)
    print("Generating Hybrid PQC ClientHello...")
    hello = create_pqc_client_hello(
        "example.com",
        groups=[0x0203, 0x001d],  # X25519-MLKEM768, X25519
        key_share_groups=[0x0203]
    )
    
    # Save to file for replay
    with open("pqc_hybrid_client_hello.bin", "wb") as f:
        f.write(hello)
    print(f"Saved {len(hello)} bytes to pqc_hybrid_client_hello.bin")
    
    # Test 2: Pure PQC (Kyber only)
    print("\nGenerating Pure PQC ClientHello...")
    hello = create_pqc_client_hello(
        "example.com",
        groups=[0x0201],  # ML-KEM-768
        key_share_groups=[0x0201]
    )
    
    with open("pqc_pure_client_hello.bin", "wb") as f:
        f.write(hello)
    print(f"Saved {len(hello)} bytes to pqc_pure_client_hello.bin")
    
    # Test 3: Classical only
    print("\nGenerating Classical ClientHello...")
    hello = create_pqc_client_hello(
        "example.com",
        groups=[0x001d, 0x0017],  # X25519, P-256
        key_share_groups=[0x001d]
    )
    
    with open("classical_client_hello.bin", "wb") as f:
        f.write(hello)
    print(f"Saved {len(hello)} bytes to classical_client_hello.bin")
```

### Method 4: Using Scapy to Craft Packets

```python
#!/usr/bin/env python3
"""
Craft PQC TLS packets using Scapy
"""
from scapy.all import *
from scapy.layers.tls.all import *

def send_pqc_client_hello(target_ip, target_port=443, pqc_type="hybrid"):
    """
    Send a PQC TLS ClientHello using Scapy
    """
    
    # Define supported groups based on PQC type
    if pqc_type == "pure":
        groups = [0x0201]  # ML-KEM-768
    elif pqc_type == "hybrid":
        groups = [0x0203, 0x001d]  # X25519-MLKEM768, X25519
    else:  # classical
        groups = [0x001d, 0x0017]  # X25519, P-256
    
    # Create TLS ClientHello
    client_hello = TLSClientHello(
        version=0x0303,  # TLS 1.2 for compatibility
        ciphers=[
            0x1301,  # TLS_AES_128_GCM_SHA256
            0x1302,  # TLS_AES_256_GCM_SHA384
        ],
        ext=[
            TLS_Ext_ServerName(servernames=[ServerName(servername=b"example.com")]),
            TLS_Ext_SupportedGroups(groups=groups),
            TLS_Ext_SupportedVersions(versions=[0x0304]),  # TLS 1.3
        ]
    )
    
    # Wrap in TLS record
    tls_record = TLS(msg=[client_hello])
    
    # Create TCP/IP packet
    packet = IP(dst=target_ip)/TCP(dport=target_port, flags="S")/tls_record
    
    # Send packet
    send(packet)
    print(f"Sent {pqc_type} PQC ClientHello to {target_ip}:{target_port}")

if __name__ == "__main__":
    # Test different PQC types
    send_pqc_client_hello("93.184.216.34", pqc_type="hybrid")
    send_pqc_client_hello("93.184.216.34", pqc_type="pure")
    send_pqc_client_hello("93.184.216.34", pqc_type="classical")
```

### Method 5: Using tcpreplay with Pre-captured PCAPs

```bash
# Capture PQC traffic from a PQC-enabled client
sudo tcpdump -i any -w pqc_traffic.pcap 'tcp port 443'

# Replay the traffic through Suricata
tcpreplay -i eth0 pqc_traffic.pcap

# Or use Suricata directly on the PCAP
./src/suricata -c suricata.yaml -r pqc_traffic.pcap -l ./logs
```

## Testing with Suricata

### 1. Create Test Rules

Create `rules/pqc-test.rules`:

```
# Alert on any PQC usage
alert tls any any -> any any (msg:"TEST: PQC TLS Detected"; tls.is_pqc; sid:9000001; rev:1;)

# Alert on pure PQC
alert tls any any -> any any (msg:"TEST: Pure PQC Connection"; tls.pqc_posture:"PQC_PURE"; sid:9000002; rev:1;)

# Alert on hybrid PQC
alert tls any any -> any any (msg:"TEST: Hybrid PQC Connection"; tls.pqc_posture:"PQC_HYBRID"; sid:9000003; rev:1;)

# Alert on classical only
alert tls any any -> any any (msg:"TEST: Classical TLS Only"; tls.pqc_posture:"CLASSICAL"; sid:9000004; rev:1;)

# Alert on ECH
alert tls any any -> any any (msg:"TEST: ECH Detected"; tls.pqc_posture:"ECH_PROTECTED"; sid:9000005; rev:1;)
```

### 2. Run Suricata with Test Rules

```bash
# Start Suricata with test rules
./src/suricata -c suricata.yaml -S rules/pqc-test.rules -i eth0 -l ./logs

# Or test with PCAP
./src/suricata -c suricata.yaml -S rules/pqc-test.rules -r test.pcap -l ./logs
```

### 3. Monitor Results

```bash
# Watch for PQC events in real-time
./view-pqc-events.sh

# Check alerts
tail -f logs/fast.log

# Analyze EVE JSON
jq 'select(.event_type=="tls") | .tls.pqc' logs/eve.json
```

## Expected EVE JSON Output

### Hybrid PQC Connection
```json
{
  "timestamp": "2026-02-09T10:00:00.000000+0000",
  "event_type": "tls",
  "tls": {
    "version": "TLS 1.3",
    "sni": "example.com",
    "pqc_posture": "PQC_HYBRID",
    "pqc": {
      "posture": "PQC_HYBRID",
      "is_pqc": true,
      "has_ech": false,
      "supported_groups": [515, 29],
      "supported_groups_names": ["X25519-MLKEM768", "X25519"],
      "key_share_groups": [515],
      "key_share_groups_names": ["X25519-MLKEM768"]
    }
  }
}
```

### Pure PQC Connection
```json
{
  "tls": {
    "pqc_posture": "PQC_PURE",
    "pqc": {
      "posture": "PQC_PURE",
      "is_pqc": true,
      "supported_groups": [513],
      "supported_groups_names": ["ML-KEM-768"]
    }
  }
}
```

## Quick Test Servers

### Public PQC Test Servers
- **Cloudflare**: `https://pq.cloudflareresearch.com`
- **Google**: `https://www.google.com` (supports hybrid PQC)
- **AWS**: Various AWS services support PQC

### Local Test Server

```bash
# Using OQS-OpenSSL to create a test server
/usr/local/oqs-openssl/bin/openssl s_server \
  -accept 4433 \
  -cert server.crt \
  -key server.key \
  -curves X25519MLKEM768:kyber768 \
  -www
```

## Troubleshooting

### No PQC Detection
1. Verify Suricata is built with Rust support
2. Check that TLS inspection is enabled in `suricata.yaml`
3. Ensure rules are loaded correctly
4. Verify the client actually sends PQC extensions

### False Positives
1. Check for large key shares that might be misidentified
2. Review supported groups in ClientHello
3. Verify algorithm IDs match expected values

### Performance Issues
1. PQC detection adds minimal overhead (~0.1%)
2. If issues persist, check overall Suricata performance
3. Review system resources and network load

## References

- [NIST PQC Project](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [Open Quantum Safe](https://openquantumsafe.org/)
- [TLS 1.3 RFC 8446](https://datatracker.ietf.org/doc/html/rfc8446)
- [Hybrid Key Exchange Draft](https://datatracker.ietf.org/doc/draft-ietf-tls-hybrid-design/)