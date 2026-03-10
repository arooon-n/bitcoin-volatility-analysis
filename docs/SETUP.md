# Setup Guide - Bitcoin Volatility Analysis System

This document provides detailed, step-by-step instructions for setting up the Bitcoin Volatility Analysis system from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [API Key Setup](#api-key-setup)
3. [Installation Steps](#installation-steps)
4. [Verification](#verification)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software           | Version           | Download Link                                   | Purpose                    |
| ------------------ | ----------------- | ----------------------------------------------- | -------------------------- |
| **Docker Desktop** | Latest            | https://www.docker.com/products/docker-desktop/ | Container orchestration    |
| **Java (JDK)**     | 17                | https://adoptium.net/                           | Scala/Spark runtime        |
| **Scala**          | 2.13.14           | https://www.scala-lang.org/download/            | Spark job language         |
| **sbt**            | 1.12.0            | https://www.scala-sbt.org/download.html         | Scala build tool           |
| **Python**         | 3.11.x            | https://www.python.org/downloads/               | Producer & dashboard       |
| **Git**            | Latest            | https://git-scm.com/downloads                   | Version control            |
| **Git Bash**       | Included with Git | —                                               | Run .sh scripts on Windows |

### System Requirements

- **OS**: Windows 11 (configured for D:\ drive)
- **RAM**: Minimum 8 GB (16 GB recommended, configured to use 4-6 GB)
- **Disk Space**:
  - C:\ drive: 10 GB (for Docker, Python, Java installations)
  - D:\ drive: 15+ GB (for project data, HDFS, Kafka logs)
- **Network**: Stable internet connection for API calls and downloads

### Verify Installations

Open PowerShell/Command Prompt and verify each tool:

```bash
# Docker
docker --version
# Expected: Docker version 24.x.x or higher

# Docker Compose
docker-compose --version
# Expected: Docker Compose version v2.x.x or higher

# Java
java -version
# Expected: openjdk version "17.x.x"

# Scala
scala -version
# Expected: Scala code runner version 2.13.14

# sbt
sbt --version
# Expected: sbt version 1.12.0

# Python
python --version
# Expected: Python 3.11.x

# Git Bash (open Git Bash and run)
bash --version
# Expected: GNU bash, version 4.x.x or higher
```

---

## API Key Setup

### Step 1: Create CryptoCompare Account

1. Visit: https://www.cryptocompare.com/
2. Click **"Sign Up"** (top right)
3. Fill in your details:
   - Email address
   - Password
   - Accept terms
4. Verify your email address (check inbox)

### Step 2: Generate API Key

1. Log in to CryptoCompare
2. Navigate to: https://www.cryptocompare.com/cryptopian/api-keys
3. Click **"Create New API Key"**
4. Name it: `Bitcoin-Volatility-Project`
5. Click **"Create"**
6. **Copy the API key** (you'll need it in next step)

### Step 3: Configure API Key

1. Open the project configuration file:

   ```bash
   notepad d:\College\Sem6\BigData\bitcoin003\config\config.yaml
   ```

2. Find this line:

   ```yaml
   key: "YOUR_API_KEY_HERE"
   ```

3. Replace `YOUR_API_KEY_HERE` with your actual API key:

   ```yaml
   key: "a1b2c3d4e5f6g7h8i9j0" # Example format
   ```

4. Save and close the file

**IMPORTANT**: Keep your API key private. Do not commit it to version control.

---

## Installation Steps

### Step 1: Clone or Download Project

If you haven't already, ensure the project is at:

```
d:\College\Sem6\BigData\bitcoin003\
```

Open Git Bash in this directory for all subsequent commands.

### Step 2: Create Data Directories

Create directories for Docker persistent volumes:

```bash
bash scripts/create_data_dirs.sh
```

**Expected output:**

```
========================================
  Creating Data Directories
========================================

✓ Created: d:/College/Sem6/BigData/bitcoin003/data/namenode
✓ Created: d:/College/Sem6/BigData/bitcoin003/data/datanode
✓ Created: d:/College/Sem6/BigData/bitcoin003/data/kafka

✓ Data directories ready
```

### Step 3: Start Docker Infrastructure

Start all Docker containers (Hadoop, Kafka, Spark):

```bash
docker-compose up -d
```

**Expected output:**

```
Creating network "bitcoin003_bitcoin-net" with driver "bridge"
Creating zookeeper ... done
Creating namenode  ... done
Creating datanode  ... done
Creating kafka     ... done
Creating spark-master ... done
Creating spark-worker ... done
```

**Wait 60 seconds** for all services to initialize.

Verify all containers are running:

```bash
docker ps
```

You should see 6 containers running:

- `namenode`
- `datanode`
- `zookeeper`
- `kafka`
- `spark-master`
- `spark-worker`

### Step 4: Setup HDFS Directories

Create required HDFS directory structure:

```bash
bash scripts/setup_hdfs.sh
```

**Expected output:**

```
========================================
  HDFS Directory Setup
========================================

[1/5] Checking HDFS connectivity...
✓ HDFS is reachable

[2/5] Creating main /bitcoin directory...
✓ Created /bitcoin

[3/5] Creating subdirectories...
✓ Created all subdirectories

[4/5] Setting permissions...
✓ Permissions set to 777 (development mode)

[5/5] Verifying directory structure...

drwxrwxrwx - root supergroup /bitcoin
drwxrwxrwx - root supergroup /bitcoin/analysis
drwxrwxrwx - root supergroup /bitcoin/checkpoints
drwxrwxrwx - root supergroup /bitcoin/checkpoints/latest
drwxrwxrwx - root supergroup /bitcoin/checkpoints/stream
drwxrwxrwx - root supergroup /bitcoin/historical

========================================
  ✓ HDFS Setup Complete!
========================================
```

### Step 5: Setup Kafka Topics

Create Kafka topic for Bitcoin price data:

```bash
bash scripts/setup_kafka.sh
```

**Expected output:**

```
========================================
  Kafka Topic Setup
========================================

[1/3] Checking Kafka connectivity...
✓ Kafka broker is reachable

[2/3] Creating Kafka topic: bitcoin-prices
Configuration:
  - Partitions: 3 (allows parallel processing)
  - Replication Factor: 1 (single broker)

Created topic bitcoin-prices.
✓ Topic created successfully

[3/3] Verifying topic creation...

Available Kafka topics:
bitcoin-prices

Topic details:
Topic: bitcoin-prices   PartitionCount: 3   ReplicationFactor: 1
```

### Step 6: Download Historical Data

Install Python dependencies for the download script:

```bash
pip install -r scripts/requirements.txt
```

Run the historical data downloader (**This will take 10-20 minutes**):

```bash
python scripts/download_historical_data.py
```

**Expected output (abbreviated):**

```
============================================================
  Bitcoin Volatility Analysis
  Historical Data Download
============================================================

✓ Temporary directory: /tmp/bitcoin_historical
✓ HDFS target: hdfs://namenode:8020/bitcoin/historical

============================================================
  PHASE 1: DATA DOWNLOAD
============================================================

[DOWNLOAD] Fetching 90 days of minute data for BTC...
  Progress: 100.0% (129600 records)
✓ Downloaded 129600 minute records for BTC

[DOWNLOAD] Fetching 1095 days (3 years) of hourly data for BTC...
  Progress: 100.0% (26280 records)
✓ Downloaded 26280 hourly records for BTC

... (ETH and LTC downloads)

============================================================
  PHASE 2: SAVE TO PARQUET
============================================================

✓ Saved to /tmp/bitcoin_historical/btc_minute_90d.parquet (245.67 MB)
...

============================================================
  PHASE 3: UPLOAD TO HDFS
============================================================

[UPLOAD] Uploading btc_minute_90d.parquet to HDFS...
✓ Upload complete. HDFS size: 245.67 M
...

============================================================
  PHASE 4: VERIFICATION
============================================================

Total HDFS data size: 3.2 G (3.234 GB)

✓ SUCCESS: Data size (3.234 GB) meets the 3 GB requirement!

============================================================
  ✓ HISTORICAL DATA DOWNLOAD COMPLETE
============================================================
```

### Step 7: Build Spark Jobs

Compile Scala code and create a fat JAR:

```bash
cd spark-jobs
sbt assembly
cd ..
```

**This will take 3-5 minutes on first run** (downloads dependencies).

**Expected output (abbreviated):**

```
[info] welcome to sbt 1.12.0
[info] loading project definition from ...
[info] loading settings for project bitcoin-volatility from build.sbt ...
[info] compiling 2 Scala sources to ...
[info] Strategy 'discard' was applied to a file (Run the task at debug level to see details)
[success] Total time: 127 s, completed ...
```

JAR location: `spark-jobs/target/scala-2.13/bitcoin-volatility-assembly-1.0.jar`

### Step 8: Install Python Dependencies

Install dependencies for Kafka producer:

```bash
cd kafka-producer
pip install -r requirements.txt
cd ..
```

Install dependencies for dashboard:

```bash
cd dashboard
pip install -r requirements.txt
cd ..
```

**Expected output:**

```
Successfully installed kafka-python-2.0.2 requests-2.31.0 PyYAML-6.0.1
Successfully installed dash-2.14.2 plotly-5.17.0 pandas-2.0.3 ...
```

---

## Verification

### Verification Checklist

Run these checks to ensure everything is set up correctly:

#### 1. Docker Containers

```bash
docker ps
```

✅ All 6 containers should show "Up" status

#### 2. HDFS Directories

```bash
docker exec namenode hdfs dfs -ls -R /bitcoin
```

✅ Should show 5 directories: `/bitcoin`, `/bitcoin/historical`, `/bitcoin/checkpoints/stream`, `/bitcoin/checkpoints/latest`, `/bitcoin/analysis`

#### 3. HDFS Data Size

```bash
docker exec namenode hdfs dfs -du -s -h /bitcoin/historical
```

✅ Should show ≥ 3 GB (e.g., "3.2 G")

#### 4. Kafka Topics

```bash
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list
```

✅ Should show `bitcoin-prices`

#### 5. Spark JAR

```bash
ls -lh spark-jobs/target/scala-2.13/bitcoin-volatility-assembly-1.0.jar
```

✅ File should exist and be ~50-100 MB

#### 6. Configuration File

```bash
grep "YOUR_API_KEY_HERE" config/config.yaml
```

❌ Should return nothing (key is replaced)  
✅ If you see "YOUR_API_KEY_HERE", you haven't set your API key yet

#### 7. Web UIs (Open in Browser)

| Service         | URL                   | Expected               |
| --------------- | --------------------- | ---------------------- |
| Hadoop NameNode | http://localhost:9870 | HDFS overview page     |
| Hadoop DataNode | http://localhost:9864 | DataNode info page     |
| Spark Master    | http://localhost:8080 | Spark cluster overview |

---

## Troubleshooting

### Issue: Docker containers not starting

**Symptoms:**

```
Error: Cannot connect to the Docker daemon
```

**Solutions:**

1. Ensure Docker Desktop is running
2. In Docker Desktop settings, enable WSL 2 integration (Windows)
3. Restart Docker Desktop
4. Try again: `docker-compose up -d`

---

### Issue: HDFS not accessible

**Symptoms:**

```
ERROR: HDFS namenode is not accessible
```

**Solutions:**

1. Wait 60 seconds after `docker-compose up -d`
2. Check namenode logs:
   ```bash
   docker logs namenode
   ```
3. Restart namenode if needed:
   ```bash
   docker-compose restart namenode
   ```
4. If persists, remove volumes and restart:
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

---

### Issue: Kafka connection refused

**Symptoms:**

```
kafka.errors.NoBrokersAvailable: NoBrokersAvailable
```

**Solutions:**

1. Ensure Zookeeper is running:
   ```bash
   docker logs zookeeper
   ```
2. Check Kafka logs:
   ```bash
   docker logs kafka
   ```
3. Wait 30-60 seconds after starting containers
4. Verify Kafka is listening:
   ```bash
   docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list
   ```

---

### Issue: Historical data download fails

**Symptoms:**

```
ERROR: API returned error: Rate limit exceeded
```

**Solutions:**

1. **API Key**: Ensure you've set your CryptoCompare API key in `config/config.yaml`
2. **Rate Limit**: Free tier has limits. Wait 1 hour and retry.
3. **Network**: Check internet connection
4. **Partial Download**: If you have some data in HDFS, you can proceed (may be < 3 GB)

---

### Issue: sbt assembly fails

**Symptoms:**

```
[error] (compile / compileIncremental) Compilation failed
```

**Solutions:**

1. Ensure Scala 2.13.14 is installed:
   ```bash
   scala -version
   ```
2. Check Java version (must be 17):
   ```bash
   java -version
   ```
3. Clean and retry:
   ```bash
   cd spark-jobs
   sbt clean
   sbt assembly
   ```
4. If dependency download fails, check internet connection

---

### Issue: Out of memory errors

**Symptoms:**

```
java.lang.OutOfMemoryError: Java heap space
```

**Solutions:**

1. Edit `config/config.yaml`:
   ```yaml
   spark:
     driver_memory: "2g" # Reduce from 4g
     executor_memory: "1g" # Reduce from 2g
   ```
2. Edit `docker-compose.yaml` - reduce `mem_limit` values:
   ```yaml
   spark-master:
     mem_limit: 512m # Reduce from 1g
   spark-worker:
     mem_limit: 1500m # Reduce from 2500m
   ```
3. Close other applications to free RAM
4. Restart Docker: `docker-compose down && docker-compose up -d`

---

### Issue: Permission denied on .sh scripts

**Symptoms:**

```
bash: ./script.sh: Permission denied
```

**Solutions:**

1. **Use Git Bash** instead of PowerShell/CMD
2. Or make executable:
   ```bash
   chmod +x scripts/*.sh
   ```
3. Or run with `bash` prefix:
   ```bash
   bash scripts/setup_hdfs.sh
   ```

---

## Next Steps

After successful setup, proceed to:

- **[USAGE.md](USAGE.md)** - Learn how to run the system
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Understand system design

---

## Setup Summary (Copy-Paste Quick Reference)

For a fresh system:

```bash
# 1. Configure API key
notepad config/config.yaml  # Replace YOUR_API_KEY_HERE

# 2. Create directories
bash scripts/create_data_dirs.sh

# 3. Start Docker
docker-compose up -d
# Wait 60 seconds

# 4. Setup HDFS
bash scripts/setup_hdfs.sh

# 5. Setup Kafka
bash scripts/setup_kafka.sh

# 6. Download data (10-20 min)
pip install -r scripts/requirements.txt
python scripts/download_historical_data.py

# 7. Build Spark jobs (3-5 min)
cd spark-jobs && sbt assembly && cd ..

# 8. Install Python deps
pip install -r kafka-producer/requirements.txt
pip install -r dashboard/requirements.txt

# DONE! Proceed to USAGE.md
```

---

**Setup Complete! ✅**

You're now ready to run the Bitcoin Volatility Analysis pipeline.
