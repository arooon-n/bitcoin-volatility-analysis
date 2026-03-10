# Usage Guide - Bitcoin Volatility Analysis System

This document provides step-by-step instructions for running the Bitcoin Volatility Analysis pipeline and interpreting results.

## Table of Contents

1. [Starting the Pipeline](#starting-the-pipeline)
2. [Monitoring Operations](#monitoring-operations)
3. [Running Batch Analysis](#running-batch-analysis)
4. [Dashboard Usage](#dashboard-usage)
5. [Data Exploration](#data-exploration)
6. [Stopping the System](#stopping-the-system)
7. [Demo Script](#demo-script)

---

## Starting the Pipeline

### Prerequisites

Before starting, ensure:

- ✅ Docker containers are running: `docker ps` (should show 6 containers)
- ✅ HDFS directories created: See [SETUP.md](SETUP.md)
- ✅ Kafka topics created: See [SETUP.md](SETUP.md)
- ✅ Historical data uploaded: `docker exec namenode hdfs dfs -du -s -h /bitcoin/historical` shows 3+ GB
- ✅ Spark JAR compiled: `spark-jobs/target/scala-2.13/bitcoin-volatility-assembly-1.0.jar` exists

---

### Step 1: Start Kafka Producer

The producer fetches Bitcoin price data from CryptoCompare API and publishes to Kafka.

**Open Terminal 1** (Git Bash):

```bash
cd d:/College/Sem6/BigData/bitcoin003/kafka-producer
python producer.py
```

**Expected Output:**

```
============================================================
  Bitcoin Kafka Producer Initialized
============================================================
API Base URL: https://min-api.cryptocompare.com
Kafka Broker: localhost:9092
Kafka Topic: bitcoin-prices
Fetch Interval: 10 seconds
============================================================

Starting data collection... (Press Ctrl+C to stop)

2024-03-15 10:15:00 — INFO — ✓ Sent to Kafka — Price: $67,890.12 | Volume24h: $1,234,567,890 | Partition: 0 | Offset: 42
2024-03-15 10:15:10 — INFO — ✓ Sent to Kafka — Price: $67,895.45 | Volume24h: $1,234,589,123 | Partition: 1 | Offset: 38
2024-03-15 10:15:20 — INFO — ✓ Sent to Kafka — Price: $67,901.78 | Volume24h: $1,234,612,456 | Partition: 2 | Offset: 41
...
```

**What to look for:**

- ✅ "Kafka producer created successfully"
- ✅ Messages being sent every 10 seconds
- ✅ Price and volume values look reasonable
- ✅ Partition and offset numbers incrementing

**To verify Kafka messages:**

```bash
# In another terminal
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic bitcoin-prices \
  --from-beginning \
  --max-messages 5
```

**Expected:** 5 JSON messages printed to console.

**Leave this terminal running.** Press Ctrl+C to stop when needed.

---

### Step 2: Start Spark Streaming

The streaming job reads from Kafka, computes volatility, and writes to HDFS + local disk.

**Open Terminal 2** (Git Bash):

```bash
cd d:/College/Sem6/BigData/bitcoin003
bash scripts/start_streaming.sh
```

**Expected Output:**

```
========================================
  Starting Spark Streaming Job
========================================

✓ JAR found: ../spark-jobs/target/scala-2.13/bitcoin-volatility-assembly-1.0.jar
✓ Config: ../config/config.yaml
✓ Main class: VolatilityStream

Submitting job to Spark...

============================================================
  Bitcoin Volatility Stream Processing
============================================================

Loading configuration from: ../config/config.yaml
✓ Kafka Bootstrap Servers: localhost:9092
✓ Kafka Topic: bitcoin-prices
✓ HDFS Namenode: hdfs://namenode:8020
✓ Local Data Path: /tmp/bitcoin_latest

✓ Spark Session created

Connecting to Kafka stream...
✓ Connected to Kafka stream

Computing volatility metrics...
✓ Volatility metrics configured

Starting HDFS sink (Parquet)...
✓ HDFS sink started: hdfs://namenode:8020/bitcoin/historical

Starting local JSON sink for dashboard...
✓ Local sink started: /tmp/bitcoin_latest

============================================================
  Streaming Pipeline Active
============================================================
HDFS Output:
  Path: hdfs://namenode:8020/bitcoin/historical
  Format: Parquet (partitioned by date)
  Trigger: 30 seconds

Dashboard Output:
  Path: /tmp/bitcoin_latest
  Format: JSON
  Trigger: 10 seconds

Metrics computed:
  • Log returns
  • 1-hour rolling volatility
  • 24-hour rolling volatility
  • 1-hour price moving average
  • 24-hour price moving average

Press Ctrl+C to stop the stream
============================================================
```

**What to look for:**

- ✅ "Connected to Kafka stream"
- ✅ Both sinks started (HDFS and local)
- ✅ No errors about missing JAR or connection failures

**To verify streaming is working:**

```bash
# Check HDFS (wait 30 seconds after start)
docker exec namenode hdfs dfs -ls /bitcoin/historical

# Expected: date=YYYY-MM-DD directories appearing

# Check local files (wait 10 seconds after start)
ls /tmp/bitcoin_latest/

# Expected: .json files appearing
```

**Leave this terminal running.** The streaming job runs indefinitely until stopped.

---

### Step 3: Start Dashboard

The dashboard visualizes real-time price and volatility data.

**Open Terminal 3** (Git Bash):

```bash
cd d:/College/Sem6/BigData/bitcoin003/dashboard
python app.py
```

**Expected Output:**

```
============================================================
  Bitcoin Volatility Dashboard
============================================================
Server starting on http://0.0.0.0:8050
Data source: /tmp/bitcoin_latest
Auto-refresh: every 10.0 seconds
============================================================

Open your browser and navigate to:
  http://localhost:8050

Press Ctrl+C to stop the server

Dash is running on http://0.0.0.0:8050/

 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use in production.

2024-03-15 10:20:45 — INFO — Loaded 15 records. Latest: 2024-03-15 10:20:40
2024-03-15 10:20:55 — INFO — Loaded 16 records. Latest: 2024-03-15 10:20:50
...
```

**What to look for:**

- ✅ "Server starting on http://0.0.0.0:8050"
- ✅ "Loaded X records" messages appearing every 10 seconds
- ✅ Record count increasing over time

**To access dashboard:**

Open browser (Chrome, Firefox, Edge) and navigate to:

```
http://localhost:8050
```

**Expected:** Dashboard loads showing KPI cards and charts (may show "Loading..." initially for 10-20 seconds until data arrives).

**Leave this terminal running.**

---

## Monitoring Operations

### Spark UI

Monitor streaming job execution, stages, and tasks.

**URL**: http://localhost:8080 (Spark Master)  
**URL**: http://localhost:4040 (Active Spark Application - only when streaming job running)

**Key Metrics**:

- **Streaming** tab: Input rate, processing time, scheduling delay
- **Jobs** tab: Completed jobs (should run every 10-30 seconds)
- **Stages** tab: Task completion, data size read/written
- **Executors** tab: Memory usage, task count

**What to look for:**

- ✅ Scheduling delay < 1 second (means keeping up with data)
- ✅ Input rate matches producer rate (~6 records/minute)
- ✅ No failed stages or tasks

---

### Hadoop UI

Monitor HDFS health, storage usage, and datanode status.

**URL**: http://localhost:9870 (NameNode)

**Navigation**:

1. **Overview** tab: Cluster summary, capacity, used space
2. **Datanodes** tab: Health of datanode(s)
3. **Utilities** → **Browse the file system**: Navigate HDFS

**What to look for:**

- ✅ "DFS Used" increasing over time (data being written)
- ✅ Datanodes status: "Live" (not "Dead")
- ✅ `/bitcoin/historical/` showing date-partitioned directories

---

### Kafka Monitoring

Check topic status, partition distribution, and message count.

```bash
# List all topics
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Describe topic (shows partitions, replicas, ISR)
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic bitcoin-prices

# Get message count (offset lag)
docker exec kafka kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic bitcoin-prices \
  --time -1
```

**Expected Describe Output:**

```
Topic: bitcoin-prices
PartitionCount: 3
ReplicationFactor: 1
Partition: 0  Leader: 1  Replicas: 1  Isr: 1
Partition: 1  Leader: 1  Replicas: 1  Isr: 1
Partition: 2  Leader: 1  Replicas: 1  Isr: 1
```

---

### Container Health

Check Docker container status, logs, and resource usage.

```bash
# List running containers
docker ps

# Check container logs
docker logs kafka          # Kafka broker logs
docker logs spark-master   # Spark master logs
docker logs namenode       # HDFS namenode logs

# Follow logs in real-time
docker logs -f producer    # If producer is containerized

# Check resource usage
docker stats
```

---

## Running Batch Analysis

Run periodic batch analysis on accumulated historical data.

**When to run:**

- After accumulating several days of streaming data
- To generate daily/hourly reports
- To identify volatility spike events

**Command:**

```bash
cd d:/College/Sem6/BigData/bitcoin003
bash scripts/start_batch_analysis.sh
```

**Expected Output:**

```
========================================
  Starting Batch Analysis Job
========================================

✓ JAR found: ../spark-jobs/target/scala-2.13/bitcoin-volatility-assembly-1.0.jar
✓ Config: ../config/config.yaml
✓ Main class: BatchAnalysis

Submitting job to Spark...

============================================================
  Bitcoin Volatility Batch Analysis
============================================================

Loading configuration from: ../config/config.yaml
✓ HDFS Namenode: hdfs://namenode:8020
✓ Input Path: /bitcoin/historical
✓ Output Path: /bitcoin/analysis

✓ Spark Session created

Loading historical data from HDFS...
✓ Loaded 156,234 records from HDFS

============================================================
  ANALYSIS 1: Daily Statistics
============================================================

Sample Daily Statistics (most recent 10 days):
+------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-------------+
|date        |avg_price         |max_price         |min_price         |avg_vol           |max_vol           |min_vol           |std_vol           |total_volume      |record_count |
+------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-------------+
|2024-03-05  |67234.45          |68123.56          |66345.78          |0.000234          |0.000456          |0.000123          |0.000089          |1234567890.50     |8640         |
|2024-03-06  |67890.12          |68901.23          |67012.34          |0.000245          |0.000478          |0.000134          |0.000092          |1345678901.60     |8640         |
...
+------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+-------------+

Total days analyzed: 45

Writing daily statistics to: hdfs://namenode:8020/bitcoin/analysis/daily_stats
✓ Daily statistics saved

============================================================
  ANALYSIS 2: Hourly Volatility Pattern
============================================================

Volatility by Hour of Day (UTC):
+---------------------+------------------+------------------+-------------+
|hour_of_day          |avg_vol_1h        |avg_vol_24h       |record_count |
+---------------------+------------------+------------------+-------------+
|0                    |0.000189          |0.000234          |1080         |
|1                    |0.000176          |0.000228          |1080         |
...
|14                   |0.000312          |0.000289          |1080         |
|15                   |0.000298          |0.000281          |1080         |
...
+---------------------+------------------+------------------+-------------+

Peak volatility hour: 14:00 UTC
Average 1h volatility: 0.000312

Writing hourly pattern to: hdfs://namenode:8020/bitcoin/analysis/hourly_pattern
✓ Hourly pattern saved

============================================================
  ANALYSIS 3: Volatility Spike Events
============================================================

99th percentile volatility threshold: 0.000567

Total spike events identified: 1562

Top 20 Volatility Spike Events:
+-------------------------+------------+----------+-------------+-------------+----------+----------+
|datetime                 |date        |price     |volatility_24h|volume24h    |high24h   |low24h    |
+-------------------------+------------+----------+-------------+-------------+----------+----------+
|2024-03-10T14:32:15Z     |2024-03-10  |69234.56  |0.001234     |1567890123.45|69500.12  |67890.34  |
...
+-------------------------+------------+----------+-------------+-------------+----------+----------+

Writing volatility spikes to: hdfs://namenode:8020/bitcoin/analysis/volatility_spikes
✓ Volatility spikes saved

============================================================
  ✓ BATCH ANALYSIS COMPLETE
============================================================

Summary:
  • Total records analyzed: 156,234
  • Analyses generated: 3
  • Output location: hdfs://namenode:8020/bitcoin/analysis

Output directories:
  1. hdfs://namenode:8020/bitcoin/analysis/daily_stats
  2. hdfs://namenode:8020/bitcoin/analysis/hourly_pattern
  3. hdfs://namenode:8020/bitcoin/analysis/volatility_spikes

To view results, use:
  docker exec namenode hdfs dfs -ls -R /bitcoin/analysis

Stopping Spark Session...
✓ Batch analysis session stopped
```

**Interpreting Results:**

1. **Daily Statistics**: Shows how price and volatility evolved day-by-day
2. **Hourly Pattern**: Identifies when Bitcoin is most volatile (typically 13:00-16:00 UTC during US trading hours)
3. **Volatility Spikes**: Flags extreme events for risk analysis (sudden crashes, pumps)

---

## Dashboard Usage

### Accessing the Dashboard

**URL**: http://localhost:8050

### Dashboard Components

#### 1. KPI Cards (Top Row)

| Card                 | Metric                        | Interpretation          |
| -------------------- | ----------------------------- | ----------------------- |
| **Current Price**    | Latest BTC/USD price          | Current market price    |
| **24h Volatility**   | Rolling stddev of log returns | Higher = more volatile  |
| **24h Volume (USD)** | Trading volume                | Higher = more liquidity |
| **Last Update**      | Timestamp of latest data      | Should update every 10s |

#### 2. Price & Volatility Chart (Multi-Panel)

**Top Panel**: Price Time Series

- **Blue solid line**: Current BTC price
- **Orange dashed line**: 1-hour moving average (short-term trend)
- **Green dashed line**: 24-hour moving average (daily trend)

**Interpretation**:

- Price above MAs → Uptrend
- Price below MAs → Downtrend
- MAs crossing → Potential trend change

**Bottom Panel**: 24h Rolling Volatility

- **Red filled area**: Volatility magnitude over time

**Interpretation**:

- Spikes → Large price swings (risk events)
- Low volatility → Stable market

#### 3. Volatility Comparison Chart

- **Purple line**: 1-hour volatility (reactive)
- **Red line**: 24-hour volatility (smoothed)

**Interpretation**:

- 1h >> 24h → Recent volatility surge
- 1h ≈ 24h → Stable volatility regime

#### 4. Volume Bar Chart

- **Green bars**: 24-hour trading volume over time

**Interpretation**:

- High volume + price change → Strong trend
- Low volume + price change → Weak trend (may reverse)

### Dashboard Refresh

- **Auto-refresh**: Every 10 seconds
- **Manual refresh**: Reload browser page (F5)

### Troubleshooting Dashboard

| Issue                         | Cause                           | Solution                              |
| ----------------------------- | ------------------------------- | ------------------------------------- |
| "Loading..." indefinitely     | No data in /tmp/bitcoin_latest/ | Ensure Spark streaming job is running |
| "No data yet"                 | Streaming just started          | Wait 20-30 seconds for first data     |
| Charts show only 1 data point | Not enough time elapsed         | Wait 2-3 minutes for more data        |
| Old timestamp                 | Producer stopped                | Restart producer.py                   |

---

## Data Exploration

### HDFS Commands

```bash
# List all HDFS directories
docker exec namenode hdfs dfs -ls -R /bitcoin

# Check historical data size
docker exec namenode hdfs dfs -du -s -h /bitcoin/historical

# Check analysis output size
docker exec namenode hdfs dfs -du -s -h /bitcoin/analysis

# View specific date partition
docker exec namenode hdfs dfs -ls /bitcoin/historical/date=2024-03-15/

# Download a Parquet file to local (for inspection)
docker exec namenode hdfs dfs -get \
  /bitcoin/analysis/daily_stats/part-00000-....parquet \
  /tmp/daily_stats.parquet

# Copy from Docker container to Windows
docker cp namenode:/tmp/daily_stats.parquet ./daily_stats.parquet
```

### Reading Parquet Files (Python)

```python
import pandas as pd

# Read local Parquet file
df = pd.read_parquet('daily_stats.parquet')
print(df.head())

# Read from HDFS (requires hdfs3 or pyarrow)
# Requires Spark or pyarrow with HDFS support
```

### Spark SQL Queries (Advanced)

```bash
# Start Spark shell with HDFS jars
docker exec -it spark-master spark-shell

# In Spark shell:
val df = spark.read.parquet("hdfs://namenode:8020/bitcoin/historical")
df.printSchema()
df.show(10)

// Query example: Average price by date
df.groupBy("date")
  .agg(avg("price").alias("avg_price"))
  .orderBy("date")
  .show()

// Exit: Ctrl+C or :quit
```

---

## Stopping the System

### Graceful Shutdown (Recommended)

1. **Stop Kafka Producer** (Terminal 1):
   - Press `Ctrl+C`
   - Wait for "Producer closed successfully"

2. **Stop Spark Streaming** (Terminal 2):
   - Press `Ctrl+C`
   - Wait for "Stream processing stopped"

3. **Stop Dashboard** (Terminal 3):
   - Press `Ctrl+C`
   - Wait for server shutdown message

4. **Stop Docker Containers** (preserves data):
   ```bash
   docker-compose stop
   ```

### Full Teardown (Deletes Data)

```bash
# Stop and remove all containers + volumes
docker-compose down -v

# Remove local data directories
rm -rf d:/College/Sem6/BigData/bitcoin003/data
rm -rf /tmp/bitcoin_latest
```

⚠️ **WARNING**: This deletes all HDFS data and Kafka logs. Only use if you want to start from scratch.

---

## Demo Script

### Academic Presentation Sequence (10-15 minutes)

#### 1. Setup Demonstration (2 min)

```bash
# Show directory structure
tree -L 2

# Show configuration
cat config/config.yaml

# Show Docker containers
docker ps
```

#### 2. Data Ingestion (3 min)

```bash
# Terminal 1: Start producer
python kafka-producer/producer.py

# Wait 30 seconds, show messages being sent

# Terminal 2: Monitor Kafka
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic bitcoin-prices \
  --from-beginning \
  --max-messages 5
```

**Narration:**

- "Producer fetches from CryptoCompare API every 10 seconds"
- "Messages are JSON with 12 fields"
- "Kafka buffers data for stream processing"

#### 3. Stream Processing (3 min)

```bash
# Terminal 3: Start Spark streaming
bash scripts/start_streaming.sh

# Wait 1 minute, then show outputs

# Check HDFS
docker exec namenode hdfs dfs -ls /bitcoin/historical/

# Check local files
ls /tmp/bitcoin_latest/
```

**Narration:**

- "Spark reads from Kafka in micro-batches"
- "Computes log returns and rolling volatility"
- "Writes to HDFS (Parquet, partitioned by date)"
- "Also writes to local JSON for dashboard"

#### 4. Visualization (2 min)

```bash
# Terminal 4: Start dashboard
python dashboard/app.py

# Open browser: http://localhost:8050
```

**Narration:**

- "Dashboard auto-refreshes every 10 seconds"
- "Shows real-time price, volatility, volume"
- "Charts visualize trends and volatility spikes"

#### 5. Batch Analysis (3 min)

```bash
# Terminal 5: Run batch analysis
bash scripts/start_batch_analysis.sh
```

**Narration:**

- "Batch job analyzes all historical data"
- "Daily statistics show aggregations by date"
- "Hourly pattern identifies peak volatility hours"
- "Spike detection flags extreme events (99th percentile)"

#### 6. Monitoring (2 min)

**Open browser tabs:**

- Spark UI: http://localhost:8080
- Hadoop UI: http://localhost:9870

**Narration:**

- "Spark UI shows streaming jobs completing every 10-30 seconds"
- "Hadoop UI shows increasing storage usage"
- "Currently have 3+ GB of data in HDFS"

---

## Frequently Asked Questions

### Q1: How long should I let the system run?

**A**: For a demo: 5-10 minutes (enough to see charts populate).  
For full analysis: 24+ hours (captures daily volatility patterns).

### Q2: Can I pause and resume the system?

**A**: Yes, but with caveats:

- Stop all Python/Scala processes with Ctrl+C
- Keep Docker containers running: `docker-compose stop` (not `down`)
- Resume by starting producer → streaming → dashboard again
- Streaming resumes from last Kafka offset (no data loss)

### Q3: How do I clear old data?

**HDFS**:

```bash
# Delete specific date partition
docker exec namenode hdfs dfs -rm -r /bitcoin/historical/date=2024-03-10/

# Clear all historical data
docker exec namenode hdfs dfs -rm -r /bitcoin/historical/*
```

**Kafka** (auto-deletes after 24h retention period, or manually):

```bash
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete \
  --topic bitcoin-prices

# Recreate topic
bash scripts/setup_kafka.sh
```

### Q4: What if I get rate-limited by the API?

**A**: CryptoCompare free tier limits:

- ~100,000 calls/month
- ~50-100 calls/minute

**Solutions**:

1. Increase `fetch_interval_seconds` in config.yaml (e.g., 20 or 30)
2. Use existing historical data only (skip new streaming)
3. Upgrade to paid API tier

### Q5: Can I add more cryptocurrencies?

**A**: Yes, modify `producer.py`:

```python
# Change from
params = {'fsyms': 'BTC', 'tsyms': 'USD', 'api_key': self.api_key}

# To
params = {'fsyms': 'BTC,ETH,LTC', 'tsyms': 'USD', 'api_key': self.api_key}

# Then extract data for each symbol
```

You'll also need to update the Spark schema to include a `symbol` field.

---

## Next Steps

- **Extend Analysis**: Add more cryptocurrencies, correlation analysis
- **Improve Accuracy**: Implement GARCH volatility forecasting
- **Add Alerts**: Notify when volatility exceeds threshold (email, Slack)
- **Export Reports**: Generate PDF reports with matplotlib
- **Deploy to Cloud**: AWS EMR, Azure HDInsight, GCP Dataproc

---

**For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md)**  
**For setup instructions, see [SETUP.md](SETUP.md)**
