#!/bin/bash

# Start Spark Streaming Job
# This script submits the VolatilityStream job to Spark

set -e

# Resolve project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================"
echo "  Starting Spark Streaming Job"
echo "========================================"
echo ""

# Configuration
JAR_PATH="$PROJECT_ROOT/spark-jobs/target/scala-2.12/bitcoin-volatility-assembly-1.0.jar"
CONFIG_PATH="$PROJECT_ROOT/config/config.yaml"
MAIN_CLASS="VolatilityStream"

# Check if JAR exists
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: JAR file not found at $JAR_PATH"
    echo "Please run: cd spark-jobs && sbt assembly"
    exit 1
fi

echo "✓ JAR found: $JAR_PATH"
echo "✓ Config: $CONFIG_PATH"
echo "✓ Main class: $MAIN_CLASS"
echo ""

# Submit to Spark
echo "Submitting job to Spark..."
echo ""

MSYS_NO_PATHCONV=1 docker exec spark-master /opt/spark/bin/spark-submit \
  --class $MAIN_CLASS \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --driver-memory 4g \
  --executor-memory 2g \
  --total-executor-cores 2 \
  --conf spark.driver.host=spark-master \
  --conf spark.driver.bindAddress=0.0.0.0 \
  --conf spark.ui.enabled=true \
  --conf spark.ui.port=4050 \
  --conf spark.driver.extraJavaOptions="-Dspark.ui.showConsoleProgress=true" \
  /opt/spark-jobs/bitcoin-volatility-assembly-1.0.jar \
  /opt/spark-config/config.yaml

echo ""
echo "Streaming job stopped."
