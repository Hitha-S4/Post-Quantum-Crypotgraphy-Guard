#!/bin/bash

# PQC Guard - Suricata Build Script
# This script builds Suricata with PQC detection support

set -e

# Add rustup to PATH if it exists
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
fi

PROJECT_ROOT="/Users/hithas/Documents/personal/Post-Quantum-Crypotgraphy-Guard"
SURICATA_DIR="$PROJECT_ROOT/suricata"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Building Suricata with PQC Support"
echo "=========================================="

cd "$SURICATA_DIR"

echo ""
echo "Step 1: Checking dependencies..."
MISSING_DEPS=()

# Check brew dependencies (excluding rust which may be from rustup)
for dep in autoconf automake libtool pkg-config pcre2 jansson; do
    if ! brew list $dep &>/dev/null; then
        MISSING_DEPS+=($dep)
    fi
done

# Check for rust (either brew or rustup)
if ! command -v rustc &>/dev/null; then
    echo -e "${RED}✗${NC} Rust not found"
    echo "Please install rust with: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
else
    RUST_VERSION=$(rustc --version)
    echo -e "${GREEN}✓${NC} Rust installed: $RUST_VERSION"
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${RED}✗${NC} Missing dependencies: ${MISSING_DEPS[*]}"
    echo "Please install them first with:"
    echo "brew install ${MISSING_DEPS[*]}"
    exit 1
else
    echo -e "${GREEN}✓${NC} All dependencies installed"
fi

echo ""
echo "Step 2: Cleaning previous build..."
if [ -f "Makefile" ]; then
    make clean || true
fi

echo ""
echo "Step 3: Checking for configure script and Makefile.in..."
if [ ! -f "configure" ] || [ ! -f "Makefile.in" ]; then
    echo "Running autogen.sh to generate build files..."
    ./autogen.sh
else
    echo -e "${GREEN}✓${NC} Configure script and Makefile.in exist"
fi

echo ""
echo "Step 4: Configuring with Rust support..."

# Set environment variables for dependencies
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
export CPPFLAGS="-I/opt/homebrew/include"
export LDFLAGS="-L/opt/homebrew/lib"

./configure \
    --enable-geoip

echo ""
echo "Step 5: Building Suricata (this may take 10-15 minutes)..."
CPU_COUNT=$(sysctl -n hw.ncpu)
echo "Using $CPU_COUNT CPU cores for parallel build..."
make -j$CPU_COUNT

echo ""
echo "Step 6: Verifying build..."
if [ -f "src/suricata" ]; then
    echo -e "${GREEN}✓${NC} Suricata binary created successfully"
    
    # Check for Rust support
    if ./src/suricata --build-info | grep -q "Rust support.*yes"; then
        echo -e "${GREEN}✓${NC} Rust support enabled"
    else
        echo -e "${RED}✗${NC} Rust support not enabled"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Build failed - binary not found"
    exit 1
fi

echo ""
echo "Step 7: Creating log directory..."
mkdir -p logs
echo -e "${GREEN}✓${NC} Log directory created"

echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "Suricata is ready to use. To start monitoring:"
echo "  sudo ./src/suricata -c suricata.yaml -i en0 -l logs -v"
echo ""
echo "Or use the monitor-network.sh script:"
echo "  sudo ./monitor-network.sh"
echo ""


