#!/bin/bash
# Inspect Kafka messages for TLS data

# Make the Python script executable
chmod +x "$(dirname "$0")/inspect_kafka_messages.py"

# Run the inspection script
python3 "$(dirname "$0")/inspect_kafka_messages.py" "$@"