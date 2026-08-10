# Network Topology API Testing

## Overview

This directory contains a test script for the Network Topology API endpoints that provide real-time network connection mapping and visualization data.

## Test Script

### `test_topology_api.py`

Comprehensive test suite for the Network Topology API endpoints.

**Features:**
- Tests topology graph endpoint with various time windows
- Tests topology statistics endpoint
- Validates data structure and content
- Shows sample nodes and edges with security information
- Displays top talkers and protocol distribution

**Usage:**

```bash
# Make sure the API is running first
python scripts/test_topology_api.py
```

**Requirements:**
```bash
pip install httpx
```

## API Endpoints Tested

### 1. GET /api/v1/topology/graph
Returns the complete network topology graph with nodes and edges.

**Parameters:**
- `time_window` (optional): Time window in minutes (default: 60, max: 1440)
- `include_inactive` (optional): Include inactive nodes/edges (default: false)

**Example:**
```bash
curl "http://localhost:8000/api/v1/topology/graph?time_window=60"
```

### 2. GET /api/v1/topology/stats
Returns aggregated topology statistics.

**Parameters:**
- `time_window` (optional): Time window in minutes (default: 60, max: 1440)

**Example:**
```bash
curl "http://localhost:8000/api/v1/topology/stats?time_window=60"
```

## Expected Output

### Topology Graph Response
```json
{
  "timestamp": "2026-02-10T13:55:00Z",
  "timeWindowMinutes": 60,
  "nodes": {
    "192.168.1.87": {
      "nodeId": "192.168.1.87",
      "nodeType": "internal",
      "hostname": null,
      "firstSeen": "2026-02-10T13:00:00Z",
      "lastSeen": "2026-02-10T13:55:00Z",
      "connectionCount": 150,
      "secureConnections": 45,
      "insecureConnections": 105,
      "ports": [52349, 52350],
      "protocols": ["TCP"]
    }
  },
  "edges": {
    "192.168.1.87:52349->13.126.138.201:443": {
      "edgeId": "192.168.1.87:52349->13.126.138.201:443",
      "sourceIp": "192.168.1.87",
      "sourcePort": 52349,
      "destinationIp": "13.126.138.201",
      "destinationPort": 443,
      "protocol": "TCP",
      "security": {
        "isSecure": false,
        "cryptoType": "classical",
        "pqcStatus": "vulnerable",
        "confidence": 0.6667,
        "hasEch": true,
        "posture": "ECH_PROTECTED"
      },
      "tlsVersion": "TLS 1.3",
      "serverName": "enterprise.example.com",
      "connectionCount": 25,
      "totalBytes": 60000
    }
  },
  "summary": {
    "totalNodes": 25,
    "totalEdges": 150,
    "secureConnections": 45,
    "insecureConnections": 95,
    "unknownConnections": 10
  }
}
```

### Topology Statistics Response
```json
{
  "totalNodes": 25,
  "totalConnections": 150,
  "secureConnections": 45,
  "insecureConnections": 95,
  "unknownConnections": 10,
  "internalNodes": 5,
  "externalNodes": 20,
  "protocolDistribution": {
    "TCP": 140,
    "UDP": 10
  },
  "topSources": [
    {"ip": "192.168.1.87", "connections": 75}
  ],
  "topDestinations": [
    {"ip": "13.126.138.201", "connections": 60}
  ],
  "pqcSafePercentage": 30.0,
  "classicalPercentage": 63.33,
  "hybridPercentage": 6.67
}
```

## Troubleshooting

### Empty Results
If you see empty nodes/edges:
1. Ensure Kafka consumer is running and processing messages
2. Verify Suricata is capturing network traffic
3. Wait a few minutes for data to accumulate
4. Check MongoDB collections: `network_nodes` and `network_edges`

### Connection Errors
If you get connection errors:
1. Verify the API is running: `curl http://localhost:8000/api/v1/health`
2. Check the port (default: 8000)
3. Ensure MongoDB is running and accessible

### No Security Data
If security information is missing:
1. Verify TLS traffic is being captured
2. Check that PQC detection is working
3. Review Kafka messages for TLS data

## Visualization Examples

### Using the API with curl

```bash
# Get topology for last hour
curl "http://localhost:8000/api/v1/topology/graph?time_window=60" | jq .

# Get topology statistics
curl "http://localhost:8000/api/v1/topology/stats" | jq .

# Get topology for last 24 hours
curl "http://localhost:8000/api/v1/topology/graph?time_window=1440" | jq .

# Include inactive nodes
curl "http://localhost:8000/api/v1/topology/graph?include_inactive=true" | jq .
```

### Using with Python

```python
import httpx
import asyncio

async def get_topology():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/topology/graph",
            params={"time_window": 60}
        )
        return response.json()

topology = asyncio.run(get_topology())
print(f"Nodes: {len(topology['nodes'])}")
print(f"Edges: {len(topology['edges'])}")
```

### Using with JavaScript/TypeScript

```javascript
// Fetch topology data
const response = await fetch(
  'http://localhost:8000/api/v1/topology/graph?time_window=60'
);
const topology = await response.json();

console.log(`Nodes: ${Object.keys(topology.nodes).length}`);
console.log(`Edges: ${Object.keys(topology.edges).length}`);
console.log(`Secure: ${topology.summary.secureConnections}`);
console.log(`Insecure: ${topology.summary.insecureConnections}`);
```

## Integration with Visualization Libraries

See the main documentation at `docs/NETWORK_TOPOLOGY_MAPPING.md` for examples of:
- D3.js force-directed graphs
- Cytoscape.js network diagrams
- Custom React/Vue components
- Real-time updates via WebSocket

## Performance Tips

1. **Use appropriate time windows**: Shorter windows (15-60 min) for real-time monitoring
2. **Cache results**: Cache topology data for frequently accessed time windows
3. **Use statistics endpoint**: For dashboards, use `/topology/stats` instead of full graph
4. **Pagination**: For large networks, consider implementing pagination
5. **Filtering**: Filter by node type, protocol, or security status as needed

## Related Documentation

- [Network Topology Mapping](../docs/NETWORK_TOPOLOGY_MAPPING.md) - Complete feature documentation
- [API Routes](../src/ngfw_pqc_detector/api/routes.py) - API implementation
- [Topology Service](../src/ngfw_pqc_detector/services/topology_service.py) - Service implementation
- [Topology Models](../src/ngfw_pqc_detector/models/network_topology.py) - Data models