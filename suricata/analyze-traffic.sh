#!/bin/bash
# Traffic Analysis Script
# Provides summary statistics from captured traffic

echo "=========================================="
echo "Suricata Traffic Analysis"
echo "=========================================="
echo ""

if [ ! -f "logs/eve.json" ]; then
    echo "❌ No traffic data found!"
    echo "   Run ./monitor-network.sh first to capture traffic."
    exit 1
fi

echo "📊 Traffic Summary:"
echo ""

# Count total events
total_events=$(wc -l < logs/eve.json)
echo "Total Events: $total_events"
echo ""

# Count alerts
alerts=$(grep -c '"event_type":"alert"' logs/eve.json 2>/dev/null || echo "0")
echo "🚨 Alerts: $alerts"

# Count flows
flows=$(grep -c '"event_type":"flow"' logs/eve.json 2>/dev/null || echo "0")
echo "🔄 Flows: $flows"

# Count DNS queries
dns=$(grep -c '"event_type":"dns"' logs/eve.json 2>/dev/null || echo "0")
echo "🌐 DNS Queries: $dns"

# Count HTTP requests
http=$(grep -c '"event_type":"http"' logs/eve.json 2>/dev/null || echo "0")
echo "📡 HTTP Requests: $http"

# Count TLS connections
tls=$(grep -c '"event_type":"tls"' logs/eve.json 2>/dev/null || echo "0")
echo "🔒 TLS Connections: $tls"

echo ""
echo "=========================================="
echo ""
echo "📁 Detailed logs available in:"
echo "   - logs/fast.log (Quick alerts)"
echo "   - logs/eve.json (Full JSON data)"
echo "   - logs/stats.log (Statistics)"
echo ""

# Show recent alerts if any
if [ "$alerts" -gt 0 ]; then
    echo "🔍 Recent Alerts:"
    echo ""
    tail -5 logs/fast.log 2>/dev/null || echo "No alerts in fast.log"
    echo ""
fi

echo "=========================================="


