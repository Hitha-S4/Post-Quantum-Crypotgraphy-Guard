#!/bin/bash

# PQC Guard - Complete Service Startup Script
# This script starts all required services for the PQC Guard application

set -e

PROJECT_ROOT="/Users/hithas/Documents/personal/Post-Quantum-Crypotgraphy-Guard"
SURICATA_DIR="$PROJECT_ROOT/suricata"
BACKEND_DIR="$PROJECT_ROOT/backend/q-tls-backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend/q-tls-ui"

echo "=========================================="
echo "PQC Guard - Starting All Services"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
    local service=$1
    if brew services list | grep "$service" | grep -q "started"; then
        echo -e "${GREEN}✓${NC} $service is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not running"
        return 1
    fi
}

# Function to check if a port is in use
check_port() {
    local port=$1
    local service=$2
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service is running on port $port"
        return 0
    else
        echo -e "${YELLOW}!${NC} $service is not running on port $port"
        return 1
    fi
}

echo ""
echo "Step 1: Checking MongoDB..."
if ! check_service "mongodb-community"; then
    echo "Starting MongoDB..."
    brew services start mongodb-community
    sleep 3
fi

echo ""
echo "Step 2: Checking Kafka..."
if ! check_service "kafka"; then
    echo "Starting Kafka..."
    brew services start kafka
    sleep 5
fi

echo ""
echo "Step 3: Verifying Kafka topic..."
if kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -q "suricata-events"; then
    echo -e "${GREEN}✓${NC} Kafka topic 'suricata-events' exists"
else
    echo "Creating Kafka topic 'suricata-events'..."
    kafka-topics --create \
        --bootstrap-server localhost:9092 \
        --topic suricata-events \
        --partitions 1 \
        --replication-factor 1
fi

echo ""
echo "Step 4: Checking Suricata..."
if [ ! -f "$SURICATA_DIR/src/suricata" ]; then
    echo -e "${RED}✗${NC} Suricata is not built yet"
    echo "Please run: cd suricata && ./autogen.sh && ./configure --enable-rust && make -j\$(sysctl -n hw.ncpu)"
    exit 1
else
    echo -e "${GREEN}✓${NC} Suricata binary exists"
fi

echo ""
echo "Step 5: Creating log directories..."
mkdir -p "$SURICATA_DIR/logs"
mkdir -p /opt/homebrew/var/log/filebeat
echo -e "${GREEN}✓${NC} Log directories created"

echo ""
echo "Step 6: Checking Backend..."
if ! check_port 8000 "Backend API"; then
    echo -e "${YELLOW}Backend not running. Start it with:${NC}"
    echo "cd $BACKEND_DIR && source venv/bin/activate && uvicorn src.ngfw_pqc_detector.main:app --host 0.0.0.0 --port 8000 --reload"
fi

echo ""
echo "Step 7: Checking Frontend..."
if ! check_port 8080 "Frontend UI"; then
    echo -e "${YELLOW}Frontend not running. Start it with:${NC}"
    echo "cd $FRONTEND_DIR && npm run dev -- --host 0.0.0.0 --port 8080"
fi

echo ""
echo "=========================================="
echo "Service Status Summary"
echo "=========================================="
check_service "mongodb-community" || true
check_service "kafka" || true
check_port 8000 "Backend API" || true
check_port 8080 "Frontend UI" || true

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Start Suricata (in a new terminal):"
echo "   cd $SURICATA_DIR"
echo "   sudo ./src/suricata -c suricata.yaml -i en0 -l logs -v"
echo ""
echo "2. Start Filebeat (in a new terminal):"
echo "   sudo filebeat -e -c /opt/homebrew/etc/filebeat/filebeat.yml"
echo ""
echo "3. Access the application:"
echo "   Frontend: http://localhost:8080"
echo "   Backend API: http://localhost:8000/docs"
echo ""
echo "4. Generate test traffic:"
echo "   curl -I https://www.google.com"
echo "   curl -I https://www.cloudflare.com"
echo ""


