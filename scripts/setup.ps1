# Bitcoin Volatility Analysis System - PowerShell Setup Helper
# For users who prefer PowerShell over Git Bash

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Bitcoin Volatility Analysis Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[1/8] Checking prerequisites..." -ForegroundColor Yellow

$prerequisites = @{
    "Docker" = "docker --version"
    "Java" = "java -version"
    "Scala" = "scala -version"
    "sbt" = "sbt --version"
    "Python" = "python --version"
}

$allPresent = $true
foreach ($tool in $prerequisites.Keys) {
    try {
        $null = Invoke-Expression $prerequisites[$tool] 2>&1
        Write-Host "  [OK] $tool installed" -ForegroundColor Green
    } catch {
        Write-Host "  [X] $tool NOT found" -ForegroundColor Red
        $allPresent = $false
    }
}

if (-not $allPresent) {
    Write-Host ""
    Write-Host "ERROR: Missing prerequisites. Please install all required tools." -ForegroundColor Red
    Write-Host "See docs/SETUP.md for installation links." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/8] Creating data directories..." -ForegroundColor Yellow

$dataDir = "d:\College\Sem6\BigData\bitcoin003\data"
New-Item -ItemType Directory -Force -Path "$dataDir\namenode" | Out-Null
New-Item -ItemType Directory -Force -Path "$dataDir\datanode" | Out-Null
New-Item -ItemType Directory -Force -Path "$dataDir\kafka" | Out-Null

Write-Host "  [OK] Data directories created" -ForegroundColor Green
Write-Host ""

Write-Host "[3/8] Starting Docker containers..." -ForegroundColor Yellow
Write-Host "  This may take a few moments..." -ForegroundColor Gray

docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "  [X] Failed to start Docker containers" -ForegroundColor Red
    exit 1
}

Write-Host "  [OK] Docker containers started" -ForegroundColor Green
Write-Host "  Waiting 60 seconds for services to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 60

Write-Host ""
Write-Host "[4/8] Setting up HDFS directories..." -ForegroundColor Yellow

# Convert script to Windows-compatible commands
docker exec namenode hdfs dfs -mkdir -p /bitcoin
docker exec namenode hdfs dfs -mkdir -p /bitcoin/historical
docker exec namenode hdfs dfs -mkdir -p /bitcoin/checkpoints/stream
docker exec namenode hdfs dfs -mkdir -p /bitcoin/checkpoints/latest
docker exec namenode hdfs dfs -mkdir -p /bitcoin/analysis
docker exec namenode hdfs dfs -chmod -R 777 /bitcoin

Write-Host "  [OK] HDFS directories created" -ForegroundColor Green
Write-Host ""

Write-Host "[5/8] Setting up Kafka topics..." -ForegroundColor Yellow

docker exec kafka kafka-topics.sh `
    --bootstrap-server localhost:9092 `
    --create `
    --if-not-exists `
    --topic bitcoin-prices `
    --partitions 3 `
    --replication-factor 1

Write-Host "  [OK] Kafka topic created" -ForegroundColor Green
Write-Host ""

Write-Host "[6/8] Installing Python dependencies..." -ForegroundColor Yellow

pip install -r scripts\requirements.txt --quiet
pip install -r kafka-producer\requirements.txt --quiet
pip install -r dashboard\requirements.txt --quiet

Write-Host "  [OK] Python dependencies installed" -ForegroundColor Green
Write-Host ""

Write-Host "[7/8] Building Spark jobs..." -ForegroundColor Yellow
Write-Host "  This will take 3-5 minutes on first run..." -ForegroundColor Gray

Push-Location spark-jobs
sbt assembly
Pop-Location

if ($LASTEXITCODE -ne 0) {
    Write-Host "  [X] Failed to build Spark jobs" -ForegroundColor Red
    exit 1
}

Write-Host "  [OK] Spark JAR built successfully" -ForegroundColor Green
Write-Host ""

Write-Host "[8/8] Configuration check..." -ForegroundColor Yellow

$configContent = Get-Content config\config.yaml -Raw
if ($configContent -match "YOUR_API_KEY_HERE") {
    Write-Host "  [!] WARNING: API key not configured!" -ForegroundColor Yellow
    Write-Host "  Please edit config\config.yaml and set your CryptoCompare API key" -ForegroundColor Yellow
    Write-Host "  Get a free key at: https://www.cryptocompare.com/cryptopian/api-keys" -ForegroundColor Yellow
} else {
    Write-Host "  [OK] API key configured" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Optional: Download historical data (10-20 minutes):" -ForegroundColor Yellow
Write-Host "  python scripts\download_historical_data.py" -ForegroundColor White
Write-Host ""

Write-Host "To start the system, run these commands in separate terminals:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Terminal 1 (Producer):" -ForegroundColor Cyan
Write-Host "  cd kafka-producer" -ForegroundColor White
Write-Host "  python producer.py" -ForegroundColor White
Write-Host ""
Write-Host "Terminal 2 (Streaming):" -ForegroundColor Cyan
Write-Host "  bash scripts/start_streaming.sh" -ForegroundColor White
Write-Host ""
Write-Host "Terminal 3 (Dashboard):" -ForegroundColor Cyan
Write-Host "  cd dashboard" -ForegroundColor White
Write-Host "  python app.py" -ForegroundColor White
Write-Host ""
Write-Host "Then open: http://localhost:8050" -ForegroundColor Green
Write-Host ""
