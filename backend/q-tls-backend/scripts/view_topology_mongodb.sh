#!/bin/bash
# Script to view network topology data in MongoDB

echo "================================================================================"
echo "Network Topology MongoDB Data Viewer"
echo "================================================================================"
echo ""

# MongoDB connection details
MONGO_HOST="localhost"
MONGO_PORT="27017"
MONGO_DB="ngfw_pqc_detector"

echo "Connecting to MongoDB: mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}"
echo ""

# Check if mongosh is available, otherwise use mongo
if command -v mongosh &> /dev/null; then
    MONGO_CMD="mongosh"
else
    MONGO_CMD="mongo"
fi

echo "================================================================================"
echo "1. Network Nodes Collection"
echo "================================================================================"
echo ""
echo "Total nodes:"
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "db.network_nodes.countDocuments()"
echo ""

echo "Sample nodes (first 5):"
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "
db.network_nodes.find().limit(5).forEach(function(doc) {
    print('---');
    print('Node ID: ' + doc.node_id);
    print('Type: ' + doc.node_type);
    print('Hostname: ' + (doc.hostname || 'N/A'));
    print('First Seen: ' + doc.first_seen);
    print('Last Seen: ' + doc.last_seen);
    print('Total Connections: ' + doc.connection_count);
    print('Secure: ' + doc.secure_connections + ', Insecure: ' + doc.insecure_connections);
    print('Ports: ' + JSON.stringify(doc.ports));
    print('Protocols: ' + JSON.stringify(doc.protocols));
})
"
echo ""

echo "================================================================================"
echo "2. Network Edges Collection"
echo "================================================================================"
echo ""
echo "Total edges:"
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "db.network_edges.countDocuments()"
echo ""

echo "Sample edges (first 5):"
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "
db.network_edges.find().limit(5).forEach(function(doc) {
    print('---');
    print('Edge ID: ' + doc.edge_id);
    print('Connection: ' + doc.source_ip + ':' + doc.source_port + ' -> ' + doc.destination_ip + ':' + doc.destination_port);
    print('Protocol: ' + doc.protocol);
    print('First Seen: ' + doc.first_seen);
    print('Last Seen: ' + doc.last_seen);
    print('Connection Count: ' + doc.connection_count);
    print('Security Status: ' + doc.security.pqc_status + ' (' + doc.security.crypto_type + ')');
    print('Confidence: ' + (doc.security.confidence * 100).toFixed(2) + '%');
    print('TLS Version: ' + (doc.tls_version || 'N/A'));
    print('Server Name: ' + (doc.server_name || 'N/A'));
    print('Bytes: ' + doc.total_bytes + ' (to server: ' + doc.bytes_to_server + ', to client: ' + doc.bytes_to_client + ')');
})
"
echo ""

echo "================================================================================"
echo "3. Security Status Distribution"
echo "================================================================================"
echo ""
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "
db.network_edges.aggregate([
    {
        \$group: {
            _id: '\$security.pqc_status',
            count: { \$sum: 1 }
        }
    },
    {
        \$sort: { count: -1 }
    }
]).forEach(function(doc) {
    print(doc._id + ': ' + doc.count);
})
"
echo ""

echo "================================================================================"
echo "4. Top Source IPs (by connection count)"
echo "================================================================================"
echo ""
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "
db.network_nodes.find({ node_type: 'internal' }).sort({ connection_count: -1 }).limit(10).forEach(function(doc) {
    print(doc.node_id + ': ' + doc.connection_count + ' connections (secure: ' + doc.secure_connections + ', insecure: ' + doc.insecure_connections + ')');
})
"
echo ""

echo "================================================================================"
echo "5. Top Destination IPs (by connection count)"
echo "================================================================================"
echo ""
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "
db.network_nodes.find({ node_type: 'external' }).sort({ connection_count: -1 }).limit(10).forEach(function(doc) {
    print(doc.node_id + ' (' + (doc.hostname || 'no hostname') + '): ' + doc.connection_count + ' connections');
})
"
echo ""

echo "================================================================================"
echo "6. Insecure Connections (Vulnerable)"
echo "================================================================================"
echo ""
echo "Count:"
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "db.network_edges.countDocuments({ 'security.pqc_status': 'vulnerable' })"
echo ""
echo "Sample insecure connections:"
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "
db.network_edges.find({ 'security.pqc_status': 'vulnerable' }).limit(5).forEach(function(doc) {
    print('---');
    print(doc.source_ip + ':' + doc.source_port + ' -> ' + doc.destination_ip + ':' + doc.destination_port);
    print('Server: ' + (doc.server_name || 'N/A'));
    print('Crypto: ' + doc.security.crypto_type + ', TLS: ' + (doc.tls_version || 'N/A'));
})
"
echo ""

echo "================================================================================"
echo "7. Protocol Distribution"
echo "================================================================================"
echo ""
$MONGO_CMD --quiet mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval "
db.network_edges.aggregate([
    {
        \$group: {
            _id: '\$protocol',
            count: { \$sum: 1 }
        }
    },
    {
        \$sort: { count: -1 }
    }
]).forEach(function(doc) {
    print(doc._id + ': ' + doc.count);
})
"
echo ""

echo "================================================================================"
echo "Done!"
echo "================================================================================"