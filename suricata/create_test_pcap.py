#!/usr/bin/env python3
"""Create a simple test PCAP file with ICMP packets"""
import struct
import time

def write_pcap_header(f):
    """Write PCAP global header"""
    magic = 0xa1b2c3d4
    version_major = 2
    version_minor = 4
    thiszone = 0
    sigfigs = 0
    snaplen = 65535
    network = 1  # Ethernet
    
    f.write(struct.pack('<IHHIIII', magic, version_major, version_minor, 
                        thiszone, sigfigs, snaplen, network))

def write_pcap_packet(f, data, timestamp=None):
    """Write a packet to PCAP file"""
    if timestamp is None:
        timestamp = time.time()
    
    ts_sec = int(timestamp)
    ts_usec = int((timestamp - ts_sec) * 1000000)
    incl_len = len(data)
    orig_len = len(data)
    
    f.write(struct.pack('<IIII', ts_sec, ts_usec, incl_len, orig_len))
    f.write(data)

def create_icmp_packet():
    """Create a simple ICMP echo request packet"""
    # Ethernet header (14 bytes)
    dst_mac = b'\xff\xff\xff\xff\xff\xff'  # Broadcast
    src_mac = b'\x00\x11\x22\x33\x44\x55'
    eth_type = b'\x08\x00'  # IPv4
    eth_header = dst_mac + src_mac + eth_type
    
    # IP header (20 bytes)
    version_ihl = 0x45  # IPv4, 20 bytes header
    tos = 0
    total_length = 84  # 20 (IP) + 64 (ICMP)
    identification = 0x1234
    flags_fragment = 0
    ttl = 64
    protocol = 1  # ICMP
    checksum = 0  # Will be calculated
    src_ip = b'\xc0\xa8\x01\x64'  # 192.168.1.100
    dst_ip = b'\xc0\xa8\x01\x01'  # 192.168.1.1
    
    ip_header = struct.pack('>BBHHHBBH4s4s',
                           version_ihl, tos, total_length, identification,
                           flags_fragment, ttl, protocol, checksum,
                           src_ip, dst_ip)
    
    # Calculate IP checksum
    checksum = 0
    for i in range(0, len(ip_header), 2):
        word = (ip_header[i] << 8) + ip_header[i+1]
        checksum += word
    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum = ~checksum & 0xffff
    
    ip_header = struct.pack('>BBHHHBBH4s4s',
                           version_ihl, tos, total_length, identification,
                           flags_fragment, ttl, protocol, checksum,
                           src_ip, dst_ip)
    
    # ICMP header (8 bytes) + data (56 bytes)
    icmp_type = 8  # Echo request
    icmp_code = 0
    icmp_checksum = 0
    icmp_id = 0x1234
    icmp_seq = 1
    icmp_data = b'Test ICMP packet data for Suricata' + b'\x00' * 22
    
    icmp_packet = struct.pack('>BBHHH', icmp_type, icmp_code, icmp_checksum,
                             icmp_id, icmp_seq) + icmp_data
    
    # Calculate ICMP checksum
    checksum = 0
    for i in range(0, len(icmp_packet), 2):
        word = (icmp_packet[i] << 8) + (icmp_packet[i+1] if i+1 < len(icmp_packet) else 0)
        checksum += word
    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum = ~checksum & 0xffff
    
    icmp_packet = struct.pack('>BBHHH', icmp_type, icmp_code, checksum,
                             icmp_id, icmp_seq) + icmp_data
    
    return eth_header + ip_header + icmp_packet

# Create PCAP file
with open('capture.pcap', 'wb') as f:
    write_pcap_header(f)
    
    # Write 5 ICMP packets
    base_time = time.time()
    for i in range(5):
        packet = create_icmp_packet()
        write_pcap_packet(f, packet, base_time + i * 0.1)

print("Created capture.pcap with 5 ICMP packets")
