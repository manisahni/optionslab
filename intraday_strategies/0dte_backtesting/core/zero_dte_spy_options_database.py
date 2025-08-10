"""
Minute-Level 0DTE SPY Options Database Manager
Comprehensive tool for downloading, storing, and analyzing minute-by-minute 0DTE SPY options data
Specifically designed for intraday strangle strategy backtesting

Data Type: OPTIONS data with minute-level granularity
- ~50 option contracts tracked every minute
- ~19,550 records per trading day
- Includes bid/ask, Greeks, implied volatility
"""

import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import StringIO
import time
import json
from tqdm import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple, Union
import pyarrow.parquet as pq
import pyarrow as pa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MinuteLevelOptionsDB')


class ZeroDTESPYOptionsDatabase:
    """
    Database manager for 0DTE SPY options data
    Handles download, storage, and analysis of minute-level options data
    """
    
    def __init__(self, data_dir: str = "/Users/nish_macbook/0dte/market_data/options_data/spy_0dte_minute"):
        """
        Initialize Zero DTE database
        
        Args:
            data_dir: Directory to store all 0DTE options data
        """
        self.data_dir = data_dir
        self.base_url = "http://localhost:25503"
        self.symbol = "SPY"
        
        # 0DTE specific configuration
        self.strike_range_pct = 0.02  # ±2% from spot for 0DTE
        self.max_workers = 3
        self.retry_attempts = 3
        self.retry_delay = 2
        
        # Create directories
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "metadata"), exist_ok=True)
        
        # Load metadata if exists
        self.metadata_file = os.path.join(self.data_dir, "metadata", "zero_dte_database_info.json")
        self.metadata = self._load_metadata()
        
        logger.info(f"Initialized ZeroDTESPYOptionsDatabase at {self.data_dir}")
    
    def _load_metadata(self) -> dict:
        """Load database metadata"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            "created": datetime.now().isoformat(),
            "last_updated": None,
            "total_days": 0,
            "total_records": 0,
            "date_range": {"start": None, "end": None},
            "downloaded_dates": []
        }
    
    def _save_metadata(self):
        """Save database metadata"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _get_contracts_for_date(self, date: str) -> pd.DataFrame:
        """Get all SPY contracts available on a specific date"""
        url = f"{self.base_url}/v3/option/list/contracts/quote"
        params = {"symbol": self.symbol, "date": date}
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    df = pd.read_csv(StringIO(response.text))
                    
                    # Calculate DTE
                    df['expiration'] = pd.to_datetime(df['expiration'])
                    df['trade_date'] = pd.to_datetime(date, format='%Y%m%d')
                    df['dte'] = (df['expiration'] - df['trade_date']).dt.days
                    
                    return df
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    continue
                logger.error(f"Error getting contracts for {date}: {e}")
        
        return pd.DataFrame()
    
    def _download_contract_data(self, contract: dict, date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Download quotes and Greeks for a single contract"""
        # Quote parameters
        base_params = {
            "symbol": contract['symbol'],
            "expiration": contract['expiration'],
            "strike": f"{contract['strike']:.3f}",
            "right": contract['right'].lower(),
            "date": date,
            "interval": "1m",
            "format": "csv"
        }
        
        quotes_df = pd.DataFrame()
        greeks_df = pd.DataFrame()
        
        for attempt in range(self.retry_attempts):
            try:
                # Get quotes
                quotes_url = f"{self.base_url}/v3/option/history/quote"
                quotes_response = requests.get(quotes_url, params=base_params, timeout=30)
                if quotes_response.status_code == 200:
                    quotes_df = pd.read_csv(StringIO(quotes_response.text))
                
                # Get Greeks with underlying
                greeks_url = f"{self.base_url}/v3/option/history/greeks/first_order"
                greeks_response = requests.get(greeks_url, params=base_params, timeout=30)
                if greeks_response.status_code == 200:
                    greeks_df = pd.read_csv(StringIO(greeks_response.text))
                
                if not quotes_df.empty and not greeks_df.empty:
                    break
                    
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                    continue
                logger.warning(f"Error downloading {contract['strike']}{contract['right'][0]}: {e}")
        
        return quotes_df, greeks_df
    
    def download_zero_dte_options_for_date(self, date: str, force: bool = False) -> int:
        """
        Download all 0DTE options for a specific date
        
        Args:
            date: Date in YYYYMMDD format
            force: Force re-download even if data exists
            
        Returns:
            Number of records downloaded
        """
        # Check if already downloaded
        date_file = os.path.join(self.data_dir, date, f"zero_dte_spy_{date}.parquet")
        if os.path.exists(date_file) and not force:
            logger.info(f"Date {date} already downloaded, skipping...")
            return 0
        
        logger.info(f"\nDownloading 0DTE options for {date}...")
        
        # Get all contracts
        contracts_df = self._get_contracts_for_date(date)
        if contracts_df.empty:
            logger.warning(f"No contracts found for {date}")
            return 0
        
        # Filter to 0DTE only
        zero_dte = contracts_df[contracts_df['dte'] == 0]
        if zero_dte.empty:
            logger.warning(f"No 0DTE contracts for {date}")
            return 0
        
        # Get spot price from first contract's underlying
        test_contract = zero_dte.iloc[0]
        _, test_greeks = self._download_contract_data({
            'symbol': test_contract['symbol'],
            'expiration': test_contract['expiration'].strftime('%Y%m%d'),
            'strike': test_contract['strike'],
            'right': test_contract['right']
        }, date)
        
        if test_greeks.empty or 'underlying_price' not in test_greeks.columns:
            logger.error(f"Could not get underlying price for {date}")
            return 0
        
        spot_price = test_greeks['underlying_price'].iloc[0] / 100  # Convert from cents
        logger.info(f"Spot price: ${spot_price:.2f}")
        
        # Filter to near-money strikes
        min_strike = spot_price * (1 - self.strike_range_pct)
        max_strike = spot_price * (1 + self.strike_range_pct)
        
        near_money_zero_dte = zero_dte[
            (zero_dte['strike'] >= min_strike) & 
            (zero_dte['strike'] <= max_strike)
        ]
        
        logger.info(f"Found {len(near_money_zero_dte)} near-money 0DTE contracts")
        
        # Download all contracts
        all_data = []
        contracts_to_download = []
        
        for _, row in near_money_zero_dte.iterrows():
            contracts_to_download.append({
                'symbol': row['symbol'],
                'expiration': row['expiration'].strftime('%Y%m%d'),
                'strike': row['strike'],
                'right': row['right']
            })
        
        # Download with progress bar
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_contract_data, c, date): c 
                for c in contracts_to_download
            }
            
            for future in tqdm(as_completed(futures), 
                             total=len(futures), 
                             desc=f"Downloading {date}"):
                try:
                    contract = futures[future]
                    quotes_df, greeks_df = future.result()
                    
                    if not quotes_df.empty and not greeks_df.empty:
                        # Merge quotes and Greeks
                        merged = pd.merge(
                            quotes_df,
                            greeks_df[['timestamp', 'delta', 'theta', 'vega', 'rho', 
                                     'implied_vol', 'underlying_price']],
                            on='timestamp',
                            how='outer'
                        )
                        
                        # Add calculated fields
                        merged['mid_price'] = (merged['bid'] + merged['ask']) / 2
                        merged['spread'] = merged['ask'] - merged['bid']
                        merged['spread_pct'] = merged['spread'] / merged['mid_price']
                        merged['underlying_price_dollar'] = merged['underlying_price'] / 100
                        merged['trade_date'] = date
                        merged['dte'] = 0
                        
                        all_data.append(merged)
                        
                except Exception as e:
                    logger.error(f"Error processing contract: {e}")
        
        # Save combined data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Create directory
            os.makedirs(os.path.join(self.data_dir, date), exist_ok=True)
            
            # Save to parquet
            combined_df.to_parquet(date_file, compression='snappy', index=False)
            
            # Update metadata
            if date not in self.metadata["downloaded_dates"]:
                self.metadata["downloaded_dates"].append(date)
                self.metadata["total_days"] += 1
            self.metadata["total_records"] += len(combined_df)
            self._save_metadata()
            
            logger.info(f"✅ Saved {len(combined_df)} records for {date}")
            return len(combined_df)
        
        return 0
    
    def download_date_range(self, start_date: str, end_date: str):
        """
        Download 0DTE options for a date range
        
        Args:
            start_date: Start date YYYYMMDD
            end_date: End date YYYYMMDD
        """
        logger.info("="*60)
        logger.info("ZERO DTE SPY OPTIONS DOWNLOAD")
        logger.info("="*60)
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Data directory: {self.data_dir}")
        
        # Generate date range (weekdays only)
        current = pd.to_datetime(start_date, format='%Y%m%d')
        end = pd.to_datetime(end_date, format='%Y%m%d')
        
        dates_to_download = []
        while current <= end:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                dates_to_download.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)
        
        logger.info(f"Trading days to process: {len(dates_to_download)}")
        
        # Update metadata
        if not self.metadata["date_range"]["start"]:
            self.metadata["date_range"]["start"] = start_date
        self.metadata["date_range"]["end"] = end_date
        self._save_metadata()
        
        # Download each day
        total_records = 0
        successful_days = 0
        failed_days = []
        start_time = datetime.now()
        
        for i, date in enumerate(dates_to_download):
            logger.info(f"\nDay {i+1}/{len(dates_to_download)}")
            
            try:
                records = self.download_zero_dte_options_for_date(date)
                if records > 0:
                    total_records += records
                    successful_days += 1
                else:
                    failed_days.append(date)
                
                time.sleep(1)  # Brief pause
                
            except KeyboardInterrupt:
                logger.info("\nDownload interrupted by user")
                break
            except Exception as e:
                logger.error(f"Failed on {date}: {e}")
                failed_days.append(date)
                time.sleep(5)
        
        # Summary
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        logger.info("\n" + "="*60)
        logger.info("DOWNLOAD COMPLETE")
        logger.info("="*60)
        logger.info(f"Time elapsed: {elapsed:.1f} minutes")
        logger.info(f"Days processed: {successful_days}/{len(dates_to_download)}")
        logger.info(f"Total records: {total_records:,}")
        
        if failed_days:
            logger.warning(f"Failed days: {len(failed_days)}")
            logger.warning(f"First 10: {failed_days[:10]}")
    
    def load_zero_dte_data(self, date: str) -> pd.DataFrame:
        """
        Load 0DTE options data for a specific date
        
        Args:
            date: Date in YYYYMMDD format
            
        Returns:
            DataFrame with all 0DTE options for that date
        """
        date_file = os.path.join(self.data_dir, date, f"zero_dte_spy_{date}.parquet")
        
        if not os.path.exists(date_file):
            logger.warning(f"No data found for {date}")
            return pd.DataFrame()
        
        return pd.read_parquet(date_file)
    
    def load_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load 0DTE options data for a date range
        
        Args:
            start_date: Start date YYYYMMDD
            end_date: End date YYYYMMDD
            
        Returns:
            Combined DataFrame for all dates
        """
        all_data = []
        
        current = pd.to_datetime(start_date, format='%Y%m%d')
        end = pd.to_datetime(end_date, format='%Y%m%d')
        
        while current <= end:
            if current.weekday() < 5:
                date_str = current.strftime('%Y%m%d')
                df = self.load_zero_dte_data(date_str)
                if not df.empty:
                    all_data.append(df)
            current += timedelta(days=1)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    def get_zero_dte_strangles(self, date: str, delta_target: float = 0.30) -> pd.DataFrame:
        """
        Get 0DTE strangle candidates for a specific date
        
        Args:
            date: Date in YYYYMMDD format
            delta_target: Target delta for short strikes (e.g., 0.30)
            
        Returns:
            DataFrame with strangle combinations
        """
        df = self.load_zero_dte_data(date)
        if df.empty:
            return pd.DataFrame()
        
        # Get unique timestamps
        timestamps = df['timestamp'].unique()
        strangles = []
        
        for ts in timestamps:
            ts_data = df[df['timestamp'] == ts]
            
            # Find calls closest to target delta
            calls = ts_data[ts_data['right'] == 'CALL']
            puts = ts_data[ts_data['right'] == 'PUT']
            
            if not calls.empty and not puts.empty:
                # Find call with delta closest to target
                call_idx = (calls['delta'] - delta_target).abs().idxmin()
                call = calls.loc[call_idx]
                
                # Find put with delta closest to -target
                put_idx = (puts['delta'] + delta_target).abs().idxmin()
                put = puts.loc[put_idx]
                
                strangle = {
                    'timestamp': ts,
                    'underlying_price': call['underlying_price_dollar'],
                    'call_strike': call['strike'],
                    'call_bid': call['bid'],
                    'call_ask': call['ask'],
                    'call_mid': call['mid_price'],
                    'call_delta': call['delta'],
                    'call_iv': call['implied_vol'],
                    'put_strike': put['strike'],
                    'put_bid': put['bid'],
                    'put_ask': put['ask'],
                    'put_mid': put['mid_price'],
                    'put_delta': put['delta'],
                    'put_iv': put['implied_vol'],
                    'total_credit': call['bid'] + put['bid'],
                    'total_mid': call['mid_price'] + put['mid_price'],
                    'strike_width': call['strike'] - put['strike']
                }
                
                strangles.append(strangle)
        
        return pd.DataFrame(strangles)
    
    def get_atm_strangles(self, date: str, strike_offset: int = 5) -> pd.DataFrame:
        """
        Get ATM strangles for 0DTE options
        
        Args:
            date: Date in YYYYMMDD format
            strike_offset: Points away from ATM (e.g., 5 = $5 OTM)
            
        Returns:
            DataFrame with ATM strangle combinations
        """
        df = self.load_zero_dte_data(date)
        if df.empty:
            return pd.DataFrame()
        
        timestamps = df['timestamp'].unique()
        strangles = []
        
        for ts in timestamps:
            ts_data = df[df['timestamp'] == ts]
            underlying = ts_data.iloc[0]['underlying_price_dollar']
            
            # Find ATM strike
            strikes = ts_data['strike'].unique()
            atm_strike = min(strikes, key=lambda x: abs(x - underlying))
            
            # Get OTM strikes
            call_strike = atm_strike + strike_offset
            put_strike = atm_strike - strike_offset
            
            # Get specific contracts
            call = ts_data[(ts_data['strike'] == call_strike) & (ts_data['right'] == 'CALL')]
            put = ts_data[(ts_data['strike'] == put_strike) & (ts_data['right'] == 'PUT')]
            
            if not call.empty and not put.empty:
                call = call.iloc[0]
                put = put.iloc[0]
                
                strangle = {
                    'timestamp': ts,
                    'underlying_price': underlying,
                    'atm_strike': atm_strike,
                    'call_strike': call_strike,
                    'put_strike': put_strike,
                    'call_bid': call['bid'],
                    'call_ask': call['ask'],
                    'call_delta': call['delta'],
                    'put_bid': put['bid'],
                    'put_ask': put['ask'],
                    'put_delta': put['delta'],
                    'total_credit': call['bid'] + put['bid'],
                    'total_mid': call['mid_price'] + put['mid_price']
                }
                
                strangles.append(strangle)
        
        return pd.DataFrame(strangles)
    
    def database_summary(self):
        """Print database summary statistics"""
        print("\n" + "="*60)
        print("ZERO DTE SPY OPTIONS DATABASE SUMMARY")
        print("="*60)
        print(f"Location: {self.data_dir}")
        print(f"Created: {self.metadata['created']}")
        print(f"Last Updated: {self.metadata['last_updated']}")
        print(f"\nData Coverage:")
        print(f"  Date Range: {self.metadata['date_range']['start']} to {self.metadata['date_range']['end']}")
        print(f"  Total Days: {self.metadata['total_days']}")
        print(f"  Total Records: {self.metadata['total_records']:,}")
        
        if self.metadata['downloaded_dates']:
            print(f"\nFirst 5 dates: {self.metadata['downloaded_dates'][:5]}")
            print(f"Last 5 dates: {self.metadata['downloaded_dates'][-5:]}")
        
        # Calculate total size
        total_size = 0
        for date in self.metadata['downloaded_dates']:
            file_path = os.path.join(self.data_dir, date, f"zero_dte_spy_{date}.parquet")
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
        
        print(f"\nTotal Storage: {total_size / (1024**3):.2f} GB")
        print("="*60)


def main():
    """Example usage of the Zero DTE database"""
    # Initialize database
    db = ZeroDTESPYOptionsDatabase()
    
    # Show summary
    db.database_summary()
    
    # Example: Download a specific date
    # db.download_zero_dte_options_for_date('20250801')
    
    # Example: Download date range
    # db.download_date_range('20250505', '20250801')
    
    # Example: Load and analyze data
    # data = db.load_zero_dte_data('20250505')
    # strangles = db.get_zero_dte_strangles('20250505', delta_target=0.30)


if __name__ == "__main__":
    main()# Alias for clarity
MinuteLevelOptionsDatabase = ZeroDTESPYOptionsDatabase
