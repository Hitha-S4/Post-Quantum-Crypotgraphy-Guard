# PQC TLS Enforcement Guide

This guide explains how to use the PQC (Post-Quantum Cryptography) enforcement feature in Suricata to drop non-PQC TLS connections.

## Overview

The PQC enforcement feature allows you to:
- **Drop non-PQC TLS connections** automatically based on configuration
- **Enable/disable enforcement dynamically** by reloading configuration
- **Use Suricata rules** for fine-grained control over which connections to drop
- **Monitor PQC adoption** in your network before enforcing

## Architecture

The implementation consists of:

1. **Configuration Flag** (`suricata.yaml`): Global on/off switch
2. **Stream TCP Flag** (`STREAMTCP_INIT_FLAG_DROP_NON_PQC`): Runtime flag
3. **Flow Marking** (`FLOW_ACTION_DROP`): Marks flows for dropping
4. **PQC Detection** (Rust): Classifies TLS connections as PQC_PURE, PQC_HYBRID, or CLASSICAL
5. **Suricata Rules**: Fine-grained control and logging

## Configuration

### Method 1: Global Configuration (Recommended for Production)

Edit `suricata.yaml`:

```yaml
stream:
  pqc:
    drop-non-pqc: yes  # Set to 'yes' to drop all non-PQC TLS connections
```

**Advantages:**
- Simple on/off switch
- Applies to all TLS traffic
- Can be changed without restarting (reload configuration)

**Use Cases:**
- Enforce PQC across entire network
- Compliance requirements
- Zero-trust security posture

### Method 2: Rule-Based Control (Recommended for Gradual Rollout)

Keep global flag disabled and use rules from `rules/pqc-enforcement.rules`:

```yaml
stream:
  pqc:
    drop-non-pqc: no  # Keep disabled, use rules for control
```

Then enable specific drop rules:

```
# Drop non-PQC to sensitive servers
drop tls any any -> 192.168.1.100 443 (msg:"Dropping non-PQC TLS to financial server"; \
    flow:established,to_server; \
    tls.pqc_posture:"CLASSICAL"; \
    sid:1000011; rev:1;)
```

**Advantages:**
- Granular control per IP, port, or network
- Can create exceptions with pass rules
- Easier gradual rollout
- Better logging and visibility

**Use Cases:**
- Testing phase
- Mixed environment (legacy + modern systems)
- Selective enforcement by security zone

## Deployment Strategies

### Strategy 1: Monitoring Phase (Week 1-2)

**Goal:** Understand PQC adoption in your environment

1. Set `drop-non-pqc: no`
2. Enable alert rules only:
   ```
   alert tls any any -> any any (msg:"Non-PQC TLS connection detected"; \
       tls.pqc_posture:"CLASSICAL"; sid:1000001;)
   ```
3. Monitor `eve.json` for PQC posture data
4. Identify systems that don't support PQC

**Expected Output:**
```json
{
  "tls": {
    "pqc_posture": "CLASSICAL",
    "pqc_details": {
      "supported_groups": ["x25519", "secp256r1"],
      "key_share_groups": ["x25519"]
    }
  }
}
```

### Strategy 2: Selective Enforcement (Week 3-4)

**Goal:** Enforce PQC for high-security zones

1. Keep `drop-non-pqc: no`
2. Enable drop rules for critical servers:
   ```
   drop tls any any -> $FINANCIAL_SERVERS 443 (msg:"Drop non-PQC to financial"; \
       tls.pqc_posture:"CLASSICAL"; sid:1000011;)
   ```
3. Add pass rules for known legacy systems:
   ```
   pass tls any any -> 192.168.1.200 443 (msg:"Allow legacy system"; \
       tls.pqc_posture:"CLASSICAL"; sid:1000020;)
   ```
4. Monitor dropped connections

### Strategy 3: Full Enforcement (Week 5+)

**Goal:** Enforce PQC network-wide

1. Set `drop-non-pqc: yes`
2. Add pass rules for necessary exceptions
3. Monitor and adjust exceptions as needed

## Dynamic Enable/Disable

### Reload Configuration (No Restart Required)

```bash
# Edit suricata.yaml
vim /etc/suricata/suricata.yaml

# Change drop-non-pqc value
stream:
  pqc:
    drop-non-pqc: yes  # or no

# Reload configuration
sudo kill -USR2 $(pidof suricata)
# or
sudo suricatasc -c reload-config
```

### Reload Rules (No Restart Required)

```bash
# Edit rules
vim /etc/suricata/rules/pqc-enforcement.rules

# Reload rules
sudo kill -USR2 $(pidof suricata)
# or
sudo suricatasc -c reload-rules
```

## Monitoring and Logging

### Check PQC Status in Logs

```bash
# View PQC classifications
jq 'select(.event_type=="tls") | {timestamp, src_ip, dest_ip, pqc_posture: .tls.pqc_posture}' /var/log/suricata/eve.json

# Count PQC vs Classical connections
jq -r 'select(.event_type=="tls") | .tls.pqc_posture' /var/log/suricata/eve.json | sort | uniq -c

# Find dropped non-PQC connections
jq 'select(.event_type=="alert" and .alert.signature_id==1000010)' /var/log/suricata/eve.json
```

### Expected Log Output

**PQC Pure Connection:**
```json
{
  "timestamp": "2026-02-09T12:00:00.000000+0000",
  "event_type": "tls",
  "src_ip": "192.168.1.10",
  "dest_ip": "93.184.216.34",
  "tls": {
    "pqc_posture": "PQC_PURE",
    "pqc_details": {
      "supported_groups": ["mlkem768"],
      "key_share_groups": ["mlkem768"],
      "has_pqc_groups": true,
      "has_classical_groups": false
    }
  }
}
```

**Classical Connection (Dropped):**
```json
{
  "timestamp": "2026-02-09T12:00:01.000000+0000",
  "event_type": "alert",
  "alert": {
    "signature": "Dropping non-PQC TLS connection",
    "signature_id": 1000010,
    "action": "blocked"
  },
  "tls": {
    "pqc_posture": "CLASSICAL"
  }
}
```

## Troubleshooting

### Issue: Legitimate traffic being dropped

**Solution:** Add pass rules for specific systems

```
pass tls any any -> 192.168.1.200 443 (msg:"Allow legacy CRM"; \
    tls.pqc_posture:"CLASSICAL"; sid:1000020;)
```

### Issue: No connections being dropped

**Check:**
1. Configuration loaded: `grep "drop-non-pqc" /var/log/suricata/suricata.log`
2. Flag enabled: Look for `stream.pqc "drop-non-pqc": enabled` in logs
3. PQC detection working: Check for `pqc_posture` in eve.json

### Issue: Performance impact

**Mitigation:**
- PQC detection is lightweight (only during ClientHello)
- Flow marking is minimal overhead
- Consider rule-based approach for selective enforcement

## Testing

### Test with Classical TLS Client

```bash
# Generate classical TLS traffic
openssl s_client -connect example.com:443 -tls1_3 -groups X25519

# Check if dropped
tail -f /var/log/suricata/eve.json | jq 'select(.alert.signature_id==1000010)'
```

### Test with PQC TLS Client

```bash
# Generate PQC TLS traffic (requires PQC-enabled client)
# Example with Chrome Canary or custom client
curl --http3 https://pqc-enabled-server.com

# Verify allowed
tail -f /var/log/suricata/eve.json | jq 'select(.tls.pqc_posture=="PQC_HYBRID")'
```

## Best Practices

1. **Start with Monitoring:** Always begin with alert rules to understand your environment
2. **Document Exceptions:** Keep a list of systems that require classical TLS
3. **Regular Reviews:** Periodically review pass rules and remove as systems upgrade
4. **Gradual Rollout:** Enforce by security zone, not all at once
5. **Monitor Impact:** Track dropped connections and user complaints
6. **Update Regularly:** Keep Suricata updated for latest PQC algorithm support

## Security Considerations

- **Defense in Depth:** PQC enforcement is one layer; use with other security controls
- **Quantum Threat Timeline:** Adjust enforcement based on your threat model
- **Compliance:** Check if your industry has PQC requirements
- **Legacy Systems:** Plan migration path for systems that can't support PQC

## Performance Impact

- **Minimal:** PQC detection occurs only during TLS handshake
- **No Impact on Established Flows:** Only affects new connections
- **Scalable:** Tested with high-throughput environments

## Support

For issues or questions:
- Check Suricata logs: `/var/log/suricata/suricata.log`
- Review PQC detection: Look for `pqc_posture` in eve.json
- Suricata documentation: https://docs.suricata.io/

## Version Compatibility

- Requires: Suricata 9.0.0+ with PQC detection support
- Tested with: TLS 1.3, Kyber/ML-KEM algorithms
- Compatible with: All Suricata run modes (IDS/IPS)