#!/bin/bash

echo "🔨 Rebuilding Suricata with PQC Classification Fix..."
echo ""

# Rebuild Rust library
echo "1️⃣ Building Rust library..."
cd rust && cargo build --release 2>&1 | tail -5
cd ..

# Rebuild Suricata
echo ""
echo "2️⃣ Building Suricata..."
make -j$(sysctl -n hw.ncpu) 2>&1 | tail -10

# Check binary timestamp
echo ""
echo "3️⃣ Binary info:"
ls -lh src/suricata | awk '{print "   Size: " $5 "  Modified: " $6 " " $7 " " $8}'

echo ""
echo "✅ Build complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "To install and restart (requires sudo):"
echo "  sudo make install"
echo "  sudo pkill -9 suricata"
echo "  sudo src/suricata -c ./suricata.yaml -i en0 -v"
echo ""
echo "Or run from source directory:"
echo "  sudo pkill -9 suricata"
echo "  sudo src/suricata -c ./suricata.yaml -i en0 -v"
echo ""