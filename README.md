# Bitcoin Volatility Analysis System

A production-ready real-time Bitcoin volatility analysis pipeline built with Apache Kafka, Spark Structured Streaming, HDFS, and Python Dash. This academic project demonstrates Big Data technologies for streaming data processing, volatility calculation, and interactive visualization.

## Project Overview

This system:

- **Streams** live Bitcoin price data from CryptoCompare API via Kafka
- **Processes** real-time data using Spark Structured Streaming (Scala)
- **Calculates** volatility metrics: log returns, rolling volatility (1h/24h), moving averages
- **Stores** all data in HDFS (Parquet format, partitioned by date)
- **Analyzes** historical data with batch processing jobs
- **Visualizes** everything in an auto-refreshing web dashboard (updates every 10s)

**No machine learning** — pure volatility measurement and analysis.

## Architecture

```
CryptoCompare API
       ↓
   producer.py (Python)
       ↓
   Apache Kafka (bitcoin-prices topic)
       ↓
   VolatilityStream.scala (Spark Streaming)
       ↓ ↓
       ↓ ├→ HDFS (Parquet, permanent storage)
       ↓ └→ /tmp/bitcoin_latest/ (JSON, dashboard staging)
       ↓
   BatchAnalysis.scala (Spark Batch)
       ↓
   HDFS Analysis Results

/tmp/bitcoin_latest/
       ↓
   app.py (Dash Dashboard)
       ↓
   Browser (http://localhost:8050)
```

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Java 17
- Scala 2.13.14
- sbt 1.12.0
- Python 3.11
- Git Bash (for running .sh scripts on Windows)

### 2. Get CryptoCompare API Key

1. Go to https://www.cryptocompare.com/cryptopian/api-keys
2. Sign up (free) and create an API key
3. Copy your API key

### 3. Configure

```bash
# Edit config file
notepad config\config.yaml

# Replace YOUR_API_KEY_HERE with your actual API key
```

### 4. Start Infrastructure

```bash
# Create data directories
bash scripts/create_data_dirs.sh

# Start Docker containers (Hadoop, Kafka, Spark)
docker-compose up -d

# Wait 60 seconds for services to initialize
# Verify services:
docker ps  # All containers should be healthy
```

### 5. Setup HDFS and Kafka

```bash
# Create HDFS directories
bash scripts/setup_hdfs.sh

# Create Kafka topics
bash scripts/setup_kafka.sh
```

### 6. Download Historical Data (3+ GB)

```bash
# Install Python dependencies
pip install -r scripts/requirements.txt

# Download and upload to HDFS (~10-20 minutes)
python scripts/download_historical_data.py
```

### 7. Build Spark Jobs

```bash
cd spark-jobs
sbt assembly
cd ..
```

### 8. Start Pipeline

```bash
# Terminal 1: Start Kafka Producer
cd kafka-producer
pip install -r requirements.txt
python producer.py

# Terminal 2: Start Spark Streaming (after JAR is built)
bash scripts/start_streaming.sh

# Terminal 3: Start Dashboard
cd dashboard
pip install -r requirements.txt python app.py
```

### 9. Access Dashboard

Open browser: **http://localhost:8050**

### 10. Run Batch Analysis (Optional)

```bash
bash scripts/start_batch_analysis.sh
```

## Directory Structure

```
bitcoin-volatility-project/
├── config/
│   └── config.yaml                 # Central configuration file
├── docker-compose.yaml             # Docker infrastructure setup
├── data/                          # Docker volume data (created at runtime)
│   ├── namenode/
│   ├── datanode/
│   └── kafka/
├── kafka-producer/
│   ├── producer.py                # Kafka producer (Python)
│   └── requirements.txt
├── spark-jobs/
│   ├── build.sbt                  # sbt build configuration
│   ├── project/
│   │   ├── build.properties
│   │   └── plugins.sbt
│   ├── src/main/scala/
│   │   ├── VolatilityStream.scala # Spark Streaming job
│   │   └── BatchAnalysis.scala    # Batch analysis job
│   └── target/                    # Compiled JAR (created by sbt)
├── dashboard/
│   ├── app.py                     # Dash web dashboard
│   └── requirements.txt
├── scripts/
│   ├── create_data_dirs.sh        # Create Docker volume directories
│   ├── setup_hdfs.sh              # HDFS directory setup
│   ├── setup_kafka.sh             # Kafka topic setup
│   ├── download_historical_data.py # Historical data downloader
│   ├── start_streaming.sh         # Start Spark streaming
│   ├── start_batch_analysis.sh    # Run batch analysis
│   └── requirements.txt
├── docs/
│   ├── SETUP.md                   # Detailed setup instructions
│   ├── ARCHITECTURE.md            # Architecture deep-dive
│   └── USAGE.md                   # Usage guide and commands
└── README.md                      # This file
```

## Technologies

| Tool          | Version   | Purpose                     |
| ------------- | --------- | --------------------------- |
| Java          | 17        | JVM runtime for Scala/Spark |
| Scala         | 2.13.14   | Spark job implementation    |
| sbt           | 1.12.0    | Scala build tool            |
| Apache Spark  | 3.5.8     | Stream & batch processing   |
| Apache Kafka  | 3.9.0     | Message broker              |
| Apache Hadoop | 3.2.1     | HDFS distributed storage    |
| Python        | 3.11      | Data collection & dashboard |
| Dash/Plotly   | 2.14/5.17 | Interactive visualization   |
| Docker        | Latest    | Container orchestration     |

## Academic Requirements Met

| Requirement             | How Met                                                                                 |
| ----------------------- | --------------------------------------------------------------------------------------- |
| **Volume (3+ GB)**      | Historical data download: 90 days BTC minute data + 3 years hourly data for BTC/ETH/LTC |
| **Velocity**            | Real-time streaming with 10-second ingestion intervals                                  |
| **Variety**             | JSON (Kafka), Parquet (HDFS), structured/time-series data                               |
| **Veracity**            | Error handling, null filling, data validation, idempotent scripts                       |
| **Stream Processing**   | Spark Structured Streaming with windowed aggregations                                   |
| **Batch Processing**    | Spark batch jobs for daily stats, hourly patterns, spike detection                      |
| **Distributed Storage** | HDFS with date-based partitioning                                                       |
| **Message Queue**       | Kafka with 3 partitions for parallelism                                                 |
| **Visualization**       | Real-time dashboard with 4 KPIs and 3 charts                                            |

## Key Features

### Volatility Metrics

- **Log Returns**: `ln(P_t / P_t-1)` - continuous return calculation
- **Rolling Volatility**: Standard deviation of log returns over time windows
  - 1-hour window: Short-term volatility
  - 24-hour window: Daily volatility pattern
- **Moving Averages**: Price trends (1h and 24h)
- **Price Change %**: Percentage change from previous price

### Batch Analyses

1. **Daily Statistics**: Price and volatility aggregations by date
2. **Hourly Pattern**: Identifies peak volatility hours
3. **Volatility Spikes**: Extreme events (99th percentile)

### Dashboard Features

- Auto-refresh every 10 seconds
- Real-time KPI cards (price, volatility, volume, timestamp)
- Multi-panel charts (price with MAs, volatility comparison, volume)
- Hover tooltips with unified crosshair

## Resource Configuration (Windows 11, 16GB RAM)

The system is configured to use **4-6 GB RAM maximum**:

- Spark Driver: 4 GB
- Spark Executor: 2 GB
- Kafka: 1.5 GB
- Hadoop NameNode: 1 GB
- Hadoop DataNode: 1 GB
- Zookeeper: 512 MB

All data stored on **D:\ drive** to conserve C:\ space.

## Monitoring & Verification

### Check HDFS Data

```bash
# List all HDFS directories
docker exec namenode hdfs dfs -ls -R /bitcoin

# Check data size (verify 3+ GB requirement)
docker exec namenode hdfs dfs -du -s -h /bitcoin/historical
```

### Monitor Kafka

```bash
# List topics
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Consume messages
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic bitcoin-prices \
  --from-beginning
```

### Access Web UIs

- **Spark Master UI**: http://localhost:8080
- **Spark Application UI**: http://localhost:4040 (when job running)
- **Hadoop NameNode UI**: http://localhost:9870
- **Hadoop DataNode UI**: http://localhost:9864
- **Dashboard**: http://localhost:8050

## Troubleshooting

| Issue                    | Solution                                                                    |
| ------------------------ | --------------------------------------------------------------------------- |
| HDFS not accessible      | Wait 60s after `docker-compose up`, then check `docker logs namenode`       |
| Kafka connection refused | Check `docker logs kafka`, ensure Zookeeper is running first                |
| JAR not found            | Run `cd spark-jobs && sbt assembly`                                         |
| No dashboard data        | Ensure Spark streaming job is running and writing to `/tmp/bitcoin_latest/` |
| Out of memory            | Reduce `driver_memory` and `executor_memory` in config.yaml                 |
| API rate limit           | Reduce `fetch_interval_seconds` in config.yaml                              |

## Known Limitations

1. **Single node setup** - Not horizontally scalable (for academic demo)
2. **No authentication** - All services open (development only)
3. **Limited error recovery** - Manual restart required for some failures
4. **Windows path handling** - Use Git Bash for .sh scripts
5. **Resource constraints** - Configured for 4-6 GB RAM (reduce for lower specs)

## Future Enhancements

- Add more cryptocurrencies (ETH, LTC, XRP)
- Implement alerting system for volatility spikes
- Add historical comparison views
- Export analysis reports to PDF
- Implement authentication for dashboard
- Add unit tests and integration tests
- Kubernetes deployment for production

## License

Academic project - MIT License

## Contributors

Built for Big Data Analytics course (Semester 6)

## Documentation

For detailed information, see:

- [SETUP.md](docs/SETUP.md) - Step-by-step setup guide
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture details
- [USAGE.md](docs/USAGE.md) - Usage guide and commands

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review logs: `docker-compose logs [service-name]`
3. Verify all prerequisites are installed
4. Ensure config.yaml has valid API key

---

**Data Source**: CryptoCompare API  
**Processing Engine**: Apache Spark Structured Streaming  
**Storage**: HDFS (Parquet format)  
**Visualization**: Python Dash + Plotly
