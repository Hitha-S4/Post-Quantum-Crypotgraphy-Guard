#!/bin/bash

# Installation script for NGFW PQC Detector
# This script installs dependencies from PyPI

echo "Installing NGFW PQC Detector dependencies..."

# Install most dependencies from your configured index
echo "Installing core dependencies..."
pip install fastapi>=0.115.0
pip install uvicorn[standard]>=0.32.0
pip install pydantic>=2.9.0
pip install pydantic-settings>=2.6.0
pip install kafka-python>=2.0.2
pip install scapy>=2.6.0
pip install cryptography>=44.0.0
pip install python-dotenv>=1.0.1
pip install httpx>=0.28.0

# Install MongoDB packages from global PyPI
echo "Installing MongoDB packages from PyPI..."
pip install --index-url https://pypi.org/simple/ motor>=3.3.0
pip install --index-url https://pypi.org/simple/ pymongo>=4.6.0

echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.sample to .env: cp .env.sample .env"
echo "2. Update .env with your configuration"
echo "3. Run the server: python -m ngfw_pqc_detector.main"