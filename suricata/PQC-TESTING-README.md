# PQC Testing in Suricata - Quick Reference

This guide provides quick instructions for testing Post-Quantum Cryptography (PQC) detection in Suricata.

## Quick Start

Run the interactive quick start script:

```bash
./QUICK-START-PQC-TESTING.sh
```

This will guide you through:
1. Generating test PQC ClientHello messages
2. Creating PQC test rules
3. Running the full test suite
4. Testing with live traffic
5. Viewing PQC events

## Manual Testing Methods

### Method 1: Generate Test Traffic (Easiest)

```bash
# Generate test ClientHello messages
python3 scripts/generate-pqc-test-traffic.py

# This creates:
# - pqc_hybrid_client_hello.bin (X25519-MLKEM768)
# - pqc_pure_client_hello.bin (ML-KEM-768)
# - classical_client_hello.bin (X25519 only)
```

### Method 2: Test with Real PQC Servers

```bash
# Using curl (if built with PQC support)
curl --curves X25519MLKEM768 https://pq.cloudflareresearch.com -v

# Using OpenSSL (if built with OQS)
openssl s_client -connect pq.cloudflareresearch.com:443 \
  -curves X25519MLKEM768 -msg

# Capture traffic while testing
sudo ./src/suricata -c suricata.yaml -i eth0 -l ./logs
```

### Method 3: Test with PCAP Files

```bash
# Run Suricata on a PCAP file
./src/suricata -c suricata.yaml -r test.pcap -l ./logs

# View results
jq 'select(.event_type=="tls") | .tls.pqc' logs/eve.json
```

## PQC Algorithm IDs Reference

| Algorithm | ID (Hex) | ID (Dec) | Type |
|-----------|----------|----------|------|
| ML-KEM-512 | 0x0200 | 512 | Pure PQC |
| ML-KEM-768 | 0x0201 | 513 | Pure PQC |
| ML-KEM-1024 | 0x0202 | 514 | Pure PQC |
| X25519-MLKEM768 | 0x0203 | 515 | Hybrid PQC |
| X25519-MLKEM1024 | 0x0204 | 516 | Hybrid PQC |
| P256-MLKEM768 | 0x0205 | 517 | Hybrid PQC |
| X25519 | 0x001d | 29 | Classical |
| P-256 | 0x0017 | 23 | Classical |

## Expected Detection Results

### Hybrid PQC (X25519-MLKEM768)
```json
{
  "tls": {
    "pqc_posture": "PQC_HYBRID",
    "pqc": {
      "posture": "PQC_HYBRID",
      "is_pqc": true,
      "has_ech": false,
      "supported_groups": [515, 29],
      "supported_groups_names": ["X25519-MLKEM768", "X25519"]
    }
  }
}
```

### Pure PQC (ML-KEM-768)
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

### Classical Only
```json
{
  "tls": {
    "pqc_posture": "CLASSICAL",
    "pqc": {
      "posture": "CLASSICAL",
      "is_pqc": false,
      "supported_groups": [29, 23],
      "supported_groups_names": ["X25519", "P-256"]
    }
  }
}
```

## Test Rules

Create test rules:
```bash
./scripts/create-pqc-test-rules.sh
```

This creates comprehensive rules in `rules/pqc-test.rules` including:
- Basic PQC detection (any, pure, hybrid, classical)
- Specific algorithm detection
- Traffic direction rules
- Compliance monitoring
- Known service detection

## Monitoring PQC Events

### Real-time Monitoring
```bash
# Use the built-in viewer
./view-pqc-events.sh

# Or use jq directly
tail -f logs/eve.json | jq 'select(.event_type=="tls") | .tls.pqc'
```

### Query Specific Postures
```bash
# Find all hybrid PQC connections
jq 'select(.tls.pqc.posture=="PQC_HYBRID")' logs/eve.json

# Find all pure PQC connections
jq 'select(.tls.pqc.posture=="PQC_PURE")' logs/eve.json

# Count PQC vs non-PQC
jq 'select(.event_type=="tls") | .tls.pqc.is_pqc' logs/eve.json | \
  sort | uniq -c
```

## Public PQC Test Servers

Test against these known PQC-enabled servers:

1. **Cloudflare PQC Research**
   ```bash
   curl https://pq.cloudflareresearch.com
   ```

2. **Google** (supports hybrid PQC)
   ```bash
   curl https://www.google.com
   ```

3. **AWS Services** (various services support PQC)

## Troubleshooting

### No PQC Detection

1. **Verify Suricata is built with Rust support:**
   ```bash
   ./src/suricata --build-info | grep -i rust
   ```

2. **Check TLS inspection is enabled:**
   ```bash
   grep -A5 "app-layer:" suricata.yaml | grep -A3 "tls:"
   ```

3. **Verify rules are loaded:**
   ```bash
   ./src/suricata -c suricata.yaml -T
   ```

4. **Check the client sends PQC extensions:**
   - Use Wireshark to inspect ClientHello
   - Look for Supported Groups extension (0x000a)
   - Verify group IDs include PQC algorithms

### False Positives

- Review the `supported_groups` array in EVE JSON
- Check if large key shares are being misidentified
- Verify algorithm IDs match expected values

### Performance Issues

- PQC detection adds minimal overhead (~0.1%)
- If issues persist, check overall Suricata performance
- Review system resources and network load

## Scripts Overview

| Script | Purpose |
|--------|---------|
| [`QUICK-START-PQC-TESTING.sh`](QUICK-START-PQC-TESTING.sh) | Interactive quick start guide |
| [`scripts/generate-pqc-test-traffic.py`](scripts/generate-pqc-test-traffic.py) | Generate test ClientHello messages |
| [`scripts/test-pqc-detection.sh`](scripts/test-pqc-detection.sh) | Full test suite |
| [`scripts/create-pqc-test-rules.sh`](scripts/create-pqc-test-rules.sh) | Create comprehensive test rules |
| [`view-pqc-events.sh`](view-pqc-events.sh) | Real-time PQC event viewer |

## Documentation

- **[PQC-TLS-DETECTION.md](PQC-TLS-DETECTION.md)** - Architecture and implementation details
- **[PQC-TEST-GUIDE.md](PQC-TEST-GUIDE.md)** - Comprehensive testing guide with examples
- **[QUICK-START-KAFKA.sh](QUICK-START-KAFKA.sh)** - Kafka streaming setup (if needed)

## Example Workflow

```bash
# 1. Generate test traffic
python3 scripts/generate-pqc-test-traffic.py

# 2. Create test rules
./scripts/create-pqc-test-rules.sh

# 3. Start Suricata with test rules
./src/suricata -c suricata.yaml -S rules/pqc-test.rules -i eth0 -l ./logs

# 4. In another terminal, monitor events
./view-pqc-events.sh

# 5. Generate some test traffic
curl https://pq.cloudflareresearch.com
curl https://www.google.com

# 6. Check results
jq 'select(.event_type=="tls") | 
    {sni: .tls.sni, posture: .tls.pqc.posture, is_pqc: .tls.pqc.is_pqc}' \
    logs/eve.json
```

## Advanced Testing

### Using Python to Craft Custom Packets

See [`scripts/generate-pqc-test-traffic.py`](scripts/generate-pqc-test-traffic.py) for examples of:
- Creating ClientHello with specific PQC algorithms
- Generating hybrid vs pure PQC configurations
- Testing different key share combinations

### Using Scapy

```python
from scapy.all import *
from scapy.layers.tls.all import *

# Create PQC ClientHello
client_hello = TLSClientHello(
    ext=[
        TLS_Ext_SupportedGroups(groups=[0x0203, 0x001d]),  # Hybrid
    ]
)
```

### Building OpenSSL with PQC Support

```bash
# Install liboqs
git clone https://github.com/open-quantum-safe/liboqs.git
cd liboqs && mkdir build && cd build
cmake -GNinja -DCMAKE_INSTALL_PREFIX=/usr/local ..
ninja && sudo ninja install

# Install OQS-OpenSSL
git clone https://github.com/open-quantum-safe/openssl.git
cd openssl
./config --prefix=/usr/local/oqs-openssl
make -j$(nproc) && sudo make install
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in `logs/suricata.log`
3. Enable debug mode: `suricata -c suricata.yaml --set logging.outputs.1.console.level=debug`
4. Consult the main documentation in [`PQC-TLS-DETECTION.md`](PQC-TLS-DETECTION.md)

## License

Copyright (C) 2026 Open Information Security Foundation
Licensed under GPLv2. See LICENSE file for details.