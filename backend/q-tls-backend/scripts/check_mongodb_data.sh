#!/bin/bash
# Script to check MongoDB data for TLS connections and statistics

echo "=========================================="
echo "MongoDB Data Checker"
echo "=========================================="
echo ""

# MongoDB connection details
MONGO_HOST="localhost"
MONGO_PORT="27017"
MONGO_DB="ngfw_pqc"

echo "Connecting to MongoDB at $MONGO_HOST:$MONGO_PORT"
echo "Database: $MONGO_DB"
echo ""

# Check if mongosh is available, otherwise try mongo
if command -v mongosh &> /dev/null; then
    MONGO_CMD="mongosh"
elif command -v mongo &> /dev/null; then
    MONGO_CMD="mongo"
else
    echo "❌ Error: Neither mongosh nor mongo command found"
    echo "Please install MongoDB shell"
    exit 1
fi

echo "Using MongoDB shell: $MONGO_CMD"
echo ""

# Execute MongoDB queries
$MONGO_CMD --quiet <<EOF
use $MONGO_DB

print("==========================================");
print("TLS CONNECTIONS COLLECTION");
print("==========================================");
print("");

// Count total documents
var totalCount = db.tls_connections.countDocuments();
print("Total TLS Connections: " + totalCount);
print("");

if (totalCount > 0) {
    // Count by crypto type
    print("Breakdown by Crypto Type:");
    db.tls_connections.aggregate([
        { \$group: { _id: "\$crypto_type", count: { \$sum: 1 } } },
        { \$sort: { count: -1 } }
    ]).forEach(function(doc) {
        var percentage = (doc.count / totalCount * 100).toFixed(1);
        print("  " + doc._id + ": " + doc.count + " (" + percentage + "%)");
    });
    print("");

    // Show latest 5 connections
    print("Latest 5 TLS Connections:");
    print("------------------------------------------");
    db.tls_connections.find().sort({timestamp: -1}).limit(5).forEach(function(doc) {
        print("• " + doc.timestamp.toISOString());
        print("  " + doc.source_ip + ":" + doc.source_port + " → " + doc.destination_ip + ":" + doc.destination_port);
        print("  Server: " + (doc.server_name || "N/A"));
        print("  Crypto: " + doc.crypto_type + " (confidence: " + (doc.detection_confidence * 100).toFixed(0) + "%)");
        print("  TLS: " + doc.tls_version);
        print("");
    });
} else {
    print("⚠️  No TLS connections found in database");
    print("");
}

print("==========================================");
print("TLS STATISTICS COLLECTION");
print("==========================================");
print("");

// Count statistics documents
var statsCount = db.tls_statistics.countDocuments();
print("Total Statistics Documents: " + statsCount);
print("");

if (statsCount > 0) {
    // Show latest statistics
    print("Latest Statistics:");
    print("------------------------------------------");
    var latestStats = db.tls_statistics.findOne({}, {sort: {timestamp: -1}});
    if (latestStats) {
        print("Timestamp: " + latestStats.timestamp.toISOString());
        print("Time Window: " + latestStats.time_window_minutes + " minutes");
        print("Events Processed: " + latestStats.events_processed);
        print("");
        print("Connection Statistics:");
        print("  Total: " + latestStats.connection_stats.total_connections);
        print("  PQC: " + latestStats.connection_stats.pqc_connections + 
              " (" + latestStats.connection_stats.pqc_percentage.toFixed(1) + "%)");
        print("  Hybrid: " + latestStats.connection_stats.hybrid_connections + 
              " (" + latestStats.connection_stats.hybrid_percentage.toFixed(1) + "%)");
        print("  Classical: " + latestStats.connection_stats.classical_connections + 
              " (" + latestStats.connection_stats.classical_percentage.toFixed(1) + "%)");
        print("");
    }
} else {
    print("⚠️  No statistics found in database");
    print("   Statistics are generated every " + (process.env.ANALYTICS_BATCH_INTERVAL || "60") + " seconds");
    print("");
}

print("==========================================");
print("COLLECTION INDEXES");
print("==========================================");
print("");

print("TLS Connections Indexes:");
db.tls_connections.getIndexes().forEach(function(idx) {
    print("  • " + JSON.stringify(idx.key));
});
print("");

print("TLS Statistics Indexes:");
db.tls_statistics.getIndexes().forEach(function(idx) {
    print("  • " + JSON.stringify(idx.key));
});
print("");

print("==========================================");
print("QUICK QUERIES");
print("==========================================");
print("");
print("To query MongoDB manually, use:");
print("");
print("  $MONGO_CMD");
print("  > use $MONGO_DB");
print("  > db.tls_connections.find().limit(5).pretty()");
print("  > db.tls_statistics.find().limit(1).pretty()");
print("");
print("To count PQC connections:");
print("  > db.tls_connections.countDocuments({is_pqc: true})");
print("");
print("To see latest connections:");
print("  > db.tls_connections.find().sort({timestamp: -1}).limit(10).pretty()");
print("");

EOF

echo "=========================================="
echo "Check complete!"
echo "=========================================="