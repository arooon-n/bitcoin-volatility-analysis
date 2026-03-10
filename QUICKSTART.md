# Quick Start Guide

Get the Bitcoin Volatility Analysis System running in under 30 minutes.

## Prerequisites

- Docker Desktop installed and running
- Java 17, Scala 2.13.14, sbt 1.12.0
- Python 3.11
- Git Bash (Windows)
- CryptoCompare API key (free): https://www.cryptocompare.com/cryptopian/api-keys

## One-Time Setup (15 minutes)

```bash
# 1. Configure API key
notepad config/config.yaml  # Replace YOUR_API_KEY_HERE

# 2. Create data directories
bash scripts/create_data_dirs.sh

# 3. Start Docker containers (wait 60 seconds after)
docker-compose up -d
sleep 60

# 4. Setup HDFS and Kafka
bash scripts/setup_hdfs.sh
bash scripts/setup_kafka.sh

# 5. Download historical data (10-20 minutes)
pip install -r scripts/requirements.txt
python scripts/download_historical_data.py

# 6. Build Spark jobs (3-5 minutes)
cd spark-jobs && sbt assembly && cd ..

# 7. Install Python dependencies
pip install -r kafka-producer/requirements.txt
pip install -r dashboard/requirements.txt
```

## Running the System (3 terminals)

**Terminal 1** - Kafka Producer:

```bash
cd kafka-producer
python producer.py
```

**Terminal 2** - Spark Streaming:

```bash
bash scripts/start_streaming.sh
```

**Terminal 3** - Dashboard:

```bash
cd dashboard
python app.py
```

**Browser**: http://localhost:8050

## Optional: Batch Analysis

```bash
bash scripts/start_batch_analysis.sh
```

## Monitoring

- **Dashboard**: http://localhost:8050
- **Spark UI**: http://localhost:8080 (Master) and http://localhost:4040 (Application)
- **Hadoop UI**: http://localhost:9870
- **Check HDFS**: `docker exec namenode hdfs dfs -ls -R /bitcoin`
- **Check Kafka**: `docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list`

## Stop Everything

```bash
# Stop Python/Scala processes: Ctrl+C in each terminal
# Stop Docker: docker-compose stop
```

## Troubleshooting

| Issue                    | Solution                         |
| ------------------------ | -------------------------------- |
| HDFS not accessible      | Wait 60s after docker-compose up |
| Kafka connection refused | Check `docker logs kafka`        |
| No dashboard data        | Ensure streaming job is running  |
| Out of memory            | Reduce memory in config.yaml     |

---

**For detailed instructions, see [SETUP.md](docs/SETUP.md)**
