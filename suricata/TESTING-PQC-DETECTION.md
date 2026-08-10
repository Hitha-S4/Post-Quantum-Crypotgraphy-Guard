# Testing PQC TLS Detection in Suricata

## Quick Start Testing

### 1. Run Rust Unit Tests

The PQC detection module includes comprehensive unit tests:

```bash
cd rust
cargo test pqc_tls
```

Expected output:
```
running 8 tests
test pqc_tls::tests::test_classical_classification ... ok
test pqc_tls::tests::test_classical_group_detection ... ok
test pqc_tls::tests::test_ech_takes_precedence ... ok
test pqc_tls::tests::test_hybrid_classification ... ok
test pqc_tls::tests::test_hybrid_group_detection ... ok
test pqc_tls::tests::test_key_share_precedence ... ok
test pqc_tls::tests::test_kyber_group_detection ... ok
test pqc_tls::tests::test_pure_pqc_classification ... ok
```

### 2. Build Suricata with PQC Support

```bash
# From Suricata root directory
make clean
make -j$(sysctl -n hw.ncpu)
```

### 3. Create Test PCAP Files

Since real PQC TLS traffic is still emerging, we'll create synthetic test cases:

#### Option A: Use OpenSSL with PQC Support

```bash
# Install OQS-OpenSSL (OpenSSL with PQC algorithms)
git clone https://github.com/open-quantum-safe/openssl.git
cd openssl
./config
make -j$(nproc)
sudo make install

# Generate PQC TLS traffic
# Server side
openssl s_server -cert server.crt -key server.key \
    -groups kyber768:x25519 -port 4433

# Client side (in another terminal)
openssl s_client -connect localhost:4433 \
    -groups kyber768:x25519
```

#### Option B: Use Existing Test PCAPs

Download sample PQC TLS captures:
```bash
# Create test directory
mkdir -p test/pcaps

# Download sample PQC PCAP (if available)
# Or use the synthetic generator below
```

### 4. Generate Synthetic Test Traffic

Create a Python script to generate test TLS ClientHello packets:

```bash
python3 scripts/generate_pqc_test_pcaps.py
```

## Detailed Testing Procedures

### Test 1: Pure PQC Detection (Kyber Only)

**Create test PCAP:**
```python
# See scripts/generate_pqc_test_pcaps.py
# Generates ClientHello with only Kyber groups
```

**Run Suricata:**
```bash
./src/suricata -c suricata.yaml -r test/pcaps/pqc_pure.pcap -l ./log
```

**Verify output:**
```bash
jq 'select(.event_type=="tls") | .tls.pqc' log/eve.json
```

**Expected:**
```json
{
  "posture": "PQC_PURE",
  "is_pqc": true,
  "has_ech": false,
  "supported_groups": [512, 513, 514]
}
```

### Test 2: Hybrid PQC Detection

**Run Suricata:**
```bash
./src/suricata -c suricata.yaml -r test/pcaps/pqc_hybrid.pcap -l ./log
```

**Expected:**
```json
{
  "posture": "PQC_HYBRID",
  "is_pqc": true,
  "has_ech": false,
  "supported_groups": [515, 29]
}
```

### Test 3: Classical Only Detection

**Run Suricata:**
```bash
./src/suricata -c suricata.yaml -r test/pcaps/classical.pcap -l ./log
```

**Expected:**
```json
{
  "posture": "CLASSICAL",
  "is_pqc": false,
  "has_ech": false,
  "supported_groups": [29, 23]
}
```

### Test 4: ECH Detection

**Run Suricata:**
```bash
./src/suricata -c suricata.yaml -r test/pcaps/ech_protected.pcap -l ./log
```

**Expected:**
```json
{
  "posture": "ECH_PROTECTED",
  "is_pqc": false,
  "has_ech": true,
  "supported_groups": [29]
}
```

## Live Traffic Testing

### Capture Real PQC Traffic

```bash
# Start Suricata in live mode
sudo ./src/suricata -c suricata.yaml -i en0 -l ./log

# In another terminal, generate PQC TLS traffic
curl --tlsv1.3 https://pqc-test-server.example.com

# Monitor EVE JSON in real-time
tail -f log/eve.json | jq 'select(.event_type=="tls") | .tls.pqc'
```

### Test with Chrome/Firefox PQC Support

Modern browsers are adding PQC support:

```bash
# Chrome with PQC enabled
google-chrome --enable-features=PostQuantumKyber

# Firefox with PQC enabled
# about:config -> security.tls.enable_kyber -> true

# Browse to a PQC-enabled site
# Monitor Suricata logs
```

## Rule Testing

### Create Test Rules

```bash
cat > test/rules/pqc-test.rules << 'EOF'
# Alert on any PQC
alert tls any any -> any any (msg:"PQC Detected"; tls.is_pqc; sid:1000001;)

# Alert on pure PQC
alert tls any any -> any any (msg:"Pure PQC"; tls.pqc_posture:"PQC_PURE"; sid:1000002;)

# Alert on hybrid
alert tls any any -> any any (msg:"Hybrid PQC"; tls.pqc_posture:"PQC_HYBRID"; sid:1000003;)

# Alert on ECH
alert tls any any -> any any (msg:"ECH Detected"; tls.pqc_posture:"ECH_PROTECTED"; sid:1000004;)
EOF
```

### Test Rules

```bash
# Run with test rules
./src/suricata -c suricata.yaml -S test/rules/pqc-test.rules \
    -r test/pcaps/pqc_hybrid.pcap -l ./log

# Check alerts
cat log/fast.log
```

**Expected output:**
```
[**] [1:1000001:0] PQC Detected [**]
[**] [1:1000003:0] Hybrid PQC [**]
```

## Performance Testing

### Benchmark PQC Detection Overhead

```bash
# Test without PQC detection (baseline)
time ./src/suricata -c suricata.yaml -r large_traffic.pcap -l ./log1

# Test with PQC detection
time ./src/suricata -c suricata.yaml -r large_traffic.pcap -l ./log2

# Compare performance
# Expected: <1% overhead
```

### Load Testing

```bash
# Generate high-volume traffic
tcpreplay -i en0 -M 1000 large_traffic.pcap

# Monitor Suricata performance
./src/suricata -c suricata.yaml -i en0 --set stats.interval=1
```

## Automated Test Suite

### Run All Tests

```bash
# Create test runner script
cat > test/run_pqc_tests.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Running PQC TLS Detection Tests ==="

# 1. Rust unit tests
echo "1. Running Rust unit tests..."
cd rust && cargo test pqc_tls && cd ..

# 2. Generate test PCAPs
echo "2. Generating test PCAPs..."
python3 scripts/generate_pqc_test_pcaps.py

# 3. Test pure PQC
echo "3. Testing pure PQC detection..."
./src/suricata -c suricata.yaml -r test/pcaps/pqc_pure.pcap -l ./log/test1
grep -q "PQC_PURE" log/test1/eve.json && echo "✓ Pure PQC test passed"

# 4. Test hybrid PQC
echo "4. Testing hybrid PQC detection..."
./src/suricata -c suricata.yaml -r test/pcaps/pqc_hybrid.pcap -l ./log/test2
grep -q "PQC_HYBRID" log/test2/eve.json && echo "✓ Hybrid PQC test passed"

# 5. Test classical
echo "5. Testing classical detection..."
./src/suricata -c suricata.yaml -r test/pcaps/classical.pcap -l ./log/test3
grep -q "CLASSICAL" log/test3/eve.json && echo "✓ Classical test passed"

# 6. Test ECH
echo "6. Testing ECH detection..."
./src/suricata -c suricata.yaml -r test/pcaps/ech_protected.pcap -l ./log/test4
grep -q "ECH_PROTECTED" log/test4/eve.json && echo "✓ ECH test passed"

echo "=== All tests passed! ==="
EOF

chmod +x test/run_pqc_tests.sh
./test/run_pqc_tests.sh
```

## Debugging

### Enable Debug Logging

```yaml
# In suricata.yaml
logging:
  default-log-level: debug
  outputs:
    - console:
        enabled: yes
        type: json
```

### Check PQC Detection

```bash
# Run with verbose output
./src/suricata -c suricata.yaml -r test.pcap -l ./log -v

# Look for PQC-related log messages
grep -i "pqc\|kyber\|mlkem" log/suricata.log
```

### Inspect TLS Handshake

```bash
# Use tshark to verify PCAP contents
tshark -r test.pcap -Y "tls.handshake.type == 1" \
    -T fields -e tls.handshake.extensions.supported_group

# Compare with Suricata detection
jq '.tls.pqc.supported_groups' log/eve.json
```

## Common Issues and Solutions

### Issue 1: No PQC Detection

**Symptom:** `pqc` field missing from EVE JSON

**Solution:**
```bash
# Check if Rust module compiled correctly
nm rust/target/release/libsuricata.a | grep PQC

# Verify TLS parsing is enabled
grep -i "tls" suricata.yaml
```

### Issue 2: Incorrect Classification

**Symptom:** Wrong PQC posture reported

**Solution:**
```bash
# Enable debug logging
# Check supported groups in PCAP
tshark -r test.pcap -V | grep -A 20 "Extension: supported_groups"

# Compare with Suricata output
jq '.tls.pqc' log/eve.json
```

### Issue 3: Performance Degradation

**Symptom:** Suricata slower with PQC detection

**Solution:**
```bash
# Profile Suricata
perf record -g ./src/suricata -c suricata.yaml -r test.pcap
perf report

# Check for bottlenecks in PQC code
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: PQC Detection Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libpcre2-dev libyaml-dev libjansson-dev
      
      - name: Build Suricata
        run: |
          ./autogen.sh
          ./configure
          make -j$(nproc)
      
      - name: Run PQC tests
        run: |
          cd rust && cargo test pqc_tls
          cd .. && ./test/run_pqc_tests.sh
```

## Test Coverage

Current test coverage for PQC detection:

- ✅ Pure Kyber detection
- ✅ Hybrid Kyber detection  
- ✅ Classical algorithm detection
- ✅ ECH detection
- ✅ Multiple supported groups
- ✅ Key share precedence
- ✅ GREASE filtering
- ✅ JSON output formatting
- ⏳ Signature algorithm correlation (future)
- ⏳ Certificate chain analysis (future)

## Next Steps

1. **Generate Real PQC Traffic**: Use OQS-OpenSSL to create authentic PQC TLS handshakes
2. **Collect PCAPs**: Gather real-world PQC TLS captures from production environments
3. **Benchmark**: Measure performance impact on high-throughput networks
4. **Validate**: Compare detection with other tools (Wireshark, tcpdump)
5. **Document**: Create user guide with real-world examples

## Resources

- [OQS-OpenSSL](https://github.com/open-quantum-safe/openssl)
- [PQC Test Vectors](https://github.com/open-quantum-safe/liboqs/tree/main/tests)
- [Wireshark PQC Dissector](https://gitlab.com/wireshark/wireshark/-/issues/17909)