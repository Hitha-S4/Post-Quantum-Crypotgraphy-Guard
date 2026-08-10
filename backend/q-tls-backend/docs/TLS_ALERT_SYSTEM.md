# TLS Alert System Documentation

## Overview

The TLS Alert System automatically detects and flags insecure TLS connections and vulnerable cryptography. It monitors for TLS versions less than 1.3 and connections without post-quantum cryptography (PQC) protection. All alerts are stored in MongoDB and broadcast in real-time via WebSocket.

## Features

### 1. **Automatic Alert Detection**

#### TLS Version Alerts
- Detects TLS 1.0, TLS 1.1, TLS 1.2, SSL 3.0, and SSL 2.0 connections
- Assigns severity levels based on TLS version:
  - **CRITICAL**: SSL 2.0, SSL 3.0, TLS 1.0
  - **HIGH**: TLS 1.1
  - **MEDIUM**: TLS 1.2

#### Vulnerable Crypto Alerts
- Detects connections using classical cryptography without PQC protection
- Flags connections vulnerable to future quantum computer attacks
- Severity: **HIGH** for all vulnerable (non-PQC) connections

### 2. **Alert Storage**
- Alerts are stored in MongoDB `alerts` collection
- Indexed for fast querying by timestamp, severity, type, and acknowledgment status
- Includes full connection details (source/destination IPs, ports, server name, cipher suite)

### 3. **Real-time WebSocket Streaming**
- WebSocket endpoint: `/ws/alerts`
- Broadcasts alerts immediately when created
- Supports ping/pong for connection health

### 4. **Comprehensive API Endpoints**

#### List All Alerts
```
GET /api/v1/alerts/list
Query Parameters:
  - limit: Maximum number of alerts (default: 100, max: 1000)
  - severity: Filter by severity (critical, high, medium, low, info)
  - alert_type: Filter by alert type
  - acknowledged: Filter by acknowledgment status (true/false)
```

#### Get Alerts by Severity
```
GET /api/v1/alerts/by-severity/{severity}
Path Parameters:
  - severity: critical, high, medium, low, or info
Query Parameters:
  - limit: Maximum number of alerts (default: 100)
```

#### Get Unacknowledged Alerts
```
GET /api/v1/alerts/unacknowledged
Query Parameters:
  - limit: Maximum number of alerts (default: 100)
```

#### Get Alert Statistics
```
GET /api/v1/alerts/stats
Returns:
  - Total alerts count
  - Unacknowledged alerts count
  - Breakdown by severity
  - Breakdown by type
```

#### Acknowledge Alert
```
POST /api/v1/alerts/{alert_id}/acknowledge
Query Parameters:
  - acknowledged_by: User who acknowledged the alert (optional)
```

## Alert Model

```json
{
  "id": "string",
  "timestamp": "2026-02-10T14:00:00Z",
  "alert_type": "insecure_tls_version",
  "severity": "medium",
  "title": "Insecure TLS Version Detected: TLS 1.2",
  "description": "Connection using TLS 1.2 detected from 192.168.1.100:54321 to 93.184.216.34:443 (Server: example.com). TLS 1.3 or higher is strongly recommended for security.",
  "source_ip": "192.168.1.100",
  "source_port": 54321,
  "destination_ip": "93.184.216.34",
  "destination_port": 443,
  "server_name": "example.com",
  "tls_version": "TLS 1.2",
  "cipher_suite": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
  "crypto_type": "classical",
  "metadata": {
    "tls_version": "TLS 1.2",
    "cipher_suite": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
    "crypto_type": "classical",
    "server_name": "example.com"
  },
  "acknowledged": false,
  "acknowledged_at": null,
  "acknowledged_by": null
}
```

## Alert Types

Currently supported alert types:
- `insecure_tls_version`: TLS version less than 1.3
- `no_pqc`: No post-quantum cryptography support (vulnerable to quantum attacks)
- `weak_cipher`: Weak cipher suite detected (future)
- `suspicious_connection`: Suspicious connection pattern (future)
- `protocol_violation`: Protocol violation detected (future)

## Severity Levels

- **CRITICAL**: Immediate action required (SSL 2.0, SSL 3.0, TLS 1.0)
- **HIGH**: Urgent attention needed (TLS 1.1, vulnerable crypto without PQC)
- **MEDIUM**: Should be addressed (TLS 1.2)
- **LOW**: Minor issue
- **INFO**: Informational only

## WebSocket Usage

### Connect to Alerts Stream
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alerts');

ws.onopen = () => {
  console.log('Connected to alerts stream');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'connected') {
    console.log('Connection confirmed:', data.message);
  } else if (data.type === 'alert') {
    console.log('New alert:', data.data);
    // Handle alert (show notification, update UI, etc.)
  }
};

// Send ping to keep connection alive
setInterval(() => {
  ws.send('ping');
}, 30000);
```

## API Usage Examples

### Get All Critical Alerts
```bash
curl "http://localhost:8000/api/v1/alerts/list?severity=critical&limit=50"
```

### Get Unacknowledged Alerts
```bash
curl "http://localhost:8000/api/v1/alerts/unacknowledged?limit=100"
```

### Acknowledge an Alert
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/60f7b3c4e4b0c8a9d8e7f6a5/acknowledge?acknowledged_by=admin"
```

### Get Alert Statistics
```bash
curl "http://localhost:8000/api/v1/alerts/stats"
```

## Integration with Kafka Consumer

The alert system is integrated into the Kafka consumer service:

1. **TLS Connection Processing**: When a TLS connection is processed from Kafka
2. **Version Check**: The TLS version is checked against secure versions
3. **Crypto Check**: The crypto type and PQC status are evaluated
4. **Alert Creation**:
   - If version < TLS 1.3, a TLS version alert is created
   - If crypto is vulnerable (classical, no PQC), a vulnerable crypto alert is created
5. **Storage**: Alerts are stored in MongoDB
6. **Broadcast**: Alerts are broadcast to WebSocket clients
7. **Logging**: Alert creation is logged with 🚨 emoji

## MongoDB Collections

### alerts Collection
- Stores all security alerts
- Indexed fields:
  - `timestamp` (descending)
  - `alert_type`
  - `severity`
  - `acknowledged`
  - `source_ip`
  - `destination_ip`
  - `tls_version`
  - Compound indexes for common queries

## Performance Considerations

1. **Indexing**: All query fields are indexed for fast retrieval
2. **Pagination**: All list endpoints support limit parameter
3. **Filtering**: Server-side filtering reduces data transfer
4. **WebSocket**: Efficient real-time updates without polling
5. **Async Operations**: All database operations are asynchronous

## Security Recommendations

Based on alert severity:

### Critical Alerts (SSL 2.0, SSL 3.0, TLS 1.0)
- **Action**: Block immediately
- **Risk**: Known vulnerabilities, easily exploitable
- **Recommendation**: Upgrade to TLS 1.3 immediately

### High Alerts (TLS 1.1, Vulnerable Crypto)
- **Action**: Plan immediate upgrade
- **Risk**:
  - TLS 1.1: Deprecated, security weaknesses
  - Vulnerable Crypto: Not quantum-safe, vulnerable to future quantum attacks
- **Recommendation**:
  - TLS 1.1: Upgrade to TLS 1.3 within days
  - Vulnerable Crypto: Implement PQC-enabled protocols

### Medium Alerts (TLS 1.2)
- **Action**: Plan upgrade
- **Risk**: Not quantum-safe, older protocol
- **Recommendation**: Upgrade to TLS 1.3 with PQC support within weeks/months

## Future Enhancements

1. **Alert Rules Engine**: Configurable alert rules
2. **Alert Aggregation**: Group similar alerts
3. **Alert Notifications**: Email, Slack, webhook notifications
4. **Alert Correlation**: Correlate alerts across connections
5. **Custom Alert Types**: User-defined alert types
6. **Alert Suppression**: Temporary suppression of known issues
7. **Alert Escalation**: Automatic escalation based on severity
8. **Alert Reports**: Scheduled alert reports

## Troubleshooting

### No Alerts Being Created
1. Check Kafka consumer is running
2. Verify TLS connections are being processed
3. Check alert service initialization in logs
4. Verify MongoDB connection

### WebSocket Not Receiving Alerts
1. Check WebSocket connection is established
2. Verify alert broadcast callback is configured
3. Check network/firewall settings
4. Review WebSocket logs

### Alerts Not Stored in Database
1. Check MongoDB connection
2. Verify alerts collection exists
3. Check database permissions
4. Review error logs

## Monitoring

Monitor these metrics:
- Total alerts created
- Alerts by severity
- Unacknowledged alerts count
- Alert creation rate
- WebSocket connection count
- Database query performance

## Conclusion

The TLS Alert System provides comprehensive monitoring and alerting for insecure TLS connections, helping organizations identify and remediate security risks in real-time.