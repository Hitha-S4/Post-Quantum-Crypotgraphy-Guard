#!/bin/bash
# View PQC TLS events from WebSocket in real-time
# Connects to the FastAPI WebSocket endpoint and displays events

WEBSOCKET_URL="ws://localhost:8000/ws/kafka-stream"

echo "=========================================="
echo "PQC TLS Event Monitor (WebSocket)"
echo "=========================================="
echo ""
echo "Connecting to: $WEBSOCKET_URL"
echo "Press Ctrl+C to stop"
echo ""
echo "Waiting for TLS connections..."
echo ""

# Check if Python and websockets are available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

# Create a temporary Python script to connect to WebSocket
python3 - <<'EOF'
import asyncio
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("❌ Error: websockets library not installed")
    print("Install it with: pip install websockets")
    sys.exit(1)

async def monitor_websocket():
    uri = "ws://localhost:8000/ws/kafka-stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket\n")
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Skip connection confirmation messages
                    if data.get('type') == 'connected':
                        continue
                    
                    # Process Kafka messages
                    if data.get('type') == 'kafka_message':
                        event = data.get('data', {})
                        
                        # Only process TLS events
                        if event.get('event_type') == 'tls':
                            tls = event.get('tls', {})
                            pqc = tls.get('pqc', {})
                            
                            print("━" * 80)
                            print(f"⏰ Time:        {event.get('timestamp', 'N/A')}")
                            print(f"🌐 Connection:  {event.get('src_ip', 'N/A')}:{event.get('src_port', 'N/A')} → {event.get('dest_ip', 'N/A')}:{event.get('dest_port', 'N/A')}")
                            print(f"🔒 TLS:         {tls.get('version', 'unknown')}")
                            print(f"📝 SNI:         {tls.get('sni', 'none')}")
                            print(f"🔐 PQC Posture: {pqc.get('posture', 'UNKNOWN')}")
                            print(f"✨ Is PQC:      {str(pqc.get('is_pqc', False)).lower()}")
                            print(f"🛡️  Has ECH:     {str(pqc.get('has_ech', False)).lower()}")
                            
                            # Supported groups
                            groups = pqc.get('supported_groups', [])
                            if groups:
                                print(f"📊 Groups:      {', '.join(map(str, groups))}")
                            
                            # Group names
                            group_names = pqc.get('supported_groups_names', [])
                            if group_names:
                                print(f"📋 Group Names: {', '.join(group_names)}")
                            
                            # Key share groups
                            key_shares = pqc.get('key_share_groups_names', [])
                            if key_shares:
                                print(f"🔑 Key Shares:  {', '.join(key_shares)}")
                            
                            print("━" * 80)
                            print()
                    
                    # Send periodic ping every 10 messages
                    if hasattr(monitor_websocket, 'msg_count'):
                        monitor_websocket.msg_count += 1
                    else:
                        monitor_websocket.msg_count = 1
                    
                    if monitor_websocket.msg_count % 10 == 0:
                        await websocket.send("ping")
                
                except websockets.exceptions.ConnectionClosed:
                    print("\n✗ Connection closed by server")
                    break
                except json.JSONDecodeError as e:
                    print(f"\n✗ Error decoding JSON: {e}")
                except KeyboardInterrupt:
                    print("\n\n✓ Disconnecting...")
                    break
    
    except ConnectionRefusedError:
        print(f"\n✗ Connection refused. Is the server running on localhost:8000?")
        print("Start the server with: python -m ngfw_pqc_detector.main")
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(monitor_websocket())
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        sys.exit(0)
EOF
