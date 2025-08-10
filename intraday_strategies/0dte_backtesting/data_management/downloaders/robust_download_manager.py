"""
Robust Download Manager for SPY Options
Handles timeouts, retries, and connection issues
"""

import os
import sys
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Optional
import socket

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RobustDownloadManager:
    """Manages downloads with retry logic and connection handling"""
    
    def __init__(self):
        self.base_url = "http://localhost:25510/v2"
        self.data_dir = "/Users/nish_macbook/0dte/market_data/spy_options_minute"
        self.timeout = 30  # seconds
        self.max_retries = 3
        self.retry_delay = 5
        
    def test_connection(self) -> bool:
        """Test if ThetaData is responding"""
        try:
            response = requests.get(
                f"{self.base_url}/list/roots/option/quote",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def wait_for_connection(self, max_wait: int = 60):
        """Wait for ThetaData to be responsive"""
        logger.info("Checking ThetaData connection...")
        
        start = time.time()
        while time.time() - start < max_wait:
            if self.test_connection():
                logger.info("✅ ThetaData is responsive")
                return True
            
            logger.info("⏳ Waiting for ThetaData to respond...")
            time.sleep(5)
        
        logger.error("❌ ThetaData is not responding")
        return False
    
    def make_request(self, endpoint: str, params: dict = None) -> Optional[requests.Response]:
        """Make API request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"Request failed with status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def get_trading_days(self) -> List[str]:
        """Get trading days with our SPY stock data"""
        # Use the dates from our existing stock data
        stock_dir = "/Users/nish_macbook/0dte/market_data/spy_stock_data/SPY"
        trading_days = []
        
        if os.path.exists(stock_dir):
            for folder in sorted(os.listdir(stock_dir)):
                if folder.isdigit() and len(folder) == 8:
                    trading_days.append(folder)
        
        # Filter to our date range
        trading_days = [d for d in trading_days if "20250505" <= d <= "20250801"]
        
        logger.info(f"Found {len(trading_days)} trading days from stock data")
        return trading_days
    
    def download_single_day_simple(self, date: str):
        """Simplified download for a single day - just get EOD data first"""
        logger.info(f"\nProcessing {date}...")
        
        # Check if already done
        output_file = os.path.join(self.data_dir, date, f"SPY_options_{date}_simple.json")
        if os.path.exists(output_file):
            logger.info(f"  Already downloaded")
            return
        
        # Try to get EOD data for this date
        response = self.make_request(
            "/bulk_hist/option/eod",
            params={
                "root": "SPY",
                "exp": 0,  # All expirations
                "start_date": date,
                "end_date": date,
                "use_csv": "true"
            }
        )
        
        if response and response.text:
            # Save the data
            os.makedirs(os.path.join(self.data_dir, date), exist_ok=True)
            
            # Parse CSV
            import io
            try:
                df = pd.read_csv(io.StringIO(response.text))
                
                # Filter to 0DTE
                if 'expiration' in df.columns:
                    df['exp_date'] = pd.to_datetime(df['expiration'])
                    df['trade_date'] = pd.to_datetime(date, format='%Y%m%d')
                    df['dte'] = (df['exp_date'] - df['trade_date']).dt.days
                    
                    # Keep only 0DTE and 1DTE
                    df_filtered = df[df['dte'].isin([0, 1])]
                    
                    logger.info(f"  Got {len(df_filtered)} contracts (0DTE/1DTE)")
                    
                    # Save
                    df_filtered.to_parquet(
                        output_file.replace('.json', '.parquet'),
                        compression='snappy'
                    )
                else:
                    logger.warning(f"  Unexpected data format")
                    
            except Exception as e:
                logger.error(f"  Error parsing data: {e}")
        else:
            logger.warning(f"  No data received")
    
    def run_simplified_download(self):
        """Run a simplified download process"""
        logger.info("="*60)
        logger.info("SIMPLIFIED SPY OPTIONS DOWNLOAD")
        logger.info("="*60)
        
        # Check connection
        if not self.wait_for_connection():
            logger.error("Cannot connect to ThetaData. Please check if it's running.")
            return
        
        # Get trading days
        trading_days = self.get_trading_days()
        
        if not trading_days:
            logger.error("No trading days found")
            return
        
        logger.info(f"Will download {len(trading_days)} days")
        logger.info(f"Date range: {trading_days[0]} to {trading_days[-1]}")
        
        # Download each day
        success = 0
        failed = 0
        
        for i, date in enumerate(trading_days):
            logger.info(f"\nDay {i+1}/{len(trading_days)}")
            
            try:
                self.download_single_day_simple(date)
                success += 1
                
                # Brief pause between requests
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed on {date}: {e}")
                failed += 1
                
                # Longer pause after error
                time.sleep(5)
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("="*60)
        logger.info(f"Successful: {success}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Data location: {self.data_dir}")


def main():
    """Run the robust download"""
    manager = RobustDownloadManager()
    
    print("\nROBUST SPY OPTIONS DOWNLOADER")
    print("="*50)
    print("This will download EOD options data for backtesting")
    print("Using a simplified approach to avoid timeouts")
    print("="*50)
    
    response = input("\nProceed? (y/n): ")
    
    if response.lower() == 'y':
        manager.run_simplified_download()
    else:
        print("Cancelled.")


if __name__ == "__main__":
    main()