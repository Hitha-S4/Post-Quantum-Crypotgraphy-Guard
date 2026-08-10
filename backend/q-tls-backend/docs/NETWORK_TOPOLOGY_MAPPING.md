# Network Topology Mapping System

## Overview

The Network Topology Mapping system provides real-time visualization of network connections, showing which machines (IP addresses) connect to which destinations, along with security status indicators. This enables graphical representation of network traffic flows and identification of insecure connections.

## Features

### 1. **Network Graph Visualization**
- **Nodes**: Represent IP addresses (sources and destinations)
- **Edges**: Represent connections between nodes
- **Security Status**: Each connection is classified as secure (PQC-safe), insecure (vulnerable), or unknown
- **Real-time Updates**: Topology is updated as new connections are detected from Kafka messages

### 2. **Connection Security Indicators**
Each connection includes:
- **Crypto Type**: classical, post-quantum, hybrid, or unknown
- **PQC Status**: safe, vulnerable, or unknown
- **Confidence Score**: Detection confidence (0.0 to 1.0)
- **ECH Support**: Whether Encrypted Client Hello is used
- **Posture**: Suricata's PQC posture classification

### 3. **Node Classification**
Nodes are automatically classified as:
- **Internal**: Private IP addresses (192.168.x.x, 10.x.x.x, 172.x.x.x)
- **External**: Public IP addresses
- **Source**: Originating connections
- **Destination**: Receiving connections

## Data Model

### NetworkNode
```python
{
    "nodeId": "192.168.1.87",           # IP address
    "nodeType": "internal",              # internal/external
    "hostname": "example.com",           # Optional hostname/SNI
    "firstSeen": "2026-02-10T13:00:00Z",
    "lastSeen": "2026-02-10T13:55:00Z",
    "connectionCount": 150,
    "secureConnections": 45,
    "insecureConnections": 105,
    "ports": [52349, 52350, 52351],
    "protocols": ["TCP", "UDP"]
}
```

### NetworkEdge
```python
{
    "edgeId": "192.168.1.87:52349->13.126.138.201:443",
    "sourceIp": "192.168.1.87",
    "sourcePort": 52349,
    "destinationIp": "13.126.138.201",
    "destinationPort": 443,
    "protocol": "TCP",
    "firstSeen": "2026-02-10T13:24:45Z",
    "lastSeen": "2026-02-10T13:55:00Z",
    "connectionCount": 25,
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
    "bytesToServer": 15000,
    "bytesToClient": 45000,
    "totalBytes": 60000
}
```

## API Endpoints

### 1. Get Network Topology Graph
```http
GET /api/v1/topology/graph?time_window=60&include_inactive=false
```

**Parameters:**
- `time_window` (optional): Time window in minutes (default: 60, max: 1440)
- `include_inactive` (optional): Include nodes/edges not seen in time window (default: false)

**Response:**
```json
{
    "timestamp": "2026-02-10T13:55:00Z",
    "timeWindowMinutes": 60,
    "nodes": {
        "192.168.1.87": { /* NetworkNode */ },
        "13.126.138.201": { /* NetworkNode */ }
    },
    "edges": {
        "192.168.1.87:52349->13.126.138.201:443": { /* NetworkEdge */ }
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

### 2. Get Topology Statistics
```http
GET /api/v1/topology/stats?time_window=60
```

**Parameters:**
- `time_window` (optional): Time window in minutes (default: 60, max: 1440)

**Response:**
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
        {"ip": "192.168.1.87", "connections": 75},
        {"ip": "192.168.1.100", "connections": 50}
    ],
    "topDestinations": [
        {"ip": "13.126.138.201", "connections": 60},
        {"ip": "52.84.123.45", "connections": 45}
    ],
    "pqcSafePercentage": 30.0,
    "classicalPercentage": 63.33,
    "hybridPercentage": 6.67
}
```

## MongoDB Collections

### network_nodes
Stores information about network nodes (IP addresses):
- **Indexes**: `node_id` (unique), `last_seen`, `node_type`
- **TTL**: Configurable cleanup of old data

### network_edges
Stores information about connections between nodes:
- **Indexes**: `edge_id` (unique), `source_ip`, `destination_ip`, `last_seen`, `security.pqc_status`
- **Composite Index**: `(source_ip, destination_ip)`

## Integration

### Kafka Consumer Integration
The topology service is automatically updated when processing Kafka messages:

```python
# In kafka_consumer.py
if self.topology_service:
    await self.topology_service.update_topology_from_connection(
        source_ip=message.get('src_ip'),
        source_port=message.get('src_port'),
        dest_ip=message.get('dest_ip'),
        dest_port=message.get('dest_port'),
        protocol=message.get('proto'),
        crypto_type=crypto_type.value,
        pqc_status=pqc_status,
        confidence=confidence,
        tls_version=tls_version,
        server_name=sni,
        cipher_suite=cipher_suite,
        bytes_to_server=bytes_to_server,
        bytes_to_client=bytes_to_client,
        has_ech=has_ech,
        posture=suricata_posture,
    )
```

## Visualization Examples

### 1. Network Graph Visualization
Use the `/topology/graph` endpoint to create:
- **Force-directed graphs** showing network topology
- **Hierarchical layouts** showing internal vs external nodes
- **Security heat maps** highlighting insecure connections

### 2. Security Dashboard
Use the `/topology/stats` endpoint to display:
- **Top talkers** (most active sources/destinations)
- **Protocol distribution** pie charts
- **Security metrics** (PQC adoption percentage)
- **Connection trends** over time

## Example: Visualizing with D3.js

```javascript
// Fetch topology data
const response = await fetch('/api/v1/topology/graph?time_window=60');
const topology = await response.json();

// Create nodes array for D3
const nodes = Object.values(topology.nodes).map(node => ({
    id: node.nodeId,
    type: node.nodeType,
    label: node.hostname || node.nodeId,
    secureRatio: node.secureConnections / node.connectionCount
}));

// Create links array for D3
const links = Object.values(topology.edges).map(edge => ({
    source: edge.sourceIp,
    target: edge.destinationIp,
    isSecure: edge.security.isSecure,
    cryptoType: edge.security.cryptoType,
    weight: edge.connectionCount
}));

// Color nodes by security status
const colorScale = d3.scaleLinear()
    .domain([0, 0.5, 1])
    .range(['red', 'yellow', 'green']);

// Render force-directed graph
const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id))
    .force('charge', d3.forceManyBody())
    .force('center', d3.forceCenter(width / 2, height / 2));
```

## Example: Visualizing with Cytoscape.js

```javascript
// Fetch topology data
const response = await fetch('/api/v1/topology/graph?time_window=60');
const topology = await response.json();

// Convert to Cytoscape format
const elements = [
    // Nodes
    ...Object.values(topology.nodes).map(node => ({
        data: {
            id: node.nodeId,
            label: node.hostname || node.nodeId,
            type: node.nodeType,
            secureConnections: node.secureConnections,
            insecureConnections: node.insecureConnections
        }
    })),
    // Edges
    ...Object.values(topology.edges).map(edge => ({
        data: {
            id: edge.edgeId,
            source: edge.sourceIp,
            target: edge.destinationIp,
            isSecure: edge.security.isSecure,
            cryptoType: edge.security.cryptoType,
            label: `${edge.protocol}:${edge.destinationPort}`
        }
    }))
];

// Create Cytoscape instance
const cy = cytoscape({
    container: document.getElementById('cy'),
    elements: elements,
    style: [
        {
            selector: 'node',
            style: {
                'background-color': function(ele) {
                    return ele.data('type') === 'internal' ? '#0074D9' : '#FF4136';
                },
                'label': 'data(label)'
            }
        },
        {
            selector: 'edge',
            style: {
                'line-color': function(ele) {
                    return ele.data('isSecure') ? '#2ECC40' : '#FF4136';
                },
                'width': 2,
                'curve-style': 'bezier',
                'target-arrow-shape': 'triangle'
            }
        }
    ],
    layout: {
        name: 'cose',
        idealEdgeLength: 100,
        nodeOverlap: 20
    }
});
```

## Data Cleanup

The topology service includes automatic cleanup of old data:

```python
# Clean up data older than 7 days
await topology_service.cleanup_old_data(days=7)
```

This can be scheduled as a background job to prevent database growth.

## Performance Considerations

1. **Time Windows**: Use appropriate time windows (default 60 minutes) to balance detail vs performance
2. **Indexes**: MongoDB indexes are automatically created for efficient queries
3. **Aggregation**: Use the `/topology/stats` endpoint for aggregated data instead of processing full graph
4. **Caching**: Consider caching topology data for frequently accessed time windows

## Security Considerations

1. **IP Privacy**: Consider anonymizing internal IP addresses in production
2. **Access Control**: Implement authentication/authorization for topology endpoints
3. **Rate Limiting**: Apply rate limits to prevent abuse
4. **Data Retention**: Configure appropriate data retention policies

## Future Enhancements

1. **Geolocation**: Add geographic location data for external IPs
2. **Threat Intelligence**: Integrate with threat intelligence feeds
3. **Anomaly Detection**: Detect unusual connection patterns
4. **Historical Analysis**: Compare current topology with historical baselines
5. **Export Formats**: Support exporting topology in various formats (GraphML, GEXF, etc.)