#!/usr/bin/env python3
"""
Test script for Network Topology API endpoints
"""
import asyncio
import sys
from datetime import datetime
import httpx


BASE_URL = "http://localhost:8000/api/v1"


async def test_topology_graph():
    """Test the topology graph endpoint"""
    print("\n" + "=" * 80)
    print("Testing Network Topology Graph API")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        try:
            # Test with default parameters
            print("\n1. Fetching topology graph (60 min window)...")
            response = await client.get(f"{BASE_URL}/topology/graph")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success! Status: {response.status_code}")
                print(f"\nTopology Summary:")
                print(f"  Timestamp: {data['timestamp']}")
                print(f"  Time Window: {data['timeWindowMinutes']} minutes")
                print(f"  Total Nodes: {data['summary']['totalNodes']}")
                print(f"  Total Edges: {data['summary']['totalEdges']}")
                print(f"  Secure Connections: {data['summary']['secureConnections']}")
                print(f"  Insecure Connections: {data['summary']['insecureConnections']}")
                print(f"  Unknown Connections: {data['summary']['unknownConnections']}")

                # Show sample nodes
                if data["nodes"]:
                    print(f"\nSample Nodes (first 3):")
                    for i, (node_id, node) in enumerate(list(data["nodes"].items())[:3]):
                        print(f"\n  Node {i+1}: {node_id}")
                        print(f"    Type: {node['nodeType']}")
                        print(f"    Hostname: {node.get('hostname', 'N/A')}")
                        print(f"    Connections: {node['connectionCount']}")
                        print(
                            f"    Secure: {node['secureConnections']}, Insecure: {node['insecureConnections']}"
                        )
                        print(f"    Ports: {node['ports'][:5]}...")  # Show first 5 ports

                # Show sample edges
                if data["edges"]:
                    print(f"\nSample Edges (first 3):")
                    for i, (edge_id, edge) in enumerate(list(data["edges"].items())[:3]):
                        print(f"\n  Edge {i+1}: {edge_id}")
                        print(
                            f"    {edge['sourceIp']}:{edge['sourcePort']} -> {edge['destinationIp']}:{edge['destinationPort']}"
                        )
                        print(f"    Protocol: {edge['protocol']}")
                        print(
                            f"    Security: {edge['security']['pqcStatus']} ({edge['security']['cryptoType']})"
                        )
                        print(f"    Confidence: {edge['security']['confidence']:.2%}")
                        print(f"    TLS Version: {edge.get('tlsVersion', 'N/A')}")
                        print(f"    Server Name: {edge.get('serverName', 'N/A')}")
                        print(f"    Connections: {edge['connectionCount']}")
                        print(f"    Bytes: {edge['totalBytes']:,}")

            else:
                print(f"✗ Failed! Status: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()


async def test_topology_stats():
    """Test the topology statistics endpoint"""
    print("\n" + "=" * 80)
    print("Testing Network Topology Statistics API")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        try:
            print("\n2. Fetching topology statistics...")
            response = await client.get(f"{BASE_URL}/topology/stats")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success! Status: {response.status_code}")
                print(f"\nTopology Statistics:")
                print(f"  Total Nodes: {data['total_nodes']}")
                print(f"  Total Connections: {data['total_connections']}")
                print(f"  Secure Connections: {data['secure_connections']}")
                print(f"  Insecure Connections: {data['insecure_connections']}")
                print(f"  Unknown Connections: {data['unknown_connections']}")
                print(f"  Internal Nodes: {data['internal_nodes']}")
                print(f"  External Nodes: {data['external_nodes']}")

                print(f"\nSecurity Metrics:")
                print(f"  PQC Safe: {data['pqc_safe_percentage']:.2f}%")
                print(f"  Classical: {data['classical_percentage']:.2f}%")
                print(f"  Hybrid: {data['hybrid_percentage']:.2f}%")

                print(f"\nProtocol Distribution:")
                for proto, count in data["protocol_distribution"].items():
                    print(f"  {proto}: {count}")

                print(f"\nTop Sources:")
                for i, source in enumerate(data["top_sources"][:5], 1):
                    print(f"  {i}. {source['ip']}: {source['connections']} connections")

                print(f"\nTop Destinations:")
                for i, dest in enumerate(data["top_destinations"][:5], 1):
                    print(f"  {i}. {dest['ip']}: {dest['connections']} connections")

            else:
                print(f"✗ Failed! Status: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()


async def test_different_time_windows():
    """Test topology with different time windows"""
    print("\n" + "=" * 80)
    print("Testing Different Time Windows")
    print("=" * 80)

    time_windows = [15, 60, 240, 1440]  # 15 min, 1 hour, 4 hours, 24 hours

    async with httpx.AsyncClient() as client:
        for window in time_windows:
            try:
                print(f"\n3. Fetching topology for {window} minute window...")
                response = await client.get(
                    f"{BASE_URL}/topology/graph", params={"time_window": window}
                )

                if response.status_code == 200:
                    data = response.json()
                    print(
                        f"✓ {window} min window: {data['summary']['totalNodes']} nodes, "
                        f"{data['summary']['totalEdges']} edges"
                    )
                else:
                    print(f"✗ Failed for {window} min window: {response.status_code}")

            except Exception as e:
                print(f"✗ Error for {window} min window: {e}")


async def test_health_check():
    """Test if the API is running"""
    print("\n" + "=" * 80)
    print("Testing API Health")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        try:
            print("\n0. Checking API health...")
            response = await client.get(f"{BASE_URL}/health")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ API is healthy!")
                print(f"  Status: {data['status']}")
                print(f"  Service: {data['service']}")
            else:
                print(f"✗ API health check failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Cannot connect to API: {e}")
            print(f"\nMake sure the API is running at {BASE_URL}")
            return False

    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Network Topology API Test Suite")
    print("=" * 80)
    print(f"Testing API at: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")

    # Check if API is running
    if not await test_health_check():
        print("\n✗ API is not running. Please start the application first.")
        sys.exit(1)

    # Run tests
    await test_topology_graph()
    await test_topology_stats()
    await test_different_time_windows()

    print("\n" + "=" * 80)
    print("Test Suite Complete!")
    print("=" * 80)
    print("\nNote: If you see empty results, make sure:")
    print("  1. Kafka consumer is running and processing messages")
    print("  2. There is network traffic being captured by Suricata")
    print("  3. The topology service has had time to collect data")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
