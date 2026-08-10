#!/usr/bin/env python3
"""
Inspect raw Kafka messages to understand the actual data structure
"""

import json
import sys
import os
from pathlib import Path

# Add parent directory to path to import settings
sys.path.insert(0, str(Path(__file__).parent.parent))

from kafka import KafkaConsumer
from kafka.errors import KafkaError
from src.ngfw_pqc_detector.core.config import settings

# Kafka configuration from settings
KAFKA_BOOTSTRAP_SERVERS = settings.KAFKA_BOOTSTRAP_SERVERS
KAFKA_TOPIC = settings.KAFKA_TOPIC_TLS_LOGS
KAFKA_GROUP_ID = "kafka-inspector"


def inspect_messages(max_messages=10):
    """
    Read and inspect raw Kafka messages

    Args:
        max_messages: Maximum number of messages to inspect
    """
    print("=" * 80)
    print("KAFKA MESSAGE INSPECTOR")
    print("=" * 80)
    print(f"Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Topic: {KAFKA_TOPIC}")
    print(f"Group ID: {KAFKA_GROUP_ID}")
    print(f"Max Messages: {max_messages}")
    print("=" * 80)

    try:
        # Create consumer
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
            group_id=KAFKA_GROUP_ID,
            auto_offset_reset="latest",  # Start from latest messages
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=30000,  # 30 second timeout
        )

        print(f"✓ Connected to Kafka broker")
        print(f"✓ Subscribed to topic: '{KAFKA_TOPIC}'")
        print("\nWaiting for messages (30s timeout)...\n")

        message_count = 0
        tls_messages = []
        tcp_messages = []
        flow_messages = []

        for message in consumer:
            message_count += 1
            data = message.value

            print("=" * 80)
            print(f"MESSAGE #{message_count}")
            print("=" * 80)

            # Extract key fields
            event_type = data.get("event_type", "unknown")
            app_proto = data.get("app_proto", "unknown")
            src_ip = data.get("src_ip", "N/A")
            dest_ip = data.get("dest_ip", "N/A")
            dest_port = data.get("dest_port", "N/A")

            print(f"Event Type: {event_type}")
            print(f"App Proto: {app_proto}")
            print(f"Connection: {src_ip} → {dest_ip}:{dest_port}")

            # Check for TLS data and extract SNI
            has_tls_section = "tls" in data
            print(f"Has 'tls' section: {has_tls_section}")

            if has_tls_section:
                tls_data = data.get("tls", {})
                sni = tls_data.get("sni")
                if sni:
                    print(f"SNI (Hostname): {sni}")

            if has_tls_section:
                tls_data = data.get("tls", {})
                print(f"\nTLS Section Keys: {list(tls_data.keys())}")

                # Check for algorithm fields
                has_supported_groups = "supported_groups" in tls_data
                has_key_share = "key_share" in tls_data
                has_signature_algorithms = "signature_algorithms" in tls_data
                has_ja3 = "ja3" in tls_data

                print(f"  - supported_groups: {has_supported_groups}")
                if has_supported_groups:
                    print(f"    Value: {tls_data.get('supported_groups')}")

                print(f"  - key_share: {has_key_share}")
                if has_key_share:
                    print(f"    Value: {tls_data.get('key_share')}")

                print(f"  - signature_algorithms: {has_signature_algorithms}")
                if has_signature_algorithms:
                    print(f"    Value: {tls_data.get('signature_algorithms')}")

                print(f"  - ja3: {has_ja3}")
                if has_ja3:
                    ja3_data = tls_data.get("ja3", {})
                    print(f"    Hash: {ja3_data.get('hash', 'N/A')}")

                tls_messages.append(data)

            # Check flow data
            if "flow" in data:
                flow_data = data.get("flow", {})
                bytes_to_server = flow_data.get("bytes_toserver", 0)
                bytes_to_client = flow_data.get("bytes_toclient", 0)
                total_bytes = bytes_to_server + bytes_to_client
                print(f"\nFlow Data:")
                print(f"  - Bytes to server: {bytes_to_server}")
                print(f"  - Bytes to client: {bytes_to_client}")
                print(f"  - Total bytes: {total_bytes}")

            # Print full message structure
            print(f"\nFull Message Structure:")
            print(json.dumps(data, indent=2))

            # Categorize message
            if event_type == "tls":
                tls_messages.append(data)
            elif event_type == "flow":
                flow_messages.append(data)
            elif app_proto == "tcp":
                tcp_messages.append(data)

            if message_count >= max_messages:
                break

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total messages inspected: {message_count}")
        print(
            f"TLS event_type messages: {len([m for m in tls_messages if m.get('event_type') == 'tls'])}"
        )
        print(f"Flow event_type messages: {len(flow_messages)}")
        print(f"TCP app_proto messages: {len(tcp_messages)}")
        print(
            f"Messages with 'tls' section: {len([m for m in tls_messages + flow_messages if 'tls' in m])}"
        )

        # Analysis
        print("\n" + "=" * 80)
        print("ANALYSIS")
        print("=" * 80)

        messages_with_algorithms = 0
        for msg in tls_messages + flow_messages:
            tls_data = msg.get("tls", {})
            if any(
                k in tls_data for k in ["supported_groups", "key_share", "signature_algorithms"]
            ):
                messages_with_algorithms += 1

        print(f"Messages with algorithm data: {messages_with_algorithms}")

        if messages_with_algorithms == 0:
            print("\n⚠️  WARNING: No messages contain TLS algorithm data!")
            print("   This means Suricata is NOT capturing TLS handshake details.")
            print("   You need to enable extended TLS logging in Suricata configuration.")
        else:
            print(f"\n✓ Found {messages_with_algorithms} messages with algorithm data")

        consumer.close()

    except KafkaError as e:
        print(f"\n❌ Kafka Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inspect Kafka messages for TLS data")
    parser.add_argument(
        "--max-messages",
        type=int,
        default=10,
        help="Maximum number of messages to inspect (default: 10)",
    )
    parser.add_argument(
        "--bootstrap-servers",
        type=str,
        default=None,
        help=f"Kafka bootstrap servers (default: {settings.KAFKA_BOOTSTRAP_SERVERS})",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help=f"Kafka topic to read from (default: {settings.KAFKA_TOPIC_TLS_LOGS})",
    )

    args = parser.parse_args()

    # Override defaults with command line args if provided
    if args.bootstrap_servers:
        KAFKA_BOOTSTRAP_SERVERS = args.bootstrap_servers
    if args.topic:
        KAFKA_TOPIC = args.topic

    inspect_messages(max_messages=args.max_messages)
