#!/bin/bash

# Bitcoin Volatility Analysis - HDFS Setup Script
# This script creates all required HDFS directories for the project
# It is idempotent - safe to run multiple times

set -e  # Exit immediately if any command fails

echo "========================================"
echo "  HDFS Directory Setup"
echo "========================================"
echo ""

# Check if HDFS is reachable
echo "[1/5] Checking HDFS connectivity..."
if ! docker exec namenode hdfs dfs -ls / &>/dev/null; then
    echo "ERROR: HDFS namenode is not accessible."
    echo "Please ensure Docker containers are running: docker-compose up -d"
    exit 1
fi
echo "✓ HDFS is reachable"
echo ""

# Create main bitcoin directory
echo "[2/5] Creating main /bitcoin directory..."
docker exec namenode hdfs dfs -mkdir -p /bitcoin
echo "✓ Created /bitcoin"
echo ""

# Create subdirectories
echo "[3/5] Creating subdirectories..."
docker exec namenode hdfs dfs -mkdir -p /bitcoin/historical
docker exec namenode hdfs dfs -mkdir -p /bitcoin/checkpoints
docker exec namenode hdfs dfs -mkdir -p /bitcoin/checkpoints/stream
docker exec namenode hdfs dfs -mkdir -p /bitcoin/checkpoints/latest
docker exec namenode hdfs dfs -mkdir -p /bitcoin/analysis
echo "✓ Created all subdirectories"
echo ""

# Set permissions (777 for development - use appropriate permissions in production)
echo "[4/5] Setting permissions..."
docker exec namenode hdfs dfs -chmod -R 777 /bitcoin
echo "✓ Permissions set to 777 (development mode)"
echo ""

# Verify directory structure
echo "[5/5] Verifying directory structure..."
echo ""
docker exec namenode hdfs dfs -ls -R /bitcoin
echo ""

# Print success banner
echo "========================================"
echo "  ✓ HDFS Setup Complete!"
echo "========================================"
echo ""
echo "Directory structure created:"
echo "  /bitcoin"
echo "  ├── historical          (bulk historical data)"
echo "  ├── checkpoints"
echo "  │   ├── stream         (streaming job checkpoints)"
echo "  │   └── latest         (latest data checkpoints)"
echo "  └── analysis           (batch analysis output)"
echo ""
echo "Next step: Run scripts/setup_kafka.sh"
echo ""
