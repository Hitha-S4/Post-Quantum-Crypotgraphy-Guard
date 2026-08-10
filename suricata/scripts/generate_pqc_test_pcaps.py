#!/usr/bin/env python3
"""
Generate synthetic TLS ClientHello packets with PQC extensions for testing.

This script creates PCAP files with various PQC configurations:
- Pure PQC (Kyber only)
- Hybrid PQC (Kyber + x25519)
- Classical only (x25519, P-256)
- ECH protected

Usage:
    python3 scripts/generate_pqc_test_pcaps.py
"""

import struct
import os
from datetime import datetime

# TLS Constants
TLS_CONTENT_TYPE_HANDSHAKE = 0x16
TLS_VERSION_1_2 = 0x0303
TLS_HANDSHAKE_CLIENT_HELLO = 0x01

# TLS Extension Types
TLS_EXT_SERVER_NAME = 0x0000
TLS_EXT_SUPPORTED_GROUPS = 0x000a
TLS_EXT_SIGNATURE_ALGORITHMS = 0x000d
TLS_EXT_ALPN = 0x0010
TLS_EXT_SUPPORTED_VERSIONS = 0x002b
TLS_EXT_KEY_SHARE = 0x0033
TLS_EXT_ECH = 0xfe0d

# Named Groups
NAMED_GROUP_X25519 = 0x001d
NAMED_GROUP_SECP256R1 = 0x0017
NAMED_GROUP_MLKEM512 = 0x0200
NAMED_GROUP_MLKEM768 = 0x0201
NAMED_GROUP_MLKEM1024 = 0x0202
NAMED_GROUP_X25519_MLKEM768 = 0x0203
NAMED_GROUP_X25519_MLKEM1024 = 0x0204


def create_pcap_header():
    """Create PCAP file header."""
    return struct.pack('<IHHIIII',
        0xa1b2c3d4,  # Magic number
        2,           # Major version
        4,           # Minor version
        0,           # Timezone offset
        0,           # Timestamp accuracy
        65535,       # Snaplen
        1            # Network (Ethernet)
    )


def create_pcap_packet_header(packet_len):
    """Create PCAP packet header."""
    ts = int(datetime.now().timestamp())
    return struct.pack('<IIII',
        ts,          # Timestamp seconds
        0,           # Timestamp microseconds
        packet_len,  # Captured length
        packet_len   # Original length
    )


def create_ethernet_header(src_mac, dst_mac):
    """Create Ethernet header."""
    return (
        bytes.fromhex(dst_mac.replace(':', '')) +
        bytes.fromhex(src_mac.replace(':', '')) +
        struct.pack('>H', 0x0800)  # IPv4
    )


def create_ip_header(src_ip, dst_ip, payload_len):
    """Create IPv4 header."""
    total_len = 20 + 20 + payload_len  # IP + TCP + payload
    src_bytes = bytes([int(x) for x in src_ip.split('.')])
    dst_bytes = bytes([int(x) for x in dst_ip.split('.')])
    return struct.pack('>BBHHHBBH',
        0x45,        # Version + IHL
        0,           # TOS
        total_len,   # Total length
        0x1234,      # ID
        0x4000,      # Flags + Fragment offset
        64,          # TTL
        6,           # Protocol (TCP)
        0            # Checksum (0 for now)
    ) + src_bytes + dst_bytes


def create_tcp_header(src_port, dst_port, seq, ack, flags):
    """Create TCP header."""
    return struct.pack('>HHIIBBHHH',
        src_port,    # Source port
        dst_port,    # Destination port
        seq,         # Sequence number
        ack,         # Acknowledgment number
        0x50,        # Data offset (5 words)
        flags,       # Flags
        8192,        # Window size
        0,           # Checksum (0 for now)
        0            # Urgent pointer
    )


def create_tls_extension(ext_type, data):
    """Create a TLS extension."""
    return struct.pack('>HH', ext_type, len(data)) + data


def create_supported_groups_ext(groups):
    """Create Supported Groups extension."""
    groups_data = b''.join(struct.pack('>H', g) for g in groups)
    return create_tls_extension(
        TLS_EXT_SUPPORTED_GROUPS,
        struct.pack('>H', len(groups_data)) + groups_data
    )


def create_key_share_ext(groups):
    """Create Key Share extension with dummy key data."""
    key_shares = b''
    for group in groups:
        # Generate dummy key data (32 bytes for x25519, larger for Kyber)
        if group in [NAMED_GROUP_MLKEM768, NAMED_GROUP_X25519_MLKEM768]:
            key_len = 1184  # Kyber768 public key size
        elif group == NAMED_GROUP_MLKEM1024:
            key_len = 1568  # Kyber1024 public key size
        else:
            key_len = 32    # x25519 key size
        
        key_data = b'\x00' * key_len
        key_shares += struct.pack('>HH', group, key_len) + key_data
    
    return create_tls_extension(
        TLS_EXT_KEY_SHARE,
        struct.pack('>H', len(key_shares)) + key_shares
    )


def create_client_hello(sni, supported_groups, key_share_groups=None, include_ech=False):
    """Create TLS ClientHello message."""
    # Random (32 bytes)
    random = b'\x00' * 32
    
    # Session ID (empty)
    session_id = b'\x00'
    
    # Cipher suites (TLS 1.3 suites)
    cipher_suites = struct.pack('>H', 4) + struct.pack('>HH', 0x1301, 0x1302)
    
    # Compression methods
    compression = b'\x01\x00'
    
    # Extensions
    extensions = b''
    
    # Server Name Indication
    if sni:
        sni_data = struct.pack('>BH', 0, len(sni)) + sni.encode()
        sni_list = struct.pack('>H', len(sni_data)) + sni_data
        extensions += create_tls_extension(TLS_EXT_SERVER_NAME, sni_list)
    
    # Supported Groups
    extensions += create_supported_groups_ext(supported_groups)
    
    # Key Share (if specified)
    if key_share_groups:
        extensions += create_key_share_ext(key_share_groups)
    
    # Supported Versions (TLS 1.3)
    versions = struct.pack('>BH', 2, 0x0304)
    extensions += create_tls_extension(TLS_EXT_SUPPORTED_VERSIONS, versions)
    
    # ECH (if requested)
    if include_ech:
        ech_data = b'\x00' * 100  # Dummy ECH data
        extensions += create_tls_extension(TLS_EXT_ECH, ech_data)
    
    # Build ClientHello
    client_hello = (
        struct.pack('>H', TLS_VERSION_1_2) +
        random +
        session_id +
        cipher_suites +
        compression +
        struct.pack('>H', len(extensions)) +
        extensions
    )
    
    # Wrap in Handshake message
    handshake = (
        struct.pack('>B', TLS_HANDSHAKE_CLIENT_HELLO) +
        struct.pack('>I', len(client_hello))[1:] +  # 3-byte length
        client_hello
    )
    
    # Wrap in TLS Record
    tls_record = (
        struct.pack('>BHH', TLS_CONTENT_TYPE_HANDSHAKE, TLS_VERSION_1_2, len(handshake)) +
        handshake
    )
    
    return tls_record


def create_test_packet(scenario_name, sni, supported_groups, key_share_groups=None, include_ech=False):
    """Create a complete test packet."""
    # Create TLS ClientHello
    tls_data = create_client_hello(sni, supported_groups, key_share_groups, include_ech)
    
    # Create headers
    tcp = create_tcp_header(54321, 443, 1000, 0, 0x02)  # SYN flag
    ip = create_ip_header('192.168.1.100', '93.184.216.34', len(tcp) + len(tls_data))
    eth = create_ethernet_header('00:11:22:33:44:55', 'aa:bb:cc:dd:ee:ff')
    
    # Combine packet
    packet = eth + ip + tcp + tls_data
    
    return packet


def generate_test_pcaps():
    """Generate all test PCAP files."""
    output_dir = 'test/pcaps'
    os.makedirs(output_dir, exist_ok=True)
    
    scenarios = [
        {
            'name': 'pqc_pure',
            'description': 'Pure PQC (Kyber only)',
            'sni': 'pqc-pure.example.com',
            'supported_groups': [NAMED_GROUP_MLKEM768, NAMED_GROUP_MLKEM1024],
            'key_share_groups': [NAMED_GROUP_MLKEM768],
            'include_ech': False
        },
        {
            'name': 'pqc_hybrid',
            'description': 'Hybrid PQC (Kyber + x25519)',
            'sni': 'pqc-hybrid.example.com',
            'supported_groups': [NAMED_GROUP_X25519_MLKEM768, NAMED_GROUP_X25519],
            'key_share_groups': [NAMED_GROUP_X25519_MLKEM768],
            'include_ech': False
        },
        {
            'name': 'classical',
            'description': 'Classical only (x25519, P-256)',
            'sni': 'classical.example.com',
            'supported_groups': [NAMED_GROUP_X25519, NAMED_GROUP_SECP256R1],
            'key_share_groups': [NAMED_GROUP_X25519],
            'include_ech': False
        },
        {
            'name': 'ech_protected',
            'description': 'ECH protected',
            'sni': 'ech.example.com',
            'supported_groups': [NAMED_GROUP_X25519],
            'key_share_groups': [NAMED_GROUP_X25519],
            'include_ech': True
        },
        {
            'name': 'mixed_groups',
            'description': 'Mixed groups (all types)',
            'sni': 'mixed.example.com',
            'supported_groups': [
                NAMED_GROUP_X25519_MLKEM768,
                NAMED_GROUP_MLKEM768,
                NAMED_GROUP_X25519,
                NAMED_GROUP_SECP256R1
            ],
            'key_share_groups': [NAMED_GROUP_X25519_MLKEM768],
            'include_ech': False
        }
    ]
    
    for scenario in scenarios:
        filename = f"{output_dir}/{scenario['name']}.pcap"
        print(f"Generating {filename} - {scenario['description']}")
        
        with open(filename, 'wb') as f:
            # Write PCAP header
            f.write(create_pcap_header())
            
            # Create and write packet
            packet = create_test_packet(
                scenario['name'],
                scenario['sni'],
                scenario['supported_groups'],
                scenario.get('key_share_groups'),
                scenario.get('include_ech', False)
            )
            
            f.write(create_pcap_packet_header(len(packet)))
            f.write(packet)
        
        print(f"  ✓ Created {filename} ({len(packet)} bytes)")
    
    print(f"\n✓ Generated {len(scenarios)} test PCAP files in {output_dir}/")
    print("\nTest with:")
    print(f"  ./src/suricata -c suricata.yaml -r {output_dir}/pqc_hybrid.pcap -l ./log")


if __name__ == '__main__':
    print("=== PQC TLS Test PCAP Generator ===\n")
    generate_test_pcaps()
    print("\nDone!")