#!/bin/bash

# Verification Script - Check all components are properly configured
# Run this after setup to ensure system is ready

set -e

echo "========================================"
echo "  Bitcoin Volatility System Verification"
echo "========================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# Function to check and print result
check() {
    local test_name=$1
    local command=$2
    
    echo -n "Checking $test_name... "
    
    if eval "$command" &>/dev/null; then
        echo "✓ PASS"
        ((PASS_COUNT++))
    else
        echo "✗ FAIL"
        ((FAIL_COUNT++))
    fi
}

# 1. Docker Containers
echo "[1/10] Docker Containers"
check "  namenode" "docker ps | grep namenode | grep -q Up"
check "  datanode" "docker ps | grep datanode | grep -q Up"
check "  zookeeper" "docker ps | grep zookeeper | grep -q Up"
check "  kafka" "docker ps | grep kafka | grep -q Up"
check "  spark-master" "docker ps | grep spark-master | grep -q Up"
check "  spark-worker" "docker ps | grep spark-worker | grep -q Up"
echo ""

# 2. HDFS
echo "[2/10] HDFS Directories"
check "  /bitcoin" "docker exec namenode hdfs dfs -test -d /bitcoin"
check "  /bitcoin/historical" "docker exec namenode hdfs dfs -test -d /bitcoin/historical"
check "  /bitcoin/checkpoints" "docker exec namenode hdfs dfs -test -d /bitcoin/checkpoints"
check "  /bitcoin/analysis" "docker exec namenode hdfs dfs -test -d /bitcoin/analysis"
echo ""

# 3. Kafka
echo "[3/10] Kafka Topics"
check "  bitcoin-prices topic" "docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list | grep -q bitcoin-prices"
echo ""

# 4. Configuration
echo "[4/10] Configuration Files"
check "  config.yaml exists" "[ -f config/config.yaml ]"
check "  API key set" "! grep -q 'YOUR_API_KEY_HERE' config/config.yaml"
echo ""

# 5. Spark JAR
echo "[5/10] Spark Build"
check "  JAR exists" "[ -f spark-jobs/target/scala-2.12/bitcoin-volatility-assembly-1.0.jar ]"
echo ""

# 6. Python Dependencies
echo "[6/10] Python Dependencies"
check "  kafka-python" "python -c 'import kafka' 2>/dev/null"
check "  requests" "python -c 'import requests' 2>/dev/null"
check "  PyYAML" "python -c 'import yaml' 2>/dev/null"
check "  pandas" "python -c 'import pandas' 2>/dev/null"
check "  dash" "python -c 'import dash' 2>/dev/null"
check "  plotly" "python -c 'import plotly' 2>/dev/null"
echo ""

# 7. Data Directories
echo "[7/10] Data Directories"
check "  data/namenode" "[ -d data/namenode ]"
check "  data/datanode" "[ -d data/datanode ]"
check "  data/kafka" "[ -d data/kafka ]"
echo ""

# 8. Web UIs (check ports)
echo "[8/10] Web UI Ports"
check "  Hadoop (9870)" "curl -s http://localhost:9870 >/dev/null"
check "  Spark (8080)" "curl -s http://localhost:8080 >/dev/null"
echo ""

# 9. HDFS Data (if historical data downloaded)
echo "[9/10] Historical Data (Optional)"
if docker exec namenode hdfs dfs -test -d /bitcoin/historical &>/dev/null; then
    SIZE=$(docker exec namenode hdfs dfs -du -s /bitcoin/historical | awk '{print $1}')
    SIZE_GB=$(echo "scale=2; $SIZE / 1024 / 1024 / 1024" | bc)
    echo "  Historical data size: ${SIZE_GB} GB"
    
    if (( $(echo "$SIZE_GB >= 3.0" | bc -l) )); then
        echo "  ✓ PASS (>= 3 GB)"
        ((PASS_COUNT++))
    else
        echo "  ⚠ WARNING (< 3 GB) - Run scripts/download_historical_data.py"
    fi
else
    echo "  ⚠ No historical data yet - Run scripts/download_historical_data.py"
fi
echo ""

# 10. Prerequisites
echo "[10/10] Command-Line Tools"
check "  docker" "which docker"
check "  java" "which java"
check "  scala" "which scala"
check "  sbt" "which sbt"
check "  python" "which python"
echo ""

# Summary
echo "========================================"
echo "  Summary"
echo "========================================"
echo ""
echo "Tests Passed: $PASS_COUNT"
echo "Tests Failed: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo "✓ All checks passed! System is ready."
    echo ""
    echo "Next steps:"
    echo "  1. Ensure API key is set in config/config.yaml"
    echo "  2. Download historical data (optional): python scripts/download_historical_data.py"
    echo "  3. Start the system: see QUICKSTART.md or USAGE.md"
    exit 0
else
    echo "✗ Some checks failed. Please review the output above."
    echo "See docs/SETUP.md for troubleshooting guidance."
    exit 1
fi
