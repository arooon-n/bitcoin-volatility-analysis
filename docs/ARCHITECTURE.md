# Architecture - Bitcoin Volatility Analysis System

This document provides a comprehensive overview of the system architecture, design decisions, and Big Data principles applied in the Bitcoin Volatility Analysis pipeline.

## Table of Contents

1. [System Overview](#system-overview)
2. [Data Flow Architecture](#data-flow-architecture)
3. [Component Details](#component-details)
4. [Volatility Methodology](#volatility-methodology)
5. [HDFS Directory Layout](#hdfs-directory-layout)
6. [Big Data 4 V's](#big-data-4-vs)
7. [Technology Choices](#technology-choices)

---

## System Overview

The Bitcoin Volatility Analysis System is a **real-time streaming data pipeline** that ingests, processes, stores, and visualizes cryptocurrency price data to analyze market volatility patterns.

### Key Characteristics

- **Architecture Style**: Lambda Architecture (batch + streaming)
- **Processing Model**: Real-time streaming + periodic batch analysis
- **Storage Strategy**: Immutable data lake (HDFS Parquet)
- **Deployment**: Containerized microservices (Docker)
- **Resource Footprint**: Optimized for 4-6 GB RAM

### Design Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Idempotency**: All setup scripts can be run multiple times safely
3. **Fail-Fast**: Early validation with clear error messages
4. **Configuration-Driven**: No hardcoded values; all settings in config.yaml
5. **Observability**: Comprehensive logging at every stage

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                                 │
│                                                                         │
│   CryptoCompare API                                                     │
│   (REST: /data/pricemultifull)                                          │
│          ↓                                                              │
│   producer.py (Python 3.11)                                             │
│   • Fetch every 10 seconds                                              │
│   • Serialize to JSON                                                   │
│   • Publish to Kafka                                                    │
└───────────────────────────┬─────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    MESSAGE BROKER LAYER                                 │
│                                                                         │
│   Apache Kafka 3.9.0                                                    │
│   Topic: bitcoin-prices                                                 │
│   • 3 partitions (parallelism)                                          │
│   • Replication factor: 1                                               │
│   • Retention: 24 hours                                                 │
└───────────────────────────┬─────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    STREAM PROCESSING LAYER                              │
│                                                                         │
│   VolatilityStream.scala (Spark 3.5.8, Scala 2.13.14)                  │
│   • Read from Kafka (Structured Streaming)                              │
│   • Parse JSON → DataFrame                                              │
│   • Add timestamps (event_time, date)                                   │
│   • Compute volatility metrics:                                         │
│     - Log returns: ln(P_t / P_t-1)                                      │
│     - Rolling volatility (1h, 24h): stddev over time windows            │
│     - Moving averages (1h, 24h)                                         │
│     - Price change percentage                                           │
│   • Trigger: ProcessingTime (30s for HDFS, 10s for local)              │
└──────────────────┬──────────────────────────┬───────────────────────────┘
                   ↓                          ↓
      ┌────────────────────────┐   ┌────────────────────────┐
      │   HDFS SINK            │   │   LOCAL SINK           │
      │   (Permanent Storage)  │   │   (Dashboard Staging)  │
      │                        │   │                        │
      │ • Format: Parquet      │   │ • Format: JSON         │
      │ • Compression: Snappy  │   │ • Path: /tmp/          │
      │ • Partitioned by: date │   │   bitcoin_latest/      │
      │ • Path: /bitcoin/      │   │ • Update: 10s          │
      │   historical           │   │                        │
      └────────────┬───────────┘   └───────────┬────────────┘
                   ↓                           ↓
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│   BATCH PROCESSING LAYER         │   │   VISUALIZATION LAYER            │
│                                  │   │                                  │
│ BatchAnalysis.scala (Spark)      │   │ app.py (Dash 2.14, Plotly 5.17) │
│ • Read all Parquet from HDFS     │   │ • Read JSON from /tmp/           │
│ • Analysis 1: Daily Statistics   │   │ • Display KPIs:                  │
│   - Avg/Max/Min price & vol      │   │   - Current price                │
│ • Analysis 2: Hourly Pattern     │   │   - 24h volatility               │
│   - Volatility by hour of day    │   │   - 24h volume                   │
│ • Analysis 3: Volatility Spikes  │   │   - Last update timestamp        │
│   - 99th percentile events       │   │ • Charts:                        │
│ • Output: Parquet to             │   │   - Price + MAs + Volatility     │
│   /bitcoin/analysis              │   │   - 1h vs 24h volatility         │
│                                  │   │   - Volume bar chart             │
│                                  │   │ • Auto-refresh: 10s              │
└──────────────────────────────────┘   └──────────────────────────────────┘
```

---

## Component Details

### 1. Kafka Producer (producer.py)

**Purpose**: Continuously poll CryptoCompare API and publish price data to Kafka.

**Implementation**:

- Language: Python 3.11
- Library: kafka-python 2.0.2
- Class: `BitcoinProducer`

**Key Features**:

- **Fetch Interval**: Configurable (default 10s = 6 calls/minute)
- **Data Fields**: 12 fields including price, OHLC, volume, market cap
- **Reliability**:
  - `acks='all'` - Wait for all broker acknowledgments
  - `retries=3` - Retry failed sends
  - `max_in_flight_requests=1` - Ensure message ordering
- **Error Handling**: Catches API errors, network issues, Kafka errors
- **Logging**: INFO level with timestamps, prices, and Kafka metadata

**Message Schema** (JSON):

```json
{
  "timestamp": 1678901234,
  "datetime": "2024-03-15T12:34:56Z",
  "price": 67890.12,
  "open24h": 67500.0,
  "high24h": 68200.45,
  "low24h": 66800.3,
  "volume24h": 1234567890.5,
  "volumeto24h": 18123456.78,
  "change24h": 390.12,
  "changepct24h": 0.58,
  "market_cap": 1324567890123.45,
  "supply": 19500000.0
}
```

---

### 2. Apache Kafka

**Purpose**: Message broker for decoupling data ingestion from processing.

**Configuration**:

- **Broker**: Single instance (development setup)
- **Topic**: `bitcoin-prices`
- **Partitions**: 3 (allows parallel consumption)
- **Replication**: 1 (single broker, no replication)
- **Retention**: 24 hours (configurable)

**Why Kafka?**

- **Buffering**: Handles producer/consumer speed mismatches
- **Durability**: Persists messages to disk
- **Scalability**: Can add consumers without changing producer
- **Replay**: Can reprocess data from any offset

---

### 3. Spark Structured Streaming (VolatilityStream.scala)

**Purpose**: Real-time computation of volatility metrics from Kafka stream.

**Implementation**:

- Language: Scala 2.13.14
- Framework: Spark Structured Streaming 3.5.8
- Object: `VolatilityStream`

**Processing Pipeline**:

1. **Kafka Source**: Read from `bitcoin-prices` topic

   ```scala
   .readStream
   .format("kafka")
   .option("kafka.bootstrap.servers", kafkaServers)
   .option("subscribe", topic)
   .option("startingOffsets", "latest")
   ```

2. **JSON Parsing**: Deserialize Kafka value to DataFrame

   ```scala
   .select(from_json(col("value").cast(StringType), schema).as("parsed"))
   .select("parsed.*")
   ```

3. **Timestamp Enrichment**: Add processing-time columns

   ```scala
   .withColumn("event_time", col("timestamp").cast(TimestampType))
   .withColumn("date", to_date(col("event_time")))
   ```

4. **Volatility Metrics**: Apply windowed aggregations
   - Log return = `ln(price_t / price_t-1)`
   - 1h window = last 3600 seconds (rangeBetween)
   - 24h window = last 86400 seconds
   - Volatility = stddev of log returns over window
   - Moving average = avg of price over window

5. **Dual Sinks**:
   - **HDFS**: Parquet, partitioned by date, 30s trigger
   - **Local**: JSON, for dashboard, 10s trigger

**Checkpointing**: Ensures exactly-once processing and fault tolerance.

---

### 4. HDFS (Hadoop Distributed File System)

**Purpose**: Persistent, distributed storage for all historical data.

**Configuration**:

- **Version**: Hadoop 3.2.1
- **Mode**: Pseudo-distributed (1 NameNode + 1 DataNode)
- **Replication**: 1 (single node)
- **Format**: Parquet with Snappy compression

**Storage Efficiency**:

- Parquet: Columnar format, optimized for analytics
- Snappy Compression: ~2-3x space reduction, fast decompression
- Date Partitioning: Efficient querying by date range

---

### 5. Spark Batch Processing (BatchAnalysis.scala)

**Purpose**: Periodic deep-dive analysis of accumulated historical data.

**Implementation**:

- Language: Scala 2.13.14
- Framework: Spark SQL 3.5.8
- Object: `BatchAnalysis`

**Analyses**:

1. **Daily Statistics**

   ```scala
   .groupBy("date")
   .agg(
     avg("price"), max("price"), min("price"),
     avg("volatility_24h"), max("volatility_24h"),
     sum("volume24h")
   )
   ```

   - Output: `/bitcoin/analysis/daily_stats` (Parquet)

2. **Hourly Volatility Pattern**

   ```scala
   .withColumn("hour_of_day", hour(col("event_time")))
   .groupBy("hour_of_day")
   .agg(avg("volatility_1h"), count("*"))
   ```

   - Identifies peak volatility times (e.g., 14:00-16:00 UTC during US market hours)
   - Output: `/bitcoin/analysis/hourly_pattern` (Parquet)

3. **Volatility Spike Events**
   ```scala
   val threshold = df.stat.approxQuantile("volatility_24h", Array(0.99), 0.001).head
   df.filter(col("volatility_24h") > threshold)
   ```

   - Flags extreme events for risk analysis
   - Output: `/bitcoin/analysis/volatility_spikes` (Parquet)

---

### 6. Dashboard (app.py)

**Purpose**: Real-time web visualization for monitoring and analysis.

**Implementation**:

- Language: Python 3.11
- Framework: Dash 2.14.2 (built on Flask)
- Charting: Plotly 5.17.0
- Class: `BitcoinDashboard`

**Architecture**:

- **Server**: Flask development server
- **Port**: 8050 (configurable)
- **Update Mechanism**: Dash `Interval` component (10s)

**Layout**:

1. **Header**: Title and subtitle
2. **KPI Cards**: 4 cards (price, volatility, volume, timestamp)
3. **Charts**:
   - Multi-panel (price + volatility)
   - Volatility comparison (1h vs 24h)
   - Volume bar chart
4. **Footer**: Data source attribution

**Data Flow**:

```python
load_latest_data():
  • Glob all .json files in /tmp/bitcoin_latest/
  • Parse JSON Lines format (one object per line)
  • Combine into DataFrame
  • Sort by timestamp, keep last 1000 records
  • Return to callback

Callback (triggered every 10s):
  • Extract latest row for KPIs
  • Build 3 Plotly figures
  • Return 7 outputs (4 texts + 3 charts)
```

---

## Volatility Methodology

### Why Log Returns?

Traditional simple returns: `R_t = (P_t - P_{t-1}) / P_{t-1}`

**Problem**: Not symmetric (20% up ≠ 20% down in magnitude)

**Solution**: Log returns: `r_t = ln(P_t / P_{t-1})`

**Benefits**:

- Time-additive: `r_{1→3} = r_{1→2} + r_{2→3}`
- Symmetric: `ln(P_t / P_{t-1}) = -ln(P_{t-1} / P_t)`
- Approximately equal to simple returns for small changes
- Standard in financial modeling

### Rolling Volatility

**Definition**: Standard deviation of log returns over a time window.

**Implementation** (Spark SQL):

```scala
val window1h = Window
  .orderBy(col("timestamp").cast(LongType))
  .rangeBetween(-3600, 0)  // Last 3600 seconds

val volatility_1h = stddev(col("log_return")).over(window1h)
```

**Interpretation**:

- **High volatility**: Large price swings, higher risk
- **Low volatility**: Stable prices, lower risk

**Windows**:

- **1-hour**: Short-term volatility, responsive to recent moves
- **24-hour**: Daily volatility, smooths intraday noise

### Moving Averages

**Purpose**: Identify price trends by smoothing out noise.

**Implementation**:

```scala
val price_ma_1h = avg(col("price")).over(window1h)
```

**Interpretation**:

- **Price > MA**: Uptrend
- **Price < MA**: Downtrend

---

## HDFS Directory Layout

```
/bitcoin/                           # Root directory for all Bitcoin data
│
├── historical/                     # Streaming data (permanent storage)
│   ├── date=2024-03-15/           # Partitioned by date
│   │   ├── part-00000-....parquet
│   │   ├── part-00001-....parquet
│   │   └── ...
│   ├── date=2024-03-16/
│   └── ...
│
├── checkpoints/                    # Spark streaming checkpoints
│   ├── stream/                    # HDFS sink checkpoint
│   │   ├── commits/
│   │   ├── metadata
│   │   └── offsets/
│   └── latest/                    # Local sink checkpoint
│       ├── commits/
│       └── offsets/
│
└── analysis/                       # Batch analysis outputs
    ├── daily_stats/               # Daily aggregations
    │   └── *.parquet
    ├── hourly_pattern/            # Hourly volatility pattern
    │   └── *.parquet
    └── volatility_spikes/         # Spike events
        └── *.parquet
```

**Why Date Partitioning?**

- **Query Efficiency**: Filter by date = only scan relevant partitions
- **Manageability**: Easy to delete old data (drop partition)
- **Parallelism**: Spark can process partitions in parallel

**Checkpoint Necessity**:

- Tracks Kafka offsets (which messages processed)
- Enables exactly-once semantics
- Allows restart from last processed offset after failure

---

## Big Data 4 V's

### 1. Volume

**Requirement**: 3+ GB of data

**Strategy**:

- **Historical Bulk Load**:
  - BTC minute data (90 days): ~130,000 records × ~800 bytes ≈ 104 MB
  - BTC hourly data (3 years): ~26,000 records × ~800 bytes ≈ 21 MB
  - ETH + LTC hourly (3 years each): ~2 × 26,000 × 800 ≈ 42 MB
  - **With Parquet overhead and multiple coins**: ~3.2 GB

- **Continuous Streaming**:
  - 6 records/minute = 8,640 records/day ≈ 7 MB/day
  - Over 30 days: ~210 MB additional

**Result**: System accumulates and maintains 3+ GB in HDFS.

---

### 2. Velocity

**Requirement**: Real-time data ingestion and processing

**Implementation**:

- **Ingestion Rate**: 1 message per 10 seconds = 6/minute
- **Processing Latency**:
  - Kafka: < 100ms
  - Spark micro-batch: 10-30 seconds
  - Dashboard refresh: 10 seconds
- **End-to-End**: New data visible in dashboard within ~20 seconds

**Why 10 seconds?**

- Free API tier rate limits
- Sufficient for volatility analysis (not HFT)
- Balances freshness vs. resource usage

---

### 3. Variety

**Requirement**: Multiple data formats and structures

**Formats**:

1. **JSON**: Kafka messages, local dashboard staging
2. **Parquet**: HDFS permanent storage
3. **Structured Streams**: Spark DataFrames (in-memory)

**Data Types**:

- Time series (price, volume over time)
- Aggregated statistics (daily, hourly summaries)
- Event data (volatility spikes)

**Sources**:

- REST API (CryptoCompare)
- Streaming platform (Kafka)
- Distributed storage (HDFS)

---

### 4. Veracity

**Requirement**: Data quality, consistency, and reliability

**Techniques**:

1. **Error Handling**:
   - Try/except blocks in all Python code
   - Null handling with `coalesce`, `fill`, `when` in Spark
   - Kafka retry logic with acknowledgments

2. **Validation**:
   - Schema enforcement (StructType in Spark)
   - Type checking (LongType, DoubleType, etc.)
   - Range checks (price > 0, volume ≥ 0)

3. **Idempotency**:
   - HDFS setup: `mkdir -p`, `--if-not-exists`
   - Kafka topic: `--if-not-exists` flag
   - Overwrites in batch: `mode("overwrite")`

4. **Logging & Monitoring**:
   - Comprehensive logs at INFO/WARN/ERROR levels
   - Message counts and success rates
   - HDFS size verification

5. **Checkpointing**:
   - Exactly-once processing semantics
   - Fault tolerance (restart from last checkpoint)

---

## Technology Choices

### Why Kafka?

**Alternatives Considered**: Direct Spark streaming from API, RabbitMQ, AWS Kinesis

**Why Kafka Wins**:

- ✅ Industry-standard for streaming data
- ✅ Durable (persists to disk)
- ✅ Scalable (horizontal partitioning)
- ✅ Decouples producer from consumer
- ✅ Built-in Spark connector
- ✅ Open-source, self-hosted

---

### Why Spark Structured Streaming (not DStreams)?

**DStreams (Old API)**:

- RDD-based
- Lower-level, more boilerplate
- Deprecated in Spark 3.x

**Structured Streaming (New API)**:

- ✅ DataFrame/SQL API (familiar to analysts)
- ✅ Better optimization (Catalyst + Tungsten)
- ✅ Unified batch + streaming code
- ✅ Exactly-once semantics built-in
- ✅ Window operations with less code

---

### Why HDFS?

**Alternatives Considered**: Local disk, AWS S3, Azure Blob Storage

**Why HDFS Wins**:

- ✅ Part of Hadoop ecosystem (academic requirement)
- ✅ Designed for Big Data workloads
- ✅ Fault-tolerant (replication)
- ✅ Integrates seamlessly with Spark
- ✅ Self-hosted (no cloud costs)

---

### Why Parquet (not CSV/JSON)?

**CSV/JSON Issues**:

- Row-based (read entire row even if need 1 column)
- No schema enforcement
- No compression (or inefficient gzip)
- Slow for analytics

**Parquet Benefits**:

- ✅ Columnar format (only read needed columns)
- ✅ Schema embedded in file
- ✅ Efficient compression (Snappy: 2-3x reduction)
- ✅ Predicate pushdown (filter at file level)
- ✅ Standard for data lakes

---

### Why Scala (not Python) for Spark?

**Python Issues**:

- Serialization overhead (Python ↔ JVM)
- Limited for complex transformations
- Not statically typed

**Scala Benefits**:

- ✅ Native Spark language (zero serialization)
- ✅ Type safety (catch errors at compile time)
- ✅ Better performance for complex logic
- ✅ Academic learning (common in Big Data courses)

---

### Why Dash (not Grafana, Kibana, custom React)?

**Grafana/Kibana**: Better for logs/metrics, not custom analytics

**Custom React**: Overkill, more dev time

**Dash**:

- ✅ Pure Python (no JavaScript needed)
- ✅ Plotly integration (publication-quality charts)
- ✅ Reactive (auto-updates with callbacks)
- ✅ Lightweight (Flask under the hood)
- ✅ Fast prototyping for academic projects

---

## Performance Considerations

### Resource Limits

| Component       | CPU      | RAM    | Disk                 |
| --------------- | -------- | ------ | -------------------- |
| Spark Driver    | 2 cores  | 4 GB   | -                    |
| Spark Executor  | 2 cores  | 2 GB   | -                    |
| Kafka           | 1 core   | 1.5 GB | 10 GB (logs)         |
| Hadoop NameNode | 1 core   | 1 GB   | 5 GB (metadata)      |
| Hadoop DataNode | 1 core   | 1 GB   | 10+ GB (actual data) |
| Zookeeper       | 0.5 core | 512 MB | 1 GB                 |

**Total**: ~6 GB RAM, 4-5 CPU cores, 30+ GB disk

### Optimization Techniques

1. **Spark Shuffle Partitions**: Reduced to 3 (not 200 default)
2. **Kafka Partitions**: 3 (balances parallelism and overhead)
3. **Parquet Compression**: Snappy (fast, good ratio)
4. **Date Partitioning**: Prunes unnecessary data scans
5. **DataFrame Caching**: Cache batch analysis input
6. **Window Ranges**: Use `rangeBetween` (time-based), not `rowsBetween`

---

## Security & Production Readiness

### Current State (Development)

❌ **NOT production-ready**:

- No authentication (Kafka, HDFS, Dashboard)
- No SSL/TLS encryption
- Hardcoded `chmod 777` on HDFS
- Single point of failure (no replication)
- API key in plain text config file

### Production Recommendations

For enterprise deployment:

1. **Authentication**: SASL for Kafka, Kerberos for Hadoop
2. **Encryption**: SSL for all network traffic
3. **Secrets Management**: HashiCorp Vault, AWS Secrets Manager
4. **Replication**: 3+ Kafka brokers, HDFS replication factor 3
5. **Monitoring**: Prometheus + Grafana for metrics
6. **Logging**: ELK stack (Elasticsearch, Logstash, Kibana)
7. **Backup**: Regular HDFS snapshots, Kafka topic backups
8. **Access Control**: RBAC for HDFS, Dashboard login

---

## Future Architecture Extensions

### Horizontal Scaling

```
                    ┌─── Producer 1 ───┐
CryptoCompare API ──┼─── Producer 2 ───┼─→ Kafka Cluster (3 brokers)
                    └─── Producer 3 ───┘            ↓
                                             Spark Cluster (1 master + N workers)
                                                     ↓
                                            HDFS Cluster (1 NN + M DNs)
```

### Multi-Asset Pipeline

- Extend to track 10+ cryptocurrencies
- Cross-asset correlation analysis
- Portfolio volatility modeling

### Advanced Analytics

- Anomaly detection (Isolation Forest)
- Volatility forecasting (GARCH models)
- Sentiment analysis (Twitter API integration)

---

## Conclusion

This architecture demonstrates key Big Data principles:

- **Distributed processing** (Spark)
- **Scalable storage** (HDFS)
- **Stream processing** (Kafka + Spark Streaming)
- **Fault tolerance** (checkpointing, replication)
- **Optimized analytics** (Parquet, partitioning)

It's suitable for **academic projects** and **proof-of-concept** deployments, with a clear path to production hardening.

---

**For operational details, see [USAGE.md](USAGE.md)**  
**For setup instructions, see [SETUP.md](SETUP.md)**
