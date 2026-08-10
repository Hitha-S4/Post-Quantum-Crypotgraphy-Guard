#!/usr/bin/env python3
"""
Generate PQC TLS ClientHello packets for testing Suricata PQC detection

This script creates binary ClientHello messages with different PQC configurations
that can be replayed or sent to test servers.

Usage:
    python3 generate-pqc-test-traffic.py
    
Output:
    - pqc_hybrid_client_hello.bin
    - pqc_pure_client_hello.bin
    - classical_client_hello.bin
"""

import struct
import os
import sys

def create_pqc_client_hello(hostname, groups, key_share_groups=None):
    """
    Create a TLS 1.3 ClientHello with PQC support
    
    Args:
        hostname: Server hostname for SNI
        groups: List of supported group IDs (e.g., [515, 29] for hybrid)
        key_share_groups: List of groups to include in key_share (optional)
    
    Returns:
        bytes: Complete TLS ClientHello record
    """
    
    # TLS 1.3 ClientHello structure
    client_hello = bytearray()
    
    # TLS Record Header
    client_hello.extend(b'\x16')  # Content Type: Handshake (22)
    client_hello.extend(b'\x03\x01')  # Legacy version: TLS 1.0
    
    # Placeholder for record length (will be filled later)
    record_length_pos = len(client_hello)
    client_hello.extend(b'\x00\x00')
    
    # Handshake Protocol
    client_hello.extend(b'\x01')  # Handshake Type: ClientHello (1)
    
    # Placeholder for handshake length (will be filled later)
    hs_length_pos = len(client_hello)
    client_hello.extend(b'\x00\x00\x00')
    
    # ClientHello Body
    client_hello.extend(b'\x03\x03')  # Client Version: TLS 1.2 (for compatibility)
    
    # Random (32 bytes)
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
    
    # 1. SNI Extension (0x0000)
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
    
    # 2. Supported Groups Extension (0x000a) - CRITICAL FOR PQC DETECTION
    groups_ext = bytearray()
    groups_ext.extend(struct.pack('!H', 0x000a))  # Extension type
    groups_data = bytearray()
    groups_data.extend(struct.pack('!H', len(groups) * 2))
    for group in groups:
        groups_data.extend(struct.pack('!H', group))
    groups_ext.extend(struct.pack('!H', len(groups_data)))
    groups_ext.extend(groups_data)
    extensions.extend(groups_ext)
    
    # 3. Signature Algorithms Extension (0x000d)
    sig_algs_ext = bytearray()
    sig_algs_ext.extend(struct.pack('!H', 0x000d))
    sig_algs = [
        0x0403,  # ecdsa_secp256r1_sha256
        0x0804,  # rsa_pss_rsae_sha256
        0x0401,  # rsa_pkcs1_sha256
    ]
    sig_algs_data = bytearray()
    sig_algs_data.extend(struct.pack('!H', len(sig_algs) * 2))
    for alg in sig_algs:
        sig_algs_data.extend(struct.pack('!H', alg))
    sig_algs_ext.extend(struct.pack('!H', len(sig_algs_data)))
    sig_algs_ext.extend(sig_algs_data)
    extensions.extend(sig_algs_ext)
    
    # 4. Supported Versions Extension (0x002b)
    versions_ext = bytearray()
    versions_ext.extend(struct.pack('!H', 0x002b))
    versions_ext.extend(struct.pack('!H', 3))  # Extension length
    versions_ext.extend(b'\x02')  # Length of versions list
    versions_ext.extend(b'\x03\x04')  # TLS 1.3
    extensions.extend(versions_ext)
    
    # 5. Key Share Extension (0x0033) - IMPORTANT FOR PQC DETECTION
    if key_share_groups:
        keyshare_ext = bytearray()
        keyshare_ext.extend(struct.pack('!H', 0x0033))
        keyshare_data = bytearray()
        
        for group in key_share_groups:
            keyshare_data.extend(struct.pack('!H', group))
            
            # Generate appropriate key exchange data size
            if group in [0x0200, 0x0201, 0x0202]:  # Pure Kyber/ML-KEM
                key_size = 800  # Approximate Kyber public key size
            elif group in [0x0203, 0x0204, 0x0205]:  # Hybrid (Kyber + ECDH)
                key_size = 832  # X25519 (32) + Kyber (800)
            else:  # Classical ECDH
                key_size = 32
            
            keyshare_data.extend(struct.pack('!H', key_size))
            keyshare_data.extend(os.urandom(key_size))
        
        keyshare_ext.extend(struct.pack('!H', len(keyshare_data) + 2))
        keyshare_ext.extend(struct.pack('!H', len(keyshare_data)))
        keyshare_ext.extend(keyshare_data)
        extensions.extend(keyshare_ext)
    
    # Add extensions length and data to ClientHello
    client_hello.extend(struct.pack('!H', len(extensions)))
    client_hello.extend(extensions)
    
    # Fill in the lengths
    # Record length (everything after the record header)
    record_length = len(client_hello) - record_length_pos - 2
    struct.pack_into('!H', client_hello, record_length_pos, record_length)
    
    # Handshake length (everything after the handshake header)
    hs_length = len(client_hello) - hs_length_pos - 3
    client_hello[hs_length_pos:hs_length_pos+3] = struct.pack('!I', hs_length)[1:]
    
    return bytes(client_hello)


def main():
    """Generate test ClientHello messages for different PQC configurations"""
    
    print("=" * 70)
    print("PQC TLS ClientHello Generator")
    print("=" * 70)
    print()
    
    test_cases = [
        {
            "name": "Hybrid PQC (X25519-MLKEM768 + X25519)",
            "filename": "pqc_hybrid_client_hello.bin",
            "groups": [0x0203, 0x001d],  # X25519-MLKEM768, X25519
            "key_share_groups": [0x0203],
            "description": "Should be detected as PQC_HYBRID"
        },
        {
            "name": "Pure PQC (ML-KEM-768 only)",
            "filename": "pqc_pure_client_hello.bin",
            "groups": [0x0201],  # ML-KEM-768
            "key_share_groups": [0x0201],
            "description": "Should be detected as PQC_PURE"
        },
        {
            "name": "Classical Only (X25519 + P-256)",
            "filename": "classical_client_hello.bin",
            "groups": [0x001d, 0x0017],  # X25519, P-256
            "key_share_groups": [0x001d],
            "description": "Should be detected as CLASSICAL"
        },
        {
            "name": "Multiple Hybrid Groups",
            "filename": "pqc_multi_hybrid_client_hello.bin",
            "groups": [0x0203, 0x0204, 0x001d],  # X25519-MLKEM768, X25519-MLKEM1024, X25519
            "key_share_groups": [0x0203],
            "description": "Should be detected as PQC_HYBRID"
        },
        {
            "name": "Pure PQC with Multiple Variants",
            "filename": "pqc_multi_pure_client_hello.bin",
            "groups": [0x0200, 0x0201, 0x0202],  # ML-KEM-512, ML-KEM-768, ML-KEM-1024
            "key_share_groups": [0x0201],
            "description": "Should be detected as PQC_PURE"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] Generating: {test['name']}")
        print(f"    Groups: {[hex(g) for g in test['groups']]}")
        print(f"    Key Share: {[hex(g) for g in test['key_share_groups']]}")
        
        hello = create_pqc_client_hello(
            "example.com",
            groups=test['groups'],
            key_share_groups=test['key_share_groups']
        )
        
        with open(test['filename'], "wb") as f:
            f.write(hello)
        
        print(f"    ✓ Saved {len(hello)} bytes to {test['filename']}")
        print(f"    Expected: {test['description']}")
        print()
    
    print("=" * 70)
    print("Generation Complete!")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("1. Use these files with tcpreplay or similar tools")
    print("2. Run Suricata with: ./src/suricata -c suricata.yaml -r <file>.pcap")
    print("3. Check logs/eve.json for PQC detection results")
    print("4. Use ./view-pqc-events.sh to monitor in real-time")
    print()
    print("Example:")
    print("  # Create a PCAP from the binary ClientHello")
    print("  text2pcap -T 443,443 pqc_hybrid_client_hello.bin pqc_test.pcap")
    print("  # Run Suricata on it")
    print("  ./src/suricata -c suricata.yaml -r pqc_test.pcap -l ./logs")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)