#!/bin/bash
# Reset accumulated statistics in MongoDB

echo "Resetting accumulated statistics..."

mongosh --quiet <<EOF
use ngfw_pqc

// Delete corrupted document
db.accumulated_network_stats.deleteOne({_id: "accumulated_stats_v1"})

// Create fresh document
db.accumulated_network_stats.insertOne({
  _id: "accumulated_stats_v1",
  last_updated: new Date(),
  total_flows: 0,
  total_tls_flows: 0,
  total_tcp_flows: 0,
  total_udp_flows: 0,
  total_other_flows: 0,
  total_pqc_safe: 0,
  total_pqc_vulnerable: 0,
  total_pqc_unknown: 0,
  total_bytes_to_server: 0,
  total_bytes_to_client: 0,
  total_bytes: 0,
  total_alerts: 0,
  total_critical_alerts: 0,
  total_high_alerts: 0,
  total_medium_alerts: 0,
  total_low_alerts: 0,
  protocol_distribution: {},
  tls_version_distribution: {},
  cipher_suite_distribution: {},
  key_exchange_distribution: {},
  flow_state_distribution: {}
})

print("✓ Accumulated statistics reset successfully")
EOF

echo "Done! Restart the application."