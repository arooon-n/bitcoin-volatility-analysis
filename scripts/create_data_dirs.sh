#!/bin/bash

# Create data directories for Docker volumes
# This script must be run before docker-compose up

set -e

echo "========================================"
echo "  Creating Data Directories"
echo "========================================"
echo ""

BASE_DIR="d:/College/Sem6/BigData/bitcoin003/data"

mkdir -p "$BASE_DIR/namenode"
mkdir -p "$BASE_DIR/datanode"
mkdir -p "$BASE_DIR/kafka"

echo "✓ Created: $BASE_DIR/namenode"
echo "✓ Created: $BASE_DIR/datanode"
echo "✓ Created: $BASE_DIR/kafka"

echo ""
echo "✓ Data directories ready"
echo ""
echo "Next step: docker-compose up -d"
echo ""
