#!/bin/bash
# Generate PQC-compliant TLS requests for testing

echo "=========================================="
echo "Generating PQC TLS Requests"
echo "=========================================="
echo ""

echo "This script will make HTTPS requests to known PQC-enabled servers."
echo "Your running Suricata instance should detect and log these connections."
echo ""

# Known PQC-enabled servers
PQC_SERVERS=(
    "pq.cloudflareresearch.com|Cloudflare PQC Research (Best for testing)"
    "www.google.com|Google (Hybrid PQC)"
    "www.cloudflare.com|Cloudflare"
    "blog.cloudflare.com|Cloudflare Blog"
)

echo "Available PQC-enabled servers:"
for i in "${!PQC_SERVERS[@]}"; do
    IFS='|' read -r url desc <<< "${PQC_SERVERS[$i]}"
    echo "  $((i+1)). $url - $desc"
done
echo ""

read -p "Select server (1-${#PQC_SERVERS[@]}) or press Enter for all: " choice

if [ -z "$choice" ]; then
    echo ""
    echo "Testing all servers..."
    echo ""
    
    for server_info in "${PQC_SERVERS[@]}"; do
        IFS='|' read -r url desc <<< "$server_info"
        echo "→ Testing: $url ($desc)"
        
        # Make multiple requests to ensure capture
        for i in {1..3}; do
            curl -s -o /dev/null --max-time 10 "https://$url" 2>/dev/null
            sleep 0.5
        done
        
        echo "  ✓ Completed 3 requests"
        sleep 1
    done
else
    if [ "$choice" -ge 1 ] && [ "$choice" -le "${#PQC_SERVERS[@]}" ]; then
        IFS='|' read -r url desc <<< "${PQC_SERVERS[$((choice-1))]}"
        echo ""
        echo "→ Testing: $url ($desc)"
        echo ""
        
        for i in {1..5}; do
            echo "  Request $i/5..."
            curl -s -o /dev/null --max-time 10 "https://$url" 2>/dev/null
            sleep 1
        done
        
        echo "  ✓ Completed 5 requests"
    else
        echo "Invalid choice"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "Requests Complete!"
echo "=========================================="
echo ""
echo "Check your Suricata logs for PQC detection:"
echo ""
echo "1. View real-time events:"
echo "   ./view-pqc-events.sh"
echo ""
echo "2. Check recent PQC connections:"
echo "   tail -20 logs/eve.json | jq 'select(.event_type==\"tls\") | .tls.pqc'"
echo ""
echo "3. Count PQC vs non-PQC:"
echo "   jq -r 'select(.event_type==\"tls\") | .tls.pqc.is_pqc' logs/eve.json | sort | uniq -c"
echo ""
echo "4. Show PQC postures:"
echo "   jq -r 'select(.event_type==\"tls\") | .tls.pqc.posture' logs/eve.json | sort | uniq -c"
echo ""
echo "5. Find specific server:"
echo "   jq 'select(.tls.sni==\"pq.cloudflareresearch.com\") | .tls.pqc' logs/eve.json"
echo ""