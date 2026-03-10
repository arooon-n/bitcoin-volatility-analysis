#!/bin/bash

# Bitcoin Volatility Analysis - Kafka Setup Script
# This script creates required Kafka topics for the project
# It is idempotent - safe to run multiple times

set -e  # Exit immediately if any command fails

echo "========================================"
echo "  Kafka Topic Setup"
echo "========================================"
echo ""

# Kafka configuration
BOOTSTRAP_SERVER="localhost:9092"
TOPIC_NAME="bitcoin-prices"
PARTITIONS=3          # 3 partitions for parallelism while keeping resource usage low
REPLICATION_FACTOR=1  # Replication factor 1 (single broker setup)

# Check if Kafka is reachable
echo "[1/3] Checking Kafka connectivity..."
if ! docker exec kafka kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVER --list &>/dev/null; then
    echo "ERROR: Kafka broker is not accessible at $BOOTSTRAP_SERVER"
    echo "Please ensure Docker containers are running: docker-compose up -d"
    echo "Wait 30 seconds after starting for Kafka to be ready."
    exit 1
fi
echo "✓ Kafka broker is reachable"
echo ""

# Create topic
echo "[2/3] Creating Kafka topic: $TOPIC_NAME"
echo "Configuration:"
echo "  - Partitions: $PARTITIONS (allows parallel processing by multiple consumers)"
echo "  - Replication Factor: $REPLICATION_FACTOR (single broker, no replication)"
echo ""

# Use --if-not-exists flag to make script idempotent
docker exec kafka kafka-topics.sh \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --create \
    --if-not-exists \
    --topic $TOPIC_NAME \
    --partitions $PARTITIONS \
    --replication-factor $REPLICATION_FACTOR

echo "✓ Topic created successfully"
echo ""

# Verify topic creation
echo "[3/3] Verifying topic creation..."
echo ""
echo "Available Kafka topics:"
docker exec kafka kafka-topics.sh --bootstrap-server $BOOTSTRAP_SERVER --list
echo ""

# Display topic details
echo "Topic details:"
docker exec kafka kafka-topics.sh \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --describe \
    --topic $TOPIC_NAME
echo ""

# Print success banner
echo "========================================"
echo "  ✓ Kafka Setup Complete!"
echo "========================================"
echo ""
echo "Topic '$TOPIC_NAME' is ready to receive data."
echo ""
echo "To monitor messages in real-time, run:"
echo "  docker exec kafka kafka-console-consumer.sh \\"
echo "    --bootstrap-server $BOOTSTRAP_SERVER \\"
echo "    --topic $TOPIC_NAME \\"
echo "    --from-beginning"
echo ""
echo "Next step: python scripts/download_historical_data.py"
echo ""
