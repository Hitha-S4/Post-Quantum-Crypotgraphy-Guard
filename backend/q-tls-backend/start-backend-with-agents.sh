#!/bin/bash

# Start Backend with Modern Agent Support
# This script uses the ACTUAL venv location

set -e

echo "🚀 Starting Backend with Modern Agent System..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Use the current workspace venv (where we installed langchain)
VENV_PYTHON="./venv/bin/python"

# Kill any existing backend processes
echo "1. Stopping existing backend processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Verify langchain is installed
echo "2. Verifying dependencies..."
if $VENV_PYTHON -c "import langchain_core" 2>/dev/null; then
    echo "   ✅ langchain_core found"
    echo "   Using Python: $VENV_PYTHON"
else
    echo "   ❌ langchain_core not found in either location"
    echo "   Please run: ./install-agent-deps.sh"
    exit 1
fi

# Start the backend
echo "3. Starting backend server..."
echo ""
PYTHONPATH=src $VENV_PYTHON -m uvicorn src.ngfw_pqc_detector.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload

# Made with Bob
