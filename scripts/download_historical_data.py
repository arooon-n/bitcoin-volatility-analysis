#!/usr/bin/env python3
"""
Bitcoin Volatility Analysis - Historical Data Download Script

This script downloads historical Bitcoin price data from CryptoCompare API
and uploads it to HDFS in Parquet format. This is the primary strategy for
meeting the 3 GB data requirement.

Data downloaded:
- 90 days of minute-level BTC OHLCV data (~130,000 records)
- 3 years of hourly BTC, ETH, LTC data (~78,000 records)
- Additional coins if needed to reach 3 GB threshold
"""

import os
import sys
import time
import subprocess
import requests
import pandas as pd
import yaml
from datetime import datetime, timedelta
from pathlib import Path

# Constants
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "config.yaml"
TMP_DIR = Path("/tmp/bitcoin_historical")


class HistoricalDataDownloader:
    """Downloads historical cryptocurrency data and uploads to HDFS."""
    
    def __init__(self, config_path):
        """
        Initialize the downloader.
        
        Args:
            config_path (Path): Path to configuration YAML file
        """
        print("="*60)
        print("  Bitcoin Volatility Analysis")
        print("  Historical Data Download")
        print("="*60)
        print()
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.api_base_url = self.config['api']['base_url']
        self.api_key = self.config['api']['key']
        self.hdfs_namenode = self.config['hdfs']['namenode']
        self.hdfs_historical_path = self.config['hdfs']['paths']['historical']
        
        # Validate API key
        if self.api_key == "YOUR_API_KEY_HERE":
            print("ERROR: Please set your CryptoCompare API key in config/config.yaml")
            print("Get a free key at: https://www.cryptocompare.com/cryptopian/api-keys")
            sys.exit(1)
        
        # Create temporary directory
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✓ Temporary directory: {TMP_DIR}")
        print(f"✓ HDFS target: {self.hdfs_namenode}{self.hdfs_historical_path}")
        print()
    
    def download_minute_data(self, symbol, days=90):
        """
        Download minute-level OHLCV data.
        
        Args:
            symbol (str): Cryptocurrency symbol (e.g., 'BTC')
            days (int): Number of days of historical data
            
        Returns:
            pd.DataFrame: Downloaded data
        """
        print(f"[DOWNLOAD] Fetching {days} days of minute data for {symbol}...")
        
        all_data = []
        limit = 2000  # Max records per API call
        total_minutes = days * 24 * 60
        total_calls = (total_minutes // limit) + 1
        
        # Calculate starting timestamp
        end_time = int(time.time())
        
        for call_num in range(total_calls):
            try:
                url = f"{self.api_base_url}/data/v2/histominute"
                params = {
                    'fsym': symbol,
                    'tsym': 'USD',
                    'limit': limit,
                    'toTs': end_time,
                    'api_key': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if data['Response'] != 'Success':
                    print(f"  WARNING: API returned error: {data.get('Message', 'Unknown error')}")
                    break
                
                records = data['Data']['Data']
                all_data.extend(records)
                
                # Progress indicator
                progress = (call_num + 1) / total_calls * 100
                print(f"  Progress: {progress:.1f}% ({len(all_data)} records)", end='\r')
                
                # Update end_time for next batch (go backwards in time)
                if records:
                    end_time = records[0]['time'] - 60
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\n  ERROR during API call {call_num + 1}: {str(e)}")
                break
        
        print(f"\n✓ Downloaded {len(all_data)} minute records for {symbol}")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        df['symbol'] = symbol
        df['interval'] = 'minute'
        
        return df
    
    def download_hourly_data(self, symbol, days=1095):
        """
        Download hourly OHLCV data (default: 3 years).
        
        Args:
            symbol (str): Cryptocurrency symbol
            days (int): Number of days of historical data
            
        Returns:
            pd.DataFrame: Downloaded data
        """
        print(f"[DOWNLOAD] Fetching {days} days ({days//365} years) of hourly data for {symbol}...")
        
        all_data = []
        limit = 2000
        total_hours = days * 24
        total_calls = (total_hours // limit) + 1
        
        end_time = int(time.time())
        
        for call_num in range(total_calls):
            try:
                url = f"{self.api_base_url}/data/v2/histohour"
                params = {
                    'fsym': symbol,
                    'tsym': 'USD',
                    'limit': limit,
                    'toTs': end_time,
                    'api_key': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if data['Response'] != 'Success':
                    print(f"  WARNING: API returned error: {data.get('Message', 'Unknown error')}")
                    break
                
                records = data['Data']['Data']
                all_data.extend(records)
                
                progress = (call_num + 1) / total_calls * 100
                print(f"  Progress: {progress:.1f}% ({len(all_data)} records)", end='\r')
                
                if records:
                    end_time = records[0]['time'] - 3600
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\n  ERROR during API call {call_num + 1}: {str(e)}")
                break
        
        print(f"\n✓ Downloaded {len(all_data)} hourly records for {symbol}")
        
        df = pd.DataFrame(all_data)
        df['symbol'] = symbol
        df['interval'] = 'hourly'
        
        return df
    
    def prepare_dataframe(self, df):
        """
        Prepare DataFrame for storage: add datetime and date columns.
        
        Args:
            df (pd.DataFrame): Raw data
            
        Returns:
            pd.DataFrame: Prepared data
        """
        # Convert Unix timestamp to datetime
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df['date'] = df['datetime'].dt.date.astype(str)
        
        # Rename columns to match expected schema
        df = df.rename(columns={
            'time': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'price',
            'volumefrom': 'volume',
            'volumeto': 'volumeto'
        })
        
        # Select and order columns
        columns = [
            'timestamp', 'datetime', 'date', 'symbol', 'interval',
            'price', 'open', 'high', 'low', 'volume', 'volumeto'
        ]
        
        return df[columns]
    
    def save_to_parquet(self, df, filename):
        """
        Save DataFrame to Parquet file.
        
        Args:
            df (pd.DataFrame): Data to save
            filename (str): Output filename
            
        Returns:
            Path: Path to saved file
        """
        filepath = TMP_DIR / filename
        df.to_parquet(filepath, engine='pyarrow', compression='snappy', index=False)
        
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"✓ Saved to {filepath} ({file_size_mb:.2f} MB)")
        
        return filepath
    
    def upload_to_hdfs(self, local_path, hdfs_path):
        """
        Upload file to HDFS using Docker exec.
        
        Args:
            local_path (Path): Local file path
            hdfs_path (str): HDFS destination path
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"[UPLOAD] Uploading {local_path.name} to HDFS...")
            
            # Copy file into Docker container first
            container_path = f"/tmp/{local_path.name}"
            subprocess.run(
                ['docker', 'cp', str(local_path), f'namenode:{container_path}'],
                check=True,
                capture_output=True
            )
            
            # Then upload from container to HDFS
            subprocess.run(
                ['docker', 'exec', 'namenode', 'hdfs', 'dfs', '-put', '-f', 
                 container_path, hdfs_path],
                check=True,
                capture_output=True
            )
            
            # Check file size in HDFS
            result = subprocess.run(
                ['docker', 'exec', 'namenode', 'hdfs', 'dfs', '-du', '-h', hdfs_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            print(f"✓ Upload complete. HDFS size: {result.stdout.strip()}")
            
            # Clean up container temp file
            subprocess.run(
                ['docker', 'exec', 'namenode', 'rm', '-f', container_path],
                capture_output=True
            )
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"  ERROR during upload: {e.stderr.decode() if e.stderr else str(e)}")
            return False
    
    def get_hdfs_directory_size(self, hdfs_path):
        """
        Get total size of HDFS directory.
        
        Args:
            hdfs_path (str): HDFS directory path
            
        Returns:
            tuple: (size_bytes, size_gb, size_str)
        """
        try:
            result = subprocess.run(
                ['docker', 'exec', 'namenode', 'hdfs', 'dfs', '-du', '-s', hdfs_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output: "size_bytes replica_size path"
            size_bytes = int(result.stdout.strip().split()[0])
            size_gb = size_bytes / (1024**3)
            
            # Get human-readable size
            result_h = subprocess.run(
                ['docker', 'exec', 'namenode', 'hdfs', 'dfs', '-du', '-s', '-h', hdfs_path],
                capture_output=True,
                text=True,
                check=True
            )
            size_str = result_h.stdout.strip().split()[0]
            
            return size_bytes, size_gb, size_str
            
        except Exception as e:
            print(f"  ERROR checking HDFS size: {str(e)}")
            return 0, 0, "0 B"
    
    def run(self):
        """Execute the complete download and upload process."""
        print("\n" + "="*60)
        print("  PHASE 1: DATA DOWNLOAD")
        print("="*60 + "\n")
        
        datasets = []
        
        # Download BTC minute data (90 days)
        btc_minute_df = self.download_minute_data('BTC', days=90)
        btc_minute_df = self.prepare_dataframe(btc_minute_df)
        datasets.append(('btc_minute_90d.parquet', btc_minute_df))
        print()
        
        # Download BTC hourly data (3 years)
        btc_hourly_df = self.download_hourly_data('BTC', days=1095)
        btc_hourly_df = self.prepare_dataframe(btc_hourly_df)
        datasets.append(('btc_hourly_3y.parquet', btc_hourly_df))
        print()
        
        # Download ETH hourly data (3 years) for additional volume
        eth_hourly_df = self.download_hourly_data('ETH', days=1095)
        eth_hourly_df = self.prepare_dataframe(eth_hourly_df)
        datasets.append(('eth_hourly_3y.parquet', eth_hourly_df))
        print()
        
        # Download LTC hourly data (3 years) for additional volume
        ltc_hourly_df = self.download_hourly_data('LTC', days=1095)
        ltc_hourly_df = self.prepare_dataframe(ltc_hourly_df)
        datasets.append(('ltc_hourly_3y.parquet', ltc_hourly_df))
        print()
        
        print("\n" + "="*60)
        print("  PHASE 2: SAVE TO PARQUET")
        print("="*60 + "\n")
        
        local_files = []
        for filename, df in datasets:
            filepath = self.save_to_parquet(df, filename)
            local_files.append(filepath)
            print()
        
        print("\n" + "="*60)
        print("  PHASE 3: UPLOAD TO HDFS")
        print("="*60 + "\n")
        
        for local_path in local_files:
            hdfs_path = f"{self.hdfs_historical_path}/{local_path.name}"
            self.upload_to_hdfs(local_path, hdfs_path)
            print()
        
        print("\n" + "="*60)
        print("  PHASE 4: VERIFICATION")
        print("="*60 + "\n")
        
        # Calculate total size
        size_bytes, size_gb, size_str = self.get_hdfs_directory_size(self.hdfs_historical_path)
        
        print(f"Total HDFS data size: {size_str} ({size_gb:.3f} GB)")
        print()
        
        # Check if 3 GB threshold is met
        threshold_gb = 3.0
        if size_gb >= threshold_gb:
            print(f"✓ SUCCESS: Data size ({size_gb:.3f} GB) meets the {threshold_gb} GB requirement!")
        else:
            shortfall = threshold_gb - size_gb
            print(f"⚠ WARNING: Data size ({size_gb:.3f} GB) is below {threshold_gb} GB requirement.")
            print(f"  Shortfall: {shortfall:.3f} GB")
            print(f"  Consider downloading additional coins or longer time periods.")
        
        print("\n" + "="*60)
        print("  ✓ HISTORICAL DATA DOWNLOAD COMPLETE")
        print("="*60 + "\n")
        
        print("Next steps:")
        print("  1. Start Kafka producer: python kafka-producer/producer.py")
        print("  2. Start Spark streaming: bash scripts/start_streaming.sh")
        print("  3. Start dashboard: python dashboard/app.py")
        print()


def main():
    """Main entry point."""
    try:
        downloader = HistoricalDataDownloader(CONFIG_PATH)
        downloader.run()
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
