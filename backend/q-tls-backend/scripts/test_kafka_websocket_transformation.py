#!/usr/bin/env python3
"""
Test script to monitor Kafka messages and their transformed WebSocket payloads
Shows side-by-side comparison of incoming Kafka messages and outgoing WebSocket data
"""
import asyncio
import json
import sys
from datetime import datetime
from kafka import KafkaConsumer
import websockets
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "suricata-events"
KAFKA_GROUP_ID = "test-monitor-group"
WEBSOCKET_URL = "ws://localhost:8000/ws/batch-updates"
LOG_FILE = "kafka_websocket_monitor.json"


class MessageMonitor:
    """Monitor and display Kafka messages and WebSocket transformations"""

    def __init__(self, log_file=LOG_FILE):
        self.kafka_messages = {}
        self.websocket_messages = {}
        self.message_count = 0
        self.log_file = log_file
        self.log_entries = []

    def print_separator(self, char="=", length=100):
        """Print a separator line"""
        print(Fore.CYAN + char * length)

    def print_header(self, text):
        """Print a header"""
        self.print_separator()
        print(Fore.YELLOW + Style.BRIGHT + f"  {text}")
        self.print_separator()

    def save_to_log(self):
        """Save all collected messages to JSON log file"""
        try:
            with open(self.log_file, "w") as f:
                json.dump(
                    {
                        "total_messages": self.message_count,
                        "timestamp": datetime.now().isoformat(),
                        "entries": self.log_entries,
                    },
                    f,
                    indent=2,
                )
            print(Fore.GREEN + f"\n✓ Logs saved to {self.log_file}")
        except Exception as e:
            print(Fore.RED + f"\n❌ Failed to save logs: {e}")

    def print_kafka_message(self, message):
        """Print formatted Kafka message"""
        self.print_header(f"📨 INCOMING KAFKA MESSAGE #{self.message_count}")

        # Extract key fields
        timestamp = message.get("timestamp", "N/A")
        event_type = message.get("event_type", "unknown")
        src_ip = message.get("src_ip", "N/A")
        src_port = message.get("src_port", "N/A")
        dest_ip = message.get("dest_ip", "N/A")
        dest_port = message.get("dest_port", "N/A")
        app_proto = message.get("app_proto", "unknown")
        flow_id = message.get("flow_id", "N/A")

        # Flow data
        flow = message.get("flow", {})
        bytes_to_server = flow.get("bytes_toserver", 0)
        bytes_to_client = flow.get("bytes_toclient", 0)
        total_bytes = bytes_to_server + bytes_to_client

        print(Fore.WHITE + f"  Timestamp:    {timestamp}")
        print(Fore.WHITE + f"  Flow ID:      {flow_id}")
        print(Fore.WHITE + f"  Event Type:   {event_type}")
        print(Fore.WHITE + f"  Protocol:     {app_proto.upper()}")
        print(Fore.WHITE + f"  Connection:   {src_ip}:{src_port} → {dest_ip}:{dest_port}")
        print(
            Fore.WHITE
            + f"  Bytes:        {bytes_to_server} → server, {bytes_to_client} ← client (total: {total_bytes})"
        )

        # TLS data if available
        if "tls" in message:
            tls = message["tls"]
            print(Fore.MAGENTA + f"  TLS Version:  {tls.get('version', 'N/A')}")
            print(Fore.MAGENTA + f"  SNI:          {tls.get('sni', 'N/A')}")
            print(Fore.MAGENTA + f"  Cipher:       {tls.get('cipher_suite_name', 'N/A')}")

        print(Fore.GREEN + "\n  Raw Kafka Message:")
        print(Fore.GREEN + "  " + json.dumps(message, indent=2).replace("\n", "\n  "))

    def print_websocket_payload(self, payload):
        """Print formatted WebSocket payload"""
        print("\n")
        self.print_header(f"🔄 TRANSFORMED WEBSOCKET PAYLOAD #{self.message_count}")

        data = payload.get("data", {})
        pqc = data.get("pqc_detection", {})

        # Connection info
        print(Fore.WHITE + f"  Timestamp:    {payload.get('timestamp', 'N/A')}")
        print(Fore.WHITE + f"  Flow ID:      {data.get('flow_id', 'N/A')}")
        print(Fore.WHITE + f"  Protocol:     {data.get('app_proto', 'unknown').upper()}")
        print(
            Fore.WHITE
            + f"  Connection:   {data.get('src_ip')}:{data.get('src_port')} → {data.get('dest_ip')}:{data.get('dest_port')}"
        )

        # Flow info
        flow = data.get("flow", {})
        print(
            Fore.WHITE
            + f"  Bytes:        {flow.get('bytes_toserver', 0)} → server, {flow.get('bytes_toclient', 0)} ← client (total: {flow.get('total_bytes', 0)})"
        )

        # PQC Detection Results
        status = pqc.get("status", "unknown")
        crypto_type = pqc.get("crypto_type", "unknown")
        confidence = pqc.get("confidence", 0.0)
        is_safe = pqc.get("is_pqc_safe", False)

        status_icon = "🔐" if is_safe else "🔓" if status == "vulnerable" else "❓"
        status_color = (
            Fore.GREEN if is_safe else Fore.RED if status == "vulnerable" else Fore.YELLOW
        )

        print(status_color + Style.BRIGHT + f"\n  {status_icon} PQC DETECTION RESULTS:")
        print(status_color + f"    Status:           {status.upper()}")
        print(status_color + f"    Crypto Type:      {crypto_type.upper()}")
        print(status_color + f"    Confidence:       {confidence:.2%}")
        print(status_color + f"    Detection Method: {pqc.get('detection_method', 'N/A')}")
        print(status_color + f"    Is PQC Safe:      {is_safe}")

        # TLS info if available
        if "tls" in data:
            tls = data["tls"]
            print(Fore.MAGENTA + f"\n  TLS Information:")
            print(Fore.MAGENTA + f"    Version:      {tls.get('version', 'N/A')}")
            print(Fore.MAGENTA + f"    SNI:          {tls.get('sni', 'N/A')}")
            print(Fore.MAGENTA + f"    Cipher Suite: {tls.get('cipher_suite', 'N/A')}")

        print(Fore.CYAN + "\n  Complete WebSocket Payload:")
        print(Fore.CYAN + "  " + json.dumps(payload, indent=2).replace("\n", "\n  "))

        self.print_separator()
        print("\n")


async def monitor_kafka(monitor: MessageMonitor):
    """Monitor Kafka messages"""
    print(Fore.YELLOW + "🔌 Connecting to Kafka...")

    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        print(Fore.GREEN + f"✓ Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        print(Fore.GREEN + f"✓ Subscribed to topic: {KAFKA_TOPIC}")
        print(Fore.GREEN + f"✓ Waiting for messages...\n")

        for message in consumer:
            monitor.message_count += 1
            kafka_msg = message.value

            # Store with flow_id as key
            flow_id = kafka_msg.get("flow_id", monitor.message_count)
            monitor.kafka_messages[flow_id] = kafka_msg

            # Log entry for this message
            log_entry = {
                "message_number": monitor.message_count,
                "timestamp": datetime.now().isoformat(),
                "flow_id": flow_id,
                "kafka_message": kafka_msg,
                "websocket_message": None,  # Will be updated when WebSocket message arrives
            }
            monitor.log_entries.append(log_entry)

            # Print Kafka message
            monitor.print_kafka_message(kafka_msg)

            # Wait a bit for WebSocket message
            await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\n⚠️  Kafka monitoring stopped by user")
        monitor.save_to_log()
    except Exception as e:
        print(Fore.RED + f"\n❌ Kafka error: {e}")
        monitor.save_to_log()


async def monitor_websocket(monitor: MessageMonitor):
    """Monitor WebSocket messages"""
    print(Fore.YELLOW + "🔌 Connecting to WebSocket...")

    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                print(Fore.GREEN + f"✓ Connected to WebSocket: {WEBSOCKET_URL}")
                print(Fore.GREEN + f"✓ Listening for transformed messages...\n")

                retry_count = 0  # Reset on successful connection

                async for message in websocket:
                    try:
                        ws_msg = json.loads(message)

                        # Only process kafka_message types
                        if ws_msg.get("type") == "kafka_message":
                            data = ws_msg.get("data", {})
                            flow_id = data.get("flow_id", monitor.message_count)

                            # Store WebSocket message
                            monitor.websocket_messages[flow_id] = ws_msg

                            # Update log entry with WebSocket message
                            for entry in monitor.log_entries:
                                if (
                                    entry["flow_id"] == flow_id
                                    and entry["websocket_message"] is None
                                ):
                                    entry["websocket_message"] = ws_msg
                                    break

                            # Print WebSocket payload
                            monitor.print_websocket_payload(ws_msg)

                    except json.JSONDecodeError as e:
                        print(Fore.RED + f"❌ Failed to parse WebSocket message: {e}")
                    except Exception as e:
                        print(Fore.RED + f"❌ Error processing WebSocket message: {e}")

        except websockets.exceptions.ConnectionClosed:
            retry_count += 1
            print(
                Fore.YELLOW
                + f"⚠️  WebSocket connection closed. Retrying ({retry_count}/{max_retries})..."
            )
            await asyncio.sleep(2)

        except Exception as e:
            retry_count += 1
            print(Fore.RED + f"❌ WebSocket error: {e}")
            if retry_count < max_retries:
                print(Fore.YELLOW + f"⚠️  Retrying in 2 seconds ({retry_count}/{max_retries})...")
                await asyncio.sleep(2)
            else:
                print(Fore.RED + f"❌ Max retries reached. Exiting WebSocket monitor.")
                monitor.save_to_log()
                break


async def main():
    """Main function to run both monitors"""
    print(
        Fore.CYAN
        + Style.BRIGHT
        + """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║           Kafka → WebSocket Transformation Monitor                           ║
║                                                                               ║
║  This script monitors incoming Kafka messages and their transformed          ║
║  WebSocket payloads with PQC detection results                               ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    )

    monitor = MessageMonitor()

    # Run both monitors concurrently
    try:
        await asyncio.gather(monitor_websocket(monitor), monitor_kafka(monitor))
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\n⚠️  Monitoring stopped by user")
        print(Fore.CYAN + f"\n📊 Total messages processed: {monitor.message_count}")
        monitor.save_to_log()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\n👋 Goodbye!")
        print(Fore.GREEN + f"📁 Check {LOG_FILE} for saved logs")
        sys.exit(0)
