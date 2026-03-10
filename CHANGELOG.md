# Changelog

All notable changes to the Bitcoin Volatility Analysis System will be documented in this file.

## [1.0.0] - 2024-03-15

### Initial Release

#### Added

- **Kafka Producer** (Python): Real-time Bitcoin price ingestion from CryptoCompare API
- **Spark Streaming** (Scala): Volatility calculation with log returns and rolling windows
- **Batch Analysis** (Scala): Daily statistics, hourly patterns, and spike detection
- **Web Dashboard** (Python Dash): Real-time visualization with auto-refresh
- **Docker Compose**: Complete infrastructure setup (Hadoop, Kafka, Spark)
- **HDFS Storage**: Parquet format with date partitioning
- **Historical Data Downloader**: Script to bulk-load 3+ GB of data

#### Features

- Log return calculation: `ln(P_t / P_t-1)`
- Rolling volatility: 1-hour and 24-hour windows
- Moving averages: 1-hour and 24-hour trends
- Real-time KPI cards: price, volatility, volume, timestamp
- Interactive charts: price + MAs, volatility comparison, volume bars
- Auto-refresh: Dashboard updates every 10 seconds
- Resource-optimized: Configured for 4-6 GB RAM usage

#### Documentation

- README.md: Project overview and quick start
- docs/SETUP.md: Detailed setup instructions with troubleshooting
- docs/ARCHITECTURE.md: System design and technology choices
- docs/USAGE.md: Operational guide with demo script
- QUICKSTART.md: Condensed setup for fast start

#### Configuration

- Centralized config.yaml for all parameters
- Docker Compose for service orchestration
- Idempotent setup scripts (HDFS, Kafka)
- Windows 11 optimized (D:\ drive for data storage)

#### Academic Requirements Met

- **Volume**: 3+ GB data in HDFS (historical + streaming)
- **Velocity**: 10-second ingestion intervals, real-time processing
- **Variety**: JSON (Kafka), Parquet (HDFS), multiple data types
- **Veracity**: Error handling, null safety, checkpointing, validation

### Infrastructure

- Apache Kafka 3.9.0 with 3 partitions
- Apache Spark 3.5.8 with Structured Streaming
- Hadoop HDFS 3.2.1 with Parquet storage
- Python 3.11 for producer and dashboard
- Scala 2.13.14 for Spark jobs
- Docker containerization for reproducibility

### Known Limitations

- Single-node deployment (not horizontally scalable)
- No authentication/encryption (development only)
- Windows-specific paths (requires Git Bash for .sh scripts)
- Free API tier rate limits (100k calls/month)
- Development-grade resource limits (not production-hardened)

---

## Future Enhancements (Roadmap)

### [1.1.0] - Planned

- [ ] Multi-cryptocurrency support (ETH, LTC, XRP, ADA, BNB)
- [ ] Cross-asset correlation analysis
- [ ] Email/Slack alerts for volatility spikes
- [ ] PDF report generation

### [1.2.0] - Planned

- [ ] GARCH volatility forecasting models
- [ ] Anomaly detection (Isolation Forest)
- [ ] Sentiment analysis integration (Twitter API)
- [ ] Portfolio volatility modeling

### [2.0.0] - Planned

- [ ] Kubernetes deployment manifests
- [ ] Horizontal scaling (multi-broker Kafka, multi-worker Spark)
- [ ] Authentication and SSL/TLS encryption
- [ ] Production-grade monitoring (Prometheus + Grafana)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Comprehensive test suite (unit, integration, end-to-end)

---

## Version History

- **1.0.0** (2024-03-15): Initial release for academic project
