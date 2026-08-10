#!/bin/bash

echo "=========================================="
echo "Generating TLS Traffic for PQC Detection"
echo "=========================================="
echo ""

# Function to make HTTPS requests
generate_traffic() {
    local url=$1
    local description=$2
    echo "[$description] Connecting to: $url"
    curl -s -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n" "$url" 2>/dev/null || echo "Failed"
    sleep 1
}

echo "1. Generating traffic to major websites (likely classical TLS)..."
generate_traffic "https://www.google.com" "Google"
generate_traffic "https://www.github.com" "GitHub"
generate_traffic "https://www.amazon.com" "Amazon"
generate_traffic "https://www.microsoft.com" "Microsoft"
generate_traffic "https://www.apple.com" "Apple"

echo ""
echo "2. Generating traffic to Cloudflare (may support PQC)..."
generate_traffic "https://www.cloudflare.com" "Cloudflare"
generate_traffic "https://blog.cloudflare.com" "Cloudflare Blog"

echo ""
echo "3. Generating traffic to Google services (TLS 1.3)..."
generate_traffic "https://www.youtube.com" "YouTube"
generate_traffic "https://mail.google.com" "Gmail"
generate_traffic "https://drive.google.com" "Google Drive"

echo ""
echo "4. Generating traffic to social media (various TLS configs)..."
generate_traffic "https://www.facebook.com" "Facebook"
generate_traffic "https://www.twitter.com" "Twitter"
generate_traffic "https://www.linkedin.com" "LinkedIn"

echo ""
echo "5. Generating traffic to tech companies..."
generate_traffic "https://cloudflare.com" "Cloudflare"
generate_traffic "https://www.oracle.com" "Oracle"
generate_traffic "https://www.cisco.com" "Cisco"

echo ""
echo "6. Generating traffic to CDN providers..."
generate_traffic "https://www.akamai.com" "Akamai"
generate_traffic "https://www.fastly.com" "Fastly"

echo ""
echo "7. Generating additional diverse traffic..."
generate_traffic "https://www.wikipedia.org" "Wikipedia"
generate_traffic "https://www.reddit.com" "Reddit"
generate_traffic "https://www.stackoverflow.com" "Stack Overflow"
generate_traffic "https://www.netflix.com" "Netflix"

echo ""
echo "=========================================="
echo "Traffic generation complete!"
echo "Check your dashboard for updated statistics"
echo "=========================================="
echo ""
echo "Waiting 5 seconds for Suricata to process..."
sleep 5

echo ""
echo "Current MongoDB document count:"
mongosh ngfw_pqc --quiet --eval "print('TLS Connections: ' + db.tls_connections.countDocuments({})); print('TLS Sessions: ' + db.tls_sessions.countDocuments({}));"


