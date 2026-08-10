#!/usr/bin/env python3
"""
Test client for Kafka stream WebSocket endpoint
Connects to ws://localhost:8000/ws/kafka-stream and displays real-time Kafka messages
"""
import asyncio
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Error: websockets library not installed")
    print("Install it with: pip install websockets")
    sys.exit(1)


async def test_kafka_stream():
    """Connect to Kafka stream WebSocket and display messages"""
    uri = "ws://localhost:8000/ws/kafka-stream"
    
    print("=" * 80)
    print("  KAFKA STREAM WEBSOCKET TEST CLIENT")
    print("=" * 80)
    print(f"\nConnecting to: {uri}")
    print("Press Ctrl+C to stop\n")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected successfully!")
            print("-" * 80)
            
            message_count = 0
            
            while True:
                try:
                    # Receive message from server
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    message_count += 1
                    print(data)
                    # Display message based on type
                    if data.get('type') == 'connected':
                        print(f"\n[{data.get('timestamp')}] {data.get('message')}")
                        print("-" * 80)
                    
                    elif data.get('type') == 'kafka_message':
                        print(f"\n[Message #{message_count}] Received at: {data.get('timestamp')}")
                        
                        # Extract key information from Kafka message
                        kafka_data = data.get('data', {})
                        
                        # Display connection info
                        src_ip = kafka_data.get('src_ip', 'N/A')
                        src_port = kafka_data.get('src_port', 'N/A')
                        dest_ip = kafka_data.get('dest_ip', 'N/A')
                        dest_port = kafka_data.get('dest_port', 'N/A')
                        
                        print(f"  Connection: {src_ip}:{src_port} → {dest_ip}:{dest_port}")
                        
                        # Display TLS info if available
                        tls_data = kafka_data.get('tls', {})
                        if tls_data:
                            print(f"  TLS Version: {tls_data.get('version', 'N/A')}")
                            print(f"  SNI: {tls_data.get('sni', 'N/A')}")
                            print(f"  Cipher Suite: {tls_data.get('cipher_suite_name', 'N/A')}")
                        
                        # Display full message in compact JSON
                        print(f"  Raw Data: {json.dumps(kafka_data, indent=2)[:200]}...")
                        print("-" * 80)
                    
                    elif data.get('type') == 'pong':
                        print(f"[{datetime.utcnow().isoformat()}] Pong received")
                    
                    else:
                        print(f"\n[Unknown Message Type: {data.get('type')}]")
                        print(json.dumps(data, indent=2))
                        print("-" * 80)
                    
                    # Send periodic ping to keep connection alive
                    if message_count % 10 == 0:
                        await websocket.send("ping")
                
                except websockets.exceptions.ConnectionClosed:
                    print("\n✗ Connection closed by server")
                    break
                except json.JSONDecodeError as e:
                    print(f"\n✗ Error decoding JSON: {e}")
                except KeyboardInterrupt:
                    print("\n\n✓ Disconnecting...")
                    break
    
    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
    except ConnectionRefusedError:
        print(f"\n✗ Connection refused. Is the server running on localhost:8000?")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        
        
    
    print("\n" + "=" * 80)
    print(f"  Total messages received: {message_count}")
    print("=" * 80)


async def test_with_custom_uri(uri: str):
    """Test with a custom WebSocket URI"""
    print(f"Connecting to custom URI: {uri}")
    
    async with websockets.connect(uri) as websocket:
        print("✓ Connected!")
        
        while True:
            message = await websocket.recv()
            print(f"Received: {message}")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Custom URI provided
        custom_uri = sys.argv[1]
        asyncio.run(test_with_custom_uri(custom_uri))
    else:
        # Default Kafka stream test
        asyncio.run(test_kafka_stream())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest client stopped by user")
        sys.exit(0)