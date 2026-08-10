#!/bin/bash

# Test script to monitor Kafka messages and WebSocket transformations
# Shows side-by-side comparison of incoming and transformed messages

echo "=================================================="
echo "  Kafka → WebSocket Transformation Monitor"
echo "=================================================="
echo ""

# Check if required Python packages are installed
echo "Checking dependencies..."

# Function to install package with proper flags
install_package() {
    local package=$1
    echo "⚠️  $package not found. Installing..."
    
    # Try installing with --user flag (safer for system Python)
    if pip3 install --user "$package" 2>/dev/null; then
        echo "✓ Installed $package with --user flag"
    elif pip3 install "$package" 2>/dev/null; then
        echo "✓ Installed $package"
    else
        echo "❌ Failed to install $package"
        echo ""
        echo "   Installation failed due to PEP 668 restrictions."
        echo "   Please choose one of these options:"
        echo ""
        echo "   Option 1 (Recommended): Create a virtual environment"
        echo "     python3 -m venv venv"
        echo "     source venv/bin/activate"
        echo "     pip install $package"
        echo ""
        echo "   Option 2: Install to user directory"
        echo "     pip3 install --user $package"
        echo ""
        echo "   Option 3: Override system protection (not recommended)"
        echo "     pip3 install --break-system-packages $package"
        echo ""
        echo "   See INSTALL_KAFKA_PYTHON.md for detailed instructions"
        return 1
    fi
}

# Check and install kafka-python
if ! python3 -c "import kafka" 2>/dev/null; then
    install_package "kafka-python" || exit 1
fi

# Check and install websockets
if ! python3 -c "import websockets" 2>/dev/null; then
    install_package "websockets" || exit 1
fi

# Check and install colorama
if ! python3 -c "import colorama" 2>/dev/null; then
    install_package "colorama" || exit 1
fi

echo "✓ All dependencies installed"
echo ""

# Make the Python script executable
chmod +x test_kafka_websocket_transformation.py

# Run the monitor
echo "Starting monitor..."
echo "Press Ctrl+C to stop"
echo ""

python3 test_kafka_websocket_transformation.py