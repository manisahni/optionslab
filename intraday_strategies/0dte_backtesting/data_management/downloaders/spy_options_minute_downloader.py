"""
SPY Options Minute Data Downloader
Downloads minute-level options data from ThetaData API for enhanced strangle analysis
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SPYOptionsMinuteDownloader:
    """Downloads and manages minute-level SPY options data"""
    
    def __init__(self, 
                 base_url: str = "http://127.0.0.1:25510/v2",
                 data_dir: str = "/Users/nish_macbook/0dte/market_data/spy_options_minute",
                 symbol: str = "SPY"):
        self.base_url = base_url
        self.data_dir = data_dir
        self.symbol = symbol
        os.makedirs(data_dir, exist_ok=True)
        
        # Configure for 0DTE focus
        self.strike_range_pct = 0.02  # 2% from spot
        self.max_workers = 4  # Concurrent downloads
        
    def test_connection(self) -> bool:
        """Test connection to ThetaData API"""
        try:
            response = requests.get(f"{self.base_url}/list/dates/option/quote", 
                                  params={"root": self.symbol})
            if response.status_code == 200:
                logger.info("Successfully connected to ThetaData API")
                return True
            else:
                logger.error(f"API connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def get_available_dates(self) -> List[str]:
        """Get list of available dates for options data"""
        try:
            response = requests.get(f"{self.base_url}/list/dates/option/quote",
                                  params={"root": self.symbol})
            if response.status_code == 200:
                dates = response.json()['response']
                return sorted(dates)
            else:
                logger.error(f"Failed to get dates: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting dates: {e}")
            return []
    
    def get_strikes_for_date(self, trade_date: str, spot_price: float) -> List[int]:
        """Get relevant strikes for a given date based on spot price"""
        try:
            # Calculate strike range
            min_strike = int(spot_price * (1 - self.strike_range_pct) * 1000)
            max_strike = int(spot_price * (1 + self.strike_range_pct) * 1000)
            
            # Get all strikes for the date
            response = requests.get(f"{self.base_url}/list/strikes/option/quote",
                                  params={
                                      "root": self.symbol,
                                      "exp": trade_date  # For 0DTE
                                  })
            
            if response.status_code == 200:
                all_strikes = response.json()['response']
                # Filter strikes within range
                relevant_strikes = [s for s in all_strikes 
                                  if min_strike <= s <= max_strike]
                return sorted(relevant_strikes)
            else:
                logger.error(f"Failed to get strikes: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting strikes: {e}")
            return []
    
    def download_minute_data(self, 
                           trade_date: str, 
                           expiration: str,
                           strike: int,
                           right: str) -> Optional[pd.DataFrame]:
        """Download minute data for a specific option"""
        try:
            # Quote data endpoint for minute bars
            params = {
                "root": self.symbol,
                "exp": expiration,
                "strike": strike,
                "right": right,
                "start_date": trade_date,
                "end_date": trade_date,
                "interval": "60000",  # 1 minute in milliseconds
                "use_csv": "true"
            }
            
            # Get quote data
            quote_response = requests.get(f"{self.base_url}/hist/option/quote",
                                        params=params)
            
            # Get Greeks data
            greeks_params = params.copy()
            greeks_response = requests.get(f"{self.base_url}/hist/option/greeks",
                                         params=greeks_params)
            
            if quote_response.status_code == 200 and greeks_response.status_code == 200:
                # Parse CSV data
                quote_df = pd.read_csv(pd.io.common.StringIO(quote_response.text))
                greeks_df = pd.read_csv(pd.io.common.StringIO(greeks_response.text))
                
                # Merge data
                if not quote_df.empty and not greeks_df.empty:
                    df = pd.merge(quote_df, greeks_df, 
                                on=['ms_of_day'], 
                                suffixes=('', '_greeks'))
                    
                    # Add metadata
                    df['symbol'] = self.symbol
                    df['trade_date'] = trade_date
                    df['expiration'] = expiration
                    df['strike'] = strike
                    df['right'] = right
                    
                    return df
                else:
                    return None
            else:
                logger.error(f"Failed to download data for {strike}/{right}: {quote_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading minute data: {e}")
            return None
    
    def download_day_0dte_options(self, trade_date: str) -> pd.DataFrame:
        """Download all 0DTE options data for a specific day"""
        logger.info(f"Downloading 0DTE options for {trade_date}")
        
        # First, get spot price for the day
        spot_price = self.get_spot_price(trade_date)
        if not spot_price:
            logger.error(f"Could not get spot price for {trade_date}")
            return pd.DataFrame()
        
        # Get relevant strikes
        strikes = self.get_strikes_for_date(trade_date, spot_price)
        if not strikes:
            logger.error(f"No strikes found for {trade_date}")
            return pd.DataFrame()
        
        logger.info(f"Found {len(strikes)} strikes near spot {spot_price}")
        
        # Download data for all strikes and rights
        all_data = []
        tasks = []
        
        # Create download tasks
        for strike in strikes:
            for right in ['C', 'P']:
                tasks.append((trade_date, trade_date, strike, right))
        
        # Download in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.download_minute_data, *task): task 
                for task in tasks
            }
            
            for future in tqdm(as_completed(futures), 
                             total=len(futures), 
                             desc=f"Downloading {trade_date}"):
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        all_data.append(df)
                except Exception as e:
                    logger.error(f"Download error: {e}")
        
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df['spot_price'] = spot_price
            return combined_df
        else:
            return pd.DataFrame()
    
    def get_spot_price(self, trade_date: str) -> Optional[float]:
        """Get SPY spot price for a given date"""
        try:
            # Use stock quote endpoint
            params = {
                "root": self.symbol,
                "start_date": trade_date,
                "end_date": trade_date,
                "interval": "900000",  # 15 min bars for efficiency
                "use_csv": "true"
            }
            
            response = requests.get(f"{self.base_url}/hist/stock/quote",
                                  params=params)
            
            if response.status_code == 200:
                df = pd.read_csv(pd.io.common.StringIO(response.text))
                if not df.empty:
                    # Get opening price
                    return df.iloc[0]['open'] / 1000.0  # Convert to dollars
            
            return None
        except Exception as e:
            logger.error(f"Error getting spot price: {e}")
            return None
    
    def save_day_data(self, df: pd.DataFrame, trade_date: str):
        """Save day's options data to parquet"""
        if df.empty:
            return
            
        date_dir = os.path.join(self.data_dir, trade_date)
        os.makedirs(date_dir, exist_ok=True)
        
        file_path = os.path.join(date_dir, f"SPY_options_minute_{trade_date}.parquet")
        df.to_parquet(file_path, index=False)
        logger.info(f"Saved {len(df)} records to {file_path}")
    
    def download_date_range(self, start_date: str, end_date: str):
        """Download options data for a date range"""
        # Get available dates
        available_dates = self.get_available_dates()
        
        # Filter to our range
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        
        dates_to_download = []
        for date_str in available_dates:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            if start <= date_obj <= end:
                # Check if already downloaded
                date_dir = os.path.join(self.data_dir, date_str)
                if not os.path.exists(date_dir):
                    dates_to_download.append(date_str)
        
        logger.info(f"Found {len(dates_to_download)} dates to download")
        
        # Download each date
        for trade_date in dates_to_download:
            try:
                df = self.download_day_0dte_options(trade_date)
                if not df.empty:
                    self.save_day_data(df, trade_date)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error processing {trade_date}: {e}")
                continue
    
    def load_data_for_analysis(self, dates: Optional[List[str]] = None) -> pd.DataFrame:
        """Load downloaded options data for analysis"""
        all_data = []
        
        if dates is None:
            # Load all available dates
            dates = [d for d in os.listdir(self.data_dir) 
                    if os.path.isdir(os.path.join(self.data_dir, d))]
        
        for date_str in sorted(dates):
            file_path = os.path.join(self.data_dir, date_str, 
                                   f"SPY_options_minute_{date_str}.parquet")
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                all_data.append(df)
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            logger.info(f"Loaded {len(combined)} option quotes from {len(dates)} days")
            return combined
        else:
            return pd.DataFrame()


def main():
    """Example usage"""
    downloader = SPYOptionsMinuteDownloader()
    
    # Test connection
    if not downloader.test_connection():
        print("Failed to connect to ThetaData API. Make sure it's running.")
        return
    
    # Download last 5 trading days as example
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"Downloading 0DTE options data from {start_date.strftime('%Y%m%d')} to {end_date.strftime('%Y%m%d')}")
    
    downloader.download_date_range(
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d")
    )
    
    print("Download complete!")


if __name__ == "__main__":
    main()