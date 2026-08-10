#!/usr/bin/env python3
"""
PQC TLS Test Traffic Generator

This script generates test TLS ClientHello packets with various PQC configurations
to test Suricata's PQC detection capabilities.
"""

import socket
import struct
import sys
from typing import List, Tuple

# TLS Constants
TLS_CONTENT_TYPE_HANDSHAKE = 0x16
TLS_VERSION_1_2 = 0x0303
TLS_VERSION_1_3 = 0x0303  # TLS 1.3 uses 1.2 in record layer
TLS_HANDSHAKE_CLIENT_HELLO = 0x01

# TLS Extension Types
TLS_EXT_SERVER_NAME = 0x0000
TLS_EXT_SUPPORTED_GROUPS = 0x000a
TLS_EXT_SIGNATURE_ALGORITHMS = 0x000d
TLS_EXT_ALPN = 0x0010
TLS_EXT_SUPPORTED_VERSIONS = 0x002b
TLS_EXT_KEY_SHARE = 0x0033
TLS_EXT_ENCRYPTED_CLIENT_HELLO = 0xfe0d

# Named Groups
NAMED_GROUP_X25519 = 0x001d
NAMED_GROUP_SECP256R1 = 0x0017
NAMED_GROUP_SECP384R1 = 0x0018
NAMED_GROUP_SECP521R1 = 0x0019

# PQC Groups (IETF draft values)
NAMED_GROUP_MLKEM512 = 0x0200
NAMED_GROUP_MLKEM768 = 0x0201
NAMED_GROUP_MLKEM1024 = 0x0202
NAMED_GROUP_X25519_MLKEM768 = 0x0203
NAMED_GROUP_X25519_MLKEM1024 = 0x0204
NAMED_GROUP_SECP256R1_MLKEM768 = 0x0205


class TLSClientHelloBuilder:
    """Build TLS ClientHello packets with PQC support"""
    
    def __init__(self, sni: str = "test.example.com"):
        self.sni = sni
        self.supported_groups: List[int] = []
        self.key_share_groups: List[int] = []
        self.include_ech = False
        
    def add_supported_groups(self, groups: List[int]):
        """Add supported groups (Supported Groups extension)"""
        self.supported_groups.extend(groups)
        return self
        
    def add_key_shares(self, groups: List[int]):
        """Add key share groups (Key Share extension)"""
        self.key_share_groups.extend(groups)
        return self
        
    def enable_ech(self):
        """Enable Encrypted Client Hello"""
        self.include_ech = True
        return self
        
    def _build_extension(self, ext_type: int, data: bytes) -> bytes:
        """Build a TLS extension"""
        return struct.pack("!HH", ext_type, len(data)) + data
        
    def _build_sni_extension(self) -> bytes:
        """Build Server Name Indication extension"""
        sni_bytes = self.sni.encode('utf-8')
        # Server Name List Length (2) + Name Type (1) + Name Length (2) + Name
        sni_data = struct.pack("!HBH", len(sni_bytes) + 3, 0, len(sni_bytes)) + sni_bytes
        return self._build_extension(TLS_EXT_SERVER_NAME, sni_data)
        
    def _build_supported_groups_extension(self) -> bytes:
        """Build Supported Groups extension"""
        if not self.supported_groups:
            return b''
        groups_data = b''.join(struct.pack("!H", g) for g in self.supported_groups)
        data = struct.pack("!H", len(groups_data)) + groups_data
        return self._build_extension(TLS_EXT_SUPPORTED_GROUPS, data)
        
    def _build_key_share_extension(self) -> bytes:
        """Build Key Share extension with dummy key material"""
        if not self.key_share_groups:
            return b''
            
        shares = b''
        for group in self.key_share_groups:
            # Generate dummy key exchange data (32 bytes for X25519, larger for PQC)
            if group in [NAMED_GROUP_MLKEM768, NAMED_GROUP_X25519_MLKEM768]:
                key_len = 1184  # ML-KEM-768 public key size
            elif group in [NAMED_GROUP_MLKEM1024, NAMED_GROUP_X25519_MLKEM1024]:
                key_len = 1568  # ML-KEM-1024 public key size
            elif group == NAMED_GROUP_MLKEM512:
                key_len = 800   # ML-KEM-512 public key size
            else:
                key_len = 32    # X25519/P-256 size
                
            key_data = b'\x00' * key_len
            shares += struct.pack("!HH", group, key_len) + key_data
            
        data = struct.pack("!H", len(shares)) + shares
        return self._build_extension(TLS_EXT_KEY_SHARE, data)
        
    def _build_ech_extension(self) -> bytes:
        """Build Encrypted Client Hello extension (dummy)"""
        if not self.include_ech:
            return b''
        # Dummy ECH data
        ech_data = b'\x00' * 32
        return self._build_extension(TLS_EXT_ENCRYPTED_CLIENT_HELLO, ech_data)
        
    def _build_supported_versions_extension(self) -> bytes:
        """Build Supported Versions extension for TLS 1.3"""
        # Support TLS 1.3 (0x0304) and TLS 1.2 (0x0303)
        versions = struct.pack("!HH", 0x0304, 0x0303)
        data = struct.pack("!B", len(versions)) + versions
        return self._build_extension(TLS_EXT_SUPPORTED_VERSIONS, data)
        
    def _build_alpn_extension(self) -> bytes:
        """Build ALPN extension"""
        alpn_list = b'\x02h2\x08http/1.1'  # h2, http/1.1
        data = struct.pack("!H", len(alpn_list)) + alpn_list
        return self._build_extension(TLS_EXT_ALPN, data)
        
    def build(self) -> bytes:
        """Build complete TLS ClientHello packet"""
        # Random (32 bytes)
        random = b'\x00' * 32
        
        # Session ID (empty)
        session_id = b'\x00'
        
        # Cipher Suites (TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384)
        cipher_suites = struct.pack("!HHH", 4, 0x1301, 0x1302)
        
        # Compression Methods (null)
        compression = b'\x01\x00'
        
        # Build extensions
        extensions = b''
        extensions += self._build_sni_extension()
        extensions += self._build_supported_groups_extension()
        extensions += self._build_key_share_extension()
        extensions += self._build_ech_extension()
        extensions += self._build_supported_versions_extension()
        extensions += self._build_alpn_extension()
        
        extensions_data = struct.pack("!H", len(extensions)) + extensions
        
        # Build ClientHello
        client_hello = (
            struct.pack("!H", TLS_VERSION_1_2) +
            random +
            session_id +
            cipher_suites +
            compression +
            extensions_data
        )
        
        # Handshake header
        handshake = (
            struct.pack("!B", TLS_HANDSHAKE_CLIENT_HELLO) +
            struct.pack("!I", len(client_hello))[1:] +  # 3-byte length
            client_hello
        )
        
        # TLS Record header
        record = (
            struct.pack("!BHH", TLS_CONTENT_TYPE_HANDSHAKE, TLS_VERSION_1_2, len(handshake)) +
            handshake
        )
        
        return record


def send_test_packet(host: str, port: int, packet: bytes, description: str):
    """Send a test packet to the target"""
    print(f"\n{'='*70}")
    print(f"Test: {description}")
    print(f"Target: {host}:{port}")
    print(f"Packet size: {len(packet)} bytes")
    print(f"{'='*70}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.send(packet)
        
        # Try to receive response (will likely fail/timeout for test packets)
        try:
            response = sock.recv(1024)
            print(f"✓ Received {len(response)} bytes response")
        except socket.timeout:
            print("✓ Packet sent (no response expected for test)")
            
        sock.close()
        print("✓ Test completed")
        
    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    """Run PQC TLS tests"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           PQC TLS Test Traffic Generator                         ║
║                                                                  ║
║  This script generates test TLS ClientHello packets with        ║
║  various PQC configurations to test Suricata's detection.       ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Default test target (use a real server or local test server)
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4433
    
    print(f"Target: {host}:{port}")
    print(f"\nNote: These are test packets. Use a test server or monitor with Suricata.")
    print(f"      Real servers may reject malformed packets.\n")
    
    # Test 1: Classical only (x25519)
    print("\n" + "="*70)
    print("TEST 1: CLASSICAL - X25519 only")
    print("="*70)
    builder = TLSClientHelloBuilder("classical.test.com")
    builder.add_supported_groups([NAMED_GROUP_X25519, NAMED_GROUP_SECP256R1])
    builder.add_key_shares([NAMED_GROUP_X25519])
    packet = builder.build()
    send_test_packet(host, port, packet, "Classical X25519")
    
    # Test 2: Pure PQC (ML-KEM-768)
    print("\n" + "="*70)
    print("TEST 2: PQC_PURE - ML-KEM-768 only")
    print("="*70)
    builder = TLSClientHelloBuilder("pqc-pure.test.com")
    builder.add_supported_groups([NAMED_GROUP_MLKEM768])
    builder.add_key_shares([NAMED_GROUP_MLKEM768])
    packet = builder.build()
    send_test_packet(host, port, packet, "Pure PQC ML-KEM-768")
    
    # Test 3: Hybrid PQC (X25519+ML-KEM-768)
    print("\n" + "="*70)
    print("TEST 3: PQC_HYBRID - X25519+ML-KEM-768")
    print("="*70)
    builder = TLSClientHelloBuilder("pqc-hybrid.test.com")
    builder.add_supported_groups([NAMED_GROUP_X25519_MLKEM768, NAMED_GROUP_X25519])
    builder.add_key_shares([NAMED_GROUP_X25519_MLKEM768])
    packet = builder.build()
    send_test_packet(host, port, packet, "Hybrid X25519+ML-KEM-768")
    
    # Test 4: ECH Protected
    print("\n" + "="*70)
    print("TEST 4: ECH_PROTECTED - With Encrypted Client Hello")
    print("="*70)
    builder = TLSClientHelloBuilder("ech.test.com")
    builder.add_supported_groups([NAMED_GROUP_X25519])
    builder.add_key_shares([NAMED_GROUP_X25519])
    builder.enable_ech()
    packet = builder.build()
    send_test_packet(host, port, packet, "ECH Protected")
    
    # Test 5: Mixed (Hybrid + Classical)
    print("\n" + "="*70)
    print("TEST 5: PQC_HYBRID - Multiple hybrid groups")
    print("="*70)
    builder = TLSClientHelloBuilder("mixed.test.com")
    builder.add_supported_groups([
        NAMED_GROUP_X25519_MLKEM768,
        NAMED_GROUP_SECP256R1_MLKEM768,
        NAMED_GROUP_X25519,
        NAMED_GROUP_SECP256R1
    ])
    builder.add_key_shares([NAMED_GROUP_X25519_MLKEM768])
    packet = builder.build()
    send_test_packet(host, port, packet, "Mixed Hybrid Groups")
    
    print("\n" + "="*70)
    print("All tests completed!")
    print("="*70)
    print("\nCheck Suricata logs:")
    print("  tail -f /usr/local/var/log/suricata/eve.json | jq 'select(.event_type==\"tls\") | .tls.pqc'")
    print()


if __name__ == "__main__":
    main()