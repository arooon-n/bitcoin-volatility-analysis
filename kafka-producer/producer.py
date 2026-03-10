#!/usr/bin/env python3
"""
Bitcoin Volatility Analysis - Kafka Producer

This script continuously fetches live Bitcoin price data from the CryptoCompare API
and publishes it to a Kafka topic for real-time stream processing.

Features:
- Fetches comprehensive price data every 10 seconds
- Publishes to Kafka with guaranteed delivery (acks='all')
- Robust error handling and logging
- Graceful shutdown on Ctrl+C
"""

import json
import time
import sys
import logging
from datetime import datetime
from pathlib import Path

import requests
import yaml
from kafka import KafkaProducer
from kafka.errors import KafkaError


class BitcoinProducer:
    """Fetches Bitcoin price data and publishes to Kafka."""
    
    def __init__(self, config_path):
        """
        Initialize the Bitcoin producer.
        
        Args:
            config_path (Path): Path to configuration YAML file
        """
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s — %(levelname)s — %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.api_base_url = self.config['api']['base_url']
        self.api_key = self.config['api']['key']
        self.fetch_interval = self.config['api']['fetch_interval_seconds']
        self.kafka_servers = self.config['kafka']['bootstrap_servers']
        self.kafka_topic = self.config['kafka']['topic_prices']
        
        # Validate API key
        if self.api_key == "YOUR_API_KEY_HERE":
            self.logger.error("API key not configured in config/config.yaml")
            self.logger.error("Get a free key at: https://www.cryptocompare.com/cryptopian/api-keys")
            sys.exit(1)
        
        # Initialize Kafka producer
        self.producer = self._create_producer()
        
        self.logger.info("="*60)
        self.logger.info("  Bitcoin Kafka Producer Initialized")
        self.logger.info("="*60)
        self.logger.info(f"API Base URL: {self.api_base_url}")
        self.logger.info(f"Kafka Broker: {self.kafka_servers}")
        self.logger.info(f"Kafka Topic: {self.kafka_topic}")
        self.logger.info(f"Fetch Interval: {self.fetch_interval} seconds")
        self.logger.info("="*60)
    
    def _create_producer(self):
        """
        Create and configure Kafka producer.
        
        Returns:
            KafkaProducer: Configured producer instance
        """
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,  # Retry up to 3 times on failure
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                compression_type='gzip',  # Compress messages
                api_version=(2, 8, 1)
            )
            self.logger.info("✓ Kafka producer created successfully")
            return producer
        except Exception as e:
            self.logger.error(f"Failed to create Kafka producer: {str(e)}")
            raise
    
    def fetch_price(self):
        """
        Fetch current Bitcoin price data from CryptoCompare API.
        
        Returns:
            dict: Price data with all relevant fields, or None on error
        """
        try:
            url = f"{self.api_base_url}/data/pricemultifull"
            params = {
                'fsyms': 'BTC',
                'tsyms': 'USD',
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Response' in data and data['Response'] == 'Error':
                self.logger.error(f"API Error: {data.get('Message', 'Unknown error')}")
                return None
            
            # Extract relevant data
            raw_data = data['RAW']['BTC']['USD']
            
            # Build message
            message = {
                'timestamp': int(time.time()),
                'datetime': datetime.utcnow().isoformat() + 'Z',
                'price': float(raw_data.get('PRICE', 0)),
                'open24h': float(raw_data.get('OPEN24HOUR', 0)),
                'high24h': float(raw_data.get('HIGH24HOUR', 0)),
                'low24h': float(raw_data.get('LOW24HOUR', 0)),
                'volume24h': float(raw_data.get('VOLUME24HOUR', 0)),
                'volumeto24h': float(raw_data.get('VOLUME24HOURTO', 0)),
                'change24h': float(raw_data.get('CHANGE24HOUR', 0)),
                'changepct24h': float(raw_data.get('CHANGEPCT24HOUR', 0)),
                'market_cap': float(raw_data.get('MKTCAP', 0)),
                'supply': float(raw_data.get('SUPPLY', 0))
            }
            
            return message
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error fetching price data: {str(e)}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            self.logger.error(f"Error parsing API response: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in fetch_price: {str(e)}")
            return None
    
    def send_to_kafka(self, message):
        """
        Send message to Kafka topic.
        
        Args:
            message (dict): Message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            future = self.producer.send(self.kafka_topic, value=message)
            
            # Block until message is sent
            record_metadata = future.get(timeout=10)
            
            self.logger.info(
                f"✓ Sent to Kafka — Price: ${message['price']:,.2f} | "
                f"Volume24h: ${message['volume24h']:,.0f} | "
                f"Partition: {record_metadata.partition} | "
                f"Offset: {record_metadata.offset}"
            )
            
            return True
            
        except KafkaError as e:
            self.logger.error(f"Kafka error while sending message: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in send_to_kafka: {str(e)}")
            return False
    
    def run(self):
        """
        Main loop: fetch price data and send to Kafka continuously.
        """
        self.logger.info("")
        self.logger.info("Starting data collection... (Press Ctrl+C to stop)")
        self.logger.info("")
        
        message_count = 0
        error_count = 0
        
        try:
            while True:
                # Fetch price data
                message = self.fetch_price()
                
                if message:
                    # Send to Kafka
                    success = self.send_to_kafka(message)
                    
                    if success:
                        message_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1
                    self.logger.warning("Skipping this cycle due to fetch error")
                
                # Log statistics every 10 messages
                if message_count % 10 == 0 and message_count > 0:
                    self.logger.info(
                        f"Statistics — Messages sent: {message_count} | "
                        f"Errors: {error_count} | "
                        f"Success rate: {message_count/(message_count+error_count)*100:.1f}%"
                    )
                
                # Wait before next fetch
                time.sleep(self.fetch_interval)
                
        except KeyboardInterrupt:
            self.logger.info("")
            self.logger.info("="*60)
            self.logger.info("  Shutting down producer...")
            self.logger.info("="*60)
            self.logger.info(f"Total messages sent: {message_count}")
            self.logger.info(f"Total errors: {error_count}")
            self.logger.info("="*60)
            self.producer.close()
            self.logger.info("✓ Producer closed successfully")
            sys.exit(0)


def main():
    """Main entry point."""
    # Get config path
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"ERROR: Configuration file not found at {config_path}")
        sys.exit(1)
    
    try:
        producer = BitcoinProducer(config_path)
        producer.run()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
