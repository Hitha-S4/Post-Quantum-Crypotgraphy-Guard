# Event Filtering Strategy for Consistent Statistics

## Problem

Suricata generates **two events per TLS connection**:
1. **TLS event** (`event_type: "tls"`) - with algorithm data
2. **Flow event** (`event_type: "flow"`) - with byte counts

If both are stored in MongoDB, statistics become inconsistent:
- Duplicate connection counts
- Different PQC/vulnerable ratios between WebSocket and MongoDB
- Confusion about which classification to trust

## Solution: Store Only TLS Events in MongoDB

### Filtering Logic

```
┌─────────────────────────────────────────────────────────────┐
│                    Kafka Message Received                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ Has tls section?│
              └────────┬────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
          YES                     NO
           │                       │
           ▼                       ▼
    ┌──────────────┐      ┌──────────────┐
    │  TLS Event   │      │  Flow Event  │
    │              │      │              │
    │ • Algorithms │      │ • Byte count │
    │ • High conf  │      │ • Heuristic  │
    └──────┬───────┘      └──────┬───────┘
           │                     │
           ▼                     ▼
    ┌──────────────┐      ┌──────────────┐
    │ ✅ Store in  │      │ ❌ Skip      │
    │   MongoDB    │      │   MongoDB    │
    └──────┬───────┘      └──────┬───────┘
           │                     │
           └──────────┬──────────┘
                      │
                      ▼
              ┌───────────────┐
              │ ✅ Broadcast  │
              │  to WebSocket │
              └───────────────┘
```

### Implementation

**TLS Events** (with `tls` section):
- ✅ Stored in MongoDB
- ✅ Broadcasted to WebSocket
- ✅ Counted in statistics
- ✅ Used for analytics

**Flow Events** (without `tls` section):
- ❌ NOT stored in MongoDB
- ✅ Broadcasted to WebSocket (for real-time monitoring)
- ❌ NOT counted in statistics
- ❌ NOT used for analytics

## Benefits

### 1. Consistent Statistics

MongoDB and WebSocket now use the same data source:

| Metric | Before | After |
|--------|--------|-------|
| Total Connections | 200 (100 TLS + 100 flow) | 100 (TLS only) |
| PQC Safe | 30 TLS + 40 flow = 70 | 30 (TLS only) |
| Vulnerable | 70 TLS + 60 flow = 130 | 70 (TLS only) |
| **Consistency** | ❌ Inconsistent | ✅ Consistent |

### 2. Accurate Classification

Only algorithm-based detection is stored:

| Event Type | Detection Method | Confidence | Stored? |
|------------|-----------------|------------|---------|
| TLS | Algorithm-based | 0.70-1.00 | ✅ Yes |
| Flow | Byte-based heuristic | 0.50-0.85 | ❌ No |

### 3. No Duplicates

Each connection is counted exactly once:

```
Connection #1:
  - TLS event at 10:00:00 → Stored in MongoDB ✅
  - Flow event at 10:00:05 → Skipped ❌
  
Result: 1 connection in statistics (correct)
```

## WebSocket Behavior

WebSocket clients still receive **both** event types for real-time monitoring:

```javascript
// Frontend receives both
websocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.data.event_type === 'tls') {
    // TLS event: Has algorithms, high confidence
    // This one is also in MongoDB
  }
  
  if (data.data.event_type === 'flow') {
    // Flow event: Byte-based, lower confidence
    // This one is NOT in MongoDB
  }
};
```

**Recommendation**: Filter WebSocket display to show only TLS events for consistency with MongoDB statistics.

## MongoDB Queries

All queries now return consistent results:

```javascript
// Get PQC-safe connections
db.tls_connections.find({ 
  is_pqc: true 
})

// Get vulnerable connections  
db.tls_connections.find({ 
  is_pqc: false 
})

// All connections have algorithm data
db.tls_connections.find({
  "supported_groups": { $exists: true, $ne: [] }
})
```

## Statistics Service

The statistics service automatically gets consistent data:

```python
# This query only returns TLS events (with algorithms)
connections = await tls_collection.find({
    "timestamp": {"$gte": cutoff_time}
}).to_list()

# All connections have:
# - Algorithm data
# - High confidence scores
# - Accurate classification
```

## Migration

If you have existing data with both event types:

```javascript
// Clean up flow events from MongoDB
db.tls_connections.deleteMany({
  event_type: "flow"
})

// Or mark them
db.tls_connections.updateMany(
  { event_type: "flow" },
  { $set: { excluded_from_stats: true } }
)
```

## Configuration

No configuration needed - the filtering is automatic based on presence of `tls` section in the message.

## Logging

The system now logs clearly what's happening:

```
📨 INCOMING KAFKA MESSAGE #1
   Event Type: tls
   ✓ Stored in MongoDB
   ✓ Broadcasted to WebSocket

📨 INCOMING KAFKA MESSAGE #2
   Event Type: flow
   ⚠️  Flow event NOT stored in MongoDB (only TLS events with algorithms are stored)
   ✓ Broadcasted to WebSocket
```

## Frontend Recommendations

### Option 1: Show Only TLS Events (Recommended)

```javascript
websocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // Only display TLS events (matches MongoDB)
  if (data.data.event_type === 'tls') {
    displayConnection(data);
  }
};
```

### Option 2: Show Both with Labels

```javascript
websocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.data.event_type === 'tls') {
    displayConnection(data, { 
      label: 'TLS Event',
      badge: 'Stored in DB',
      color: 'green'
    });
  } else if (data.data.event_type === 'flow') {
    displayConnection(data, { 
      label: 'Flow Event',
      badge: 'Real-time only',
      color: 'blue'
    });
  }
};
```

### Option 3: Aggregate by flow_id

```javascript
const connections = new Map();

websocket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  const flowId = data.data.flow_id;
  
  if (data.data.event_type === 'tls') {
    // Store TLS event (has algorithms)
    connections.set(flowId, data);
  } else if (data.data.event_type === 'flow') {
    // Update with byte counts if TLS event exists
    const existing = connections.get(flowId);
    if (existing) {
      existing.data.flow = data.data.flow;
    }
  }
};
```

## Verification

### Check MongoDB Only Has TLS Events

```bash
# Should return 0
mongo ngfw_pqc --eval 'db.tls_connections.count({ event_type: "flow" })'

# Should return > 0
mongo ngfw_pqc --eval 'db.tls_connections.count({ event_type: "tls" })'
```

### Check Statistics Match

```bash
# Get stats from MongoDB
curl http://localhost:8000/api/statistics

# Compare with accumulated stats
curl http://localhost:8000/api/accumulated-stats
```

## Related Files

- [`src/ngfw_pqc_detector/services/kafka_consumer.py:140`](../src/ngfw_pqc_detector/services/kafka_consumer.py:140) - Filtering logic
- [`src/ngfw_pqc_detector/services/statistics_service.py`](../src/ngfw_pqc_detector/services/statistics_service.py) - Statistics aggregation
- [`docs/ALGORITHM_EXTRACTION_SUMMARY.md`](ALGORITHM_EXTRACTION_SUMMARY.md) - Event types explained

## Summary

✅ **MongoDB**: Only TLS events (with algorithms)  
✅ **WebSocket**: Both TLS and flow events (real-time)  
✅ **Statistics**: Consistent across all endpoints  
✅ **Classification**: Algorithm-based only (high confidence)  
✅ **No Duplicates**: Each connection counted once  