# Suricata TLS Configuration for Algorithm Extraction

## Problem

The Kafka messages are missing TLS handshake details needed for PQC detection:
- No `supported_groups`
- No `key_share` 
- No `signature_algorithms`
- No cipher suite information

## Required Suricata Configuration

### 1. Enable TLS Logging in `suricata.yaml`

```yaml
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: eve.json
      types:
        - tls:
            enabled: yes
            extended: yes  # CRITICAL: Enable extended TLS logging
            custom: [subject, issuer, serial, fingerprint, sni, version, not_before, not_after]
            # Enable JA3 fingerprinting
            ja3-fingerprints: yes
```

### 2. Enable TLS Protocol Analysis

```yaml
app-layer:
  protocols:
    tls:
      enabled: yes
      detection-ports:
        dp: 443, 465, 563, 636, 853, 989, 990, 992, 993, 995, 5061
      
      # CRITICAL: Enable JA3 fingerprinting for algorithm detection
      ja3-fingerprints: yes
      
      # Enable extended logging
      extended-logging: yes
```

### 3. Expected TLS Event Structure

With proper configuration, Suricata should produce events like:

```json
{
  "timestamp": "2026-02-10T14:57:09.141000+0530",
  "event_type": "tls",
  "src_ip": "9.109.217.201",
  "src_port": 52408,
  "dest_ip": "104.18.11.13",
  "dest_port": 443,
  "proto": "TCP",
  "app_proto": "tls",
  "tls": {
    "version": "TLS 1.3",
    "sni": "example.com",
    "cipher_suite_name": "TLS_AES_128_GCM_SHA256",
    "supported_groups": ["x25519", "secp256r1", "secp384r1"],
    "key_share": ["x25519"],
    "signature_algorithms": [
      "ecdsa_secp256r1_sha256",
      "rsa_pss_rsae_sha256",
      "rsa_pkcs1_sha256"
    ],
    "ja3": {
      "hash": "abc123...",
      "string": "771,4865-4866-4867..."
    }
  }
}
```

## Verification Steps

### 1. Check Suricata Logs

```bash
# Check if TLS events are being logged
tail -f /var/log/suricata/eve.json | grep '"event_type":"tls"'
```

### 2. Verify TLS Fields

```bash
# Check for supported_groups in TLS events
tail -f /var/log/suricata/eve.json | jq 'select(.event_type=="tls") | .tls.supported_groups'
```

### 3. Test with Known TLS Connection

```bash
# Generate TLS traffic
curl -v https://www.cloudflare.com

# Check Suricata captured it
tail -20 /var/log/suricata/eve.json | jq 'select(.tls.sni=="www.cloudflare.com")'
```

## Alternative: Flow Events with TLS Data

Some Suricata versions include TLS data in flow events:

```json
{
  "event_type": "flow",
  "app_proto": "tls",
  "flow": {
    "bytes_toserver": 2227,
    "bytes_toclient": 4851
  },
  "tls": {
    "version": "TLS 1.3",
    "supported_groups": ["x25519"],
    "key_share": ["x25519"],
    "signature_algorithms": ["ecdsa_secp256r1_sha256"]
  }
}
```

Our code already handles this case (see [`kafka_consumer.py:147`](../src/ngfw_pqc_detector/services/kafka_consumer.py:147)).

## Troubleshooting

### Issue: No TLS Events Generated

**Cause**: TLS logging not enabled or traffic not being captured

**Solution**:
1. Verify Suricata is running: `systemctl status suricata`
2. Check configuration: `suricata -T -c /etc/suricata/suricata.yaml`
3. Restart Suricata: `systemctl restart suricata`

### Issue: TLS Events Missing Algorithm Fields

**Cause**: Extended logging not enabled

**Solution**:
1. Set `extended: yes` in TLS output configuration
2. Enable `ja3-fingerprints: yes`
3. Restart Suricata

### Issue: Only Flow Events, No TLS Events

**Cause**: TLS event type not enabled in outputs

**Solution**:
```yaml
outputs:
  - eve-log:
      types:
        - tls:
            enabled: yes  # Make sure this is yes
```

## Current Behavior

Without TLS handshake data, the system:
- ✅ Detects TLS protocol (`app_proto: "tls"`)
- ✅ Captures byte counts for heuristic detection
- ❌ Cannot extract algorithms (empty arrays)
- ❌ Cannot perform accurate PQC classification
- ⚠️ Falls back to byte-based heuristics only

## Expected Behavior with Fix

With proper TLS logging:
- ✅ Extracts supported_groups, key_share, signature_algorithms
- ✅ Performs algorithm-based PQC detection
- ✅ Classifies as PQC/Hybrid/Classical with high confidence
- ✅ Provides detailed algorithm information in WebSocket messages

## References

- [Suricata TLS Documentation](https://suricata.readthedocs.io/en/latest/output/eve/eve-json-output.html#tls)
- [JA3 Fingerprinting](https://github.com/salesforce/ja3)
- Our implementation: [`kafka_consumer.py`](../src/ngfw_pqc_detector/services/kafka_consumer.py)