"""
SPY Options Database Manager
Efficiently downloads, stores, and manages minute-level options data
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta, time
from typing import Dict, List, Optional, Tuple, Set
import logging
import json
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm
import pyarrow.parquet as pq
import pyarrow as pa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    """Configuration for options data download"""
    symbol: str = "SPY"
    base_url: str = "http://127.0.0.1:25510/v2"
    data_dir: str = "/Users/nish_macbook/0dte/market_data/spy_options_minute"
    strike_range_pct: float = 0.02  # 2% from spot
    min_open_interest: int = 100
    max_workers: int = 4
    interval_ms: int = 60000  # 1 minute
    
    # Focus on 0DTE and near-term expirations
    max_days_to_expiry: int = 5
    priority_dte: List[int] = None
    
    def __post_init__(self):
        if self.priority_dte is None:
            self.priority_dte = [0, 1, 2]  # 0DTE, 1DTE, 2DTE


class OptionsDatabase:
    """Manages SPY options minute data with efficient storage and retrieval"""
    
    def __init__(self, config: DownloadConfig = None):
        self.config = config or DownloadConfig()
        self._ensure_directories()
        self.metadata = self._load_metadata()
        
    def _ensure_directories(self):
        """Create necessary directory structure"""
        os.makedirs(self.config.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.config.data_dir, "summary"), exist_ok=True)
        
    def _load_metadata(self) -> Dict:
        """Load or create metadata file"""
        metadata_path = os.path.join(self.config.data_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        else:
            metadata = {
                "created": datetime.now().isoformat(),
                "last_update": None,
                "total_records": 0,
                "date_range": {"start": None, "end": None},
                "config": asdict(self.config)
            }
            self._save_metadata(metadata)
            return metadata
    
    def _save_metadata(self, metadata: Dict):
        """Save metadata file"""
        metadata_path = os.path.join(self.config.data_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_available_dates(self) -> List[str]:
        """Get available dates from ThetaData API"""
        try:
            response = requests.get(
                f"{self.config.base_url}/list/dates/option/quote",
                params={"root": self.config.symbol}
            )
            if response.status_code == 200:
                return sorted(response.json()['response'])
            else:
                logger.error(f"Failed to get dates: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting dates: {e}")
            return []
    
    def get_expirations_for_date(self, trade_date: str) -> List[str]:
        """Get relevant expirations for a trade date"""
        try:
            response = requests.get(
                f"{self.config.base_url}/list/expirations/option/quote",
                params={
                    "root": self.config.symbol,
                    "start_date": trade_date,
                    "end_date": trade_date
                }
            )
            
            if response.status_code == 200:
                all_expirations = response.json()['response']
                
                # Filter to near-term expirations
                trade_dt = datetime.strptime(trade_date, "%Y%m%d")
                relevant_exps = []
                
                for exp_str in all_expirations:
                    exp_dt = datetime.strptime(exp_str, "%Y%m%d")
                    days_to_expiry = (exp_dt - trade_dt).days
                    
                    if 0 <= days_to_expiry <= self.config.max_days_to_expiry:
                        relevant_exps.append({
                            'expiration': exp_str,
                            'dte': days_to_expiry,
                            'priority': days_to_expiry in self.config.priority_dte
                        })
                
                # Sort by priority (0DTE first) then by DTE
                relevant_exps.sort(key=lambda x: (not x['priority'], x['dte']))
                return [exp['expiration'] for exp in relevant_exps]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting expirations: {e}")
            return []
    
    def get_strikes_for_expiration(self, trade_date: str, expiration: str, spot_price: float) -> List[int]:
        """Get relevant strikes for an expiration"""
        try:
            # Calculate strike range
            min_strike = int(spot_price * (1 - self.config.strike_range_pct) * 1000)
            max_strike = int(spot_price * (1 + self.config.strike_range_pct) * 1000)
            
            response = requests.get(
                f"{self.config.base_url}/list/strikes/option/quote",
                params={
                    "root": self.config.symbol,
                    "exp": expiration
                }
            )
            
            if response.status_code == 200:
                all_strikes = response.json()['response']
                relevant_strikes = [s for s in all_strikes if min_strike <= s <= max_strike]
                return sorted(relevant_strikes)
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting strikes: {e}")
            return []
    
    def download_option_minute_data(self,
                                  trade_date: str,
                                  expiration: str,
                                  strike: int,
                                  right: str) -> Optional[pd.DataFrame]:
        """Download minute data for a specific option"""
        try:
            # Base parameters
            params = {
                "root": self.config.symbol,
                "exp": expiration,
                "strike": strike,
                "right": right,
                "start_date": trade_date,
                "end_date": trade_date,
                "ivl": self.config.interval_ms,
                "use_csv": "true",
                "rth": "true"  # Regular trading hours only
            }
            
            # Get quote data
            quote_response = requests.get(
                f"{self.config.base_url}/hist/option/quote",
                params=params
            )
            
            # Get Greeks data
            greeks_response = requests.get(
                f"{self.config.base_url}/hist/option/greeks",
                params=params
            )
            
            if quote_response.status_code == 200 and greeks_response.status_code == 200:
                # Parse CSV responses
                quote_df = pd.read_csv(pd.io.common.StringIO(quote_response.text))
                greeks_df = pd.read_csv(pd.io.common.StringIO(greeks_response.text))
                
                if quote_df.empty or greeks_df.empty:
                    return None
                
                # Merge on timestamp
                df = pd.merge(quote_df, greeks_df, on=['ms_of_day'], suffixes=('', '_greeks'))
                
                # Add metadata
                df['symbol'] = self.config.symbol
                df['trade_date'] = trade_date
                df['expiration'] = expiration
                df['strike'] = strike / 1000.0  # Convert to dollars
                df['right'] = right
                
                # Calculate additional fields
                df['mid'] = (df['bid'] + df['ask']) / 2
                df['spread'] = df['ask'] - df['bid']
                df['spread_pct'] = df['spread'] / df['mid'] * 100
                
                # Convert ms_of_day to time
                df['time'] = pd.to_timedelta(df['ms_of_day'], unit='ms')
                df['timestamp'] = pd.to_datetime(trade_date, format='%Y%m%d') + df['time']
                
                return df
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error downloading {strike}/{right}: {e}")
            return None
    
    def get_spot_price(self, trade_date: str) -> Optional[float]:
        """Get SPY spot price for a date"""
        try:
            params = {
                "root": self.config.symbol,
                "start_date": trade_date,
                "end_date": trade_date,
                "ivl": 900000,  # 15-minute bars
                "use_csv": "true",
                "rth": "true"
            }
            
            response = requests.get(
                f"{self.config.base_url}/hist/stock/quote",
                params=params
            )
            
            if response.status_code == 200:
                df = pd.read_csv(pd.io.common.StringIO(response.text))
                if not df.empty:
                    return df.iloc[0]['open'] / 1000.0  # Convert to dollars
            return None
            
        except Exception as e:
            logger.error(f"Error getting spot price: {e}")
            return None
    
    def download_day_complete(self, trade_date: str) -> pd.DataFrame:
        """Download complete options data for a trading day"""
        logger.info(f"Downloading options data for {trade_date}")
        
        # Get spot price
        spot_price = self.get_spot_price(trade_date)
        if not spot_price:
            logger.error(f"Could not get spot price for {trade_date}")
            return pd.DataFrame()
        
        # Get expirations
        expirations = self.get_expirations_for_date(trade_date)
        if not expirations:
            logger.error(f"No expirations found for {trade_date}")
            return pd.DataFrame()
        
        logger.info(f"Processing {len(expirations)} expirations, spot: ${spot_price:.2f}")
        
        all_data = []
        total_downloads = []
        
        # Build download tasks
        for expiration in expirations:
            strikes = self.get_strikes_for_expiration(trade_date, expiration, spot_price)
            
            for strike in strikes:
                for right in ['C', 'P']:
                    total_downloads.append({
                        'trade_date': trade_date,
                        'expiration': expiration,
                        'strike': strike,
                        'right': right,
                        'dte': (datetime.strptime(expiration, '%Y%m%d') - 
                               datetime.strptime(trade_date, '%Y%m%d')).days
                    })
        
        logger.info(f"Downloading {len(total_downloads)} option contracts")
        
        # Download in parallel with progress bar
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(
                    self.download_option_minute_data,
                    task['trade_date'],
                    task['expiration'],
                    task['strike'],
                    task['right']
                ): task for task in total_downloads
            }
            
            for future in tqdm(as_completed(futures), total=len(futures), desc=trade_date):
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        task = futures[future]
                        df['dte'] = task['dte']
                        df['spot_price'] = spot_price
                        all_data.append(df)
                except Exception as e:
                    logger.error(f"Download error: {e}")
        
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Downloaded {len(combined_df)} minute bars for {trade_date}")
            return combined_df
        else:
            return pd.DataFrame()
    
    def save_day_data(self, df: pd.DataFrame, trade_date: str):
        """Save day's data efficiently using Parquet"""
        if df.empty:
            return
        
        # Create date directory
        date_dir = os.path.join(self.config.data_dir, trade_date)
        os.makedirs(date_dir, exist_ok=True)
        
        # Save main data file
        file_path = os.path.join(date_dir, f"SPY_options_minute_{trade_date}.parquet")
        
        # Use pyarrow for better compression
        table = pa.Table.from_pandas(df)
        pq.write_table(table, file_path, compression='snappy')
        
        # Update metadata
        self.metadata['last_update'] = datetime.now().isoformat()
        self.metadata['total_records'] += len(df)
        
        if self.metadata['date_range']['start'] is None or trade_date < self.metadata['date_range']['start']:
            self.metadata['date_range']['start'] = trade_date
        if self.metadata['date_range']['end'] is None or trade_date > self.metadata['date_range']['end']:
            self.metadata['date_range']['end'] = trade_date
            
        self._save_metadata(self.metadata)
        
        # Create daily summary
        self._create_daily_summary(df, trade_date)
        
        logger.info(f"Saved {len(df)} records to {file_path}")
    
    def _create_daily_summary(self, df: pd.DataFrame, trade_date: str):
        """Create summary statistics for the day"""
        summary = {
            'trade_date': trade_date,
            'total_records': len(df),
            'unique_strikes': df['strike'].nunique(),
            'unique_expirations': df['expiration'].nunique(),
            'avg_spread': df['spread'].mean(),
            'avg_volume': df['volume'].mean(),
            'spot_open': df['spot_price'].iloc[0],
            'spot_close': df['spot_price'].iloc[-1] if len(df) > 1 else df['spot_price'].iloc[0],
            'most_liquid_strikes': df.groupby('strike')['volume'].sum().nlargest(10).to_dict(),
            'iv_summary': {
                'mean': df['implied_vol'].mean(),
                'std': df['implied_vol'].std(),
                'min': df['implied_vol'].min(),
                'max': df['implied_vol'].max()
            }
        }
        
        # Save summary
        summary_dir = os.path.join(self.config.data_dir, "summary")
        summary_path = os.path.join(summary_dir, f"summary_{trade_date}.json")
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def download_date_range(self, start_date: str, end_date: str, skip_existing: bool = True):
        """Download options data for a date range"""
        available_dates = self.get_available_dates()
        
        # Filter to our range
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        
        dates_to_download = []
        for date_str in available_dates:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            if start_dt <= date_obj <= end_dt:
                if skip_existing:
                    date_dir = os.path.join(self.config.data_dir, date_str)
                    if os.path.exists(date_dir):
                        logger.info(f"Skipping {date_str} - already exists")
                        continue
                dates_to_download.append(date_str)
        
        logger.info(f"Downloading {len(dates_to_download)} days of data")
        
        for trade_date in dates_to_download:
            try:
                df = self.download_day_complete(trade_date)
                if not df.empty:
                    self.save_day_data(df, trade_date)
                    
                # Brief pause between days
                import time
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing {trade_date}: {e}")
                continue
    
    def load_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Load options data for analysis"""
        all_data = []
        
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        
        # Find all date directories
        for date_dir in os.listdir(self.config.data_dir):
            if not date_dir.isdigit() or len(date_dir) != 8:
                continue
                
            date_obj = datetime.strptime(date_dir, "%Y%m%d")
            if start_dt <= date_obj <= end_dt:
                file_path = os.path.join(
                    self.config.data_dir, 
                    date_dir, 
                    f"SPY_options_minute_{date_dir}.parquet"
                )
                
                if os.path.exists(file_path):
                    df = pd.read_parquet(file_path)
                    all_data.append(df)
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            logger.info(f"Loaded {len(combined)} records from {len(all_data)} days")
            return combined
        else:
            return pd.DataFrame()
    
    def get_database_stats(self) -> Dict:
        """Get overall database statistics"""
        stats = {
            'total_days': 0,
            'total_records': 0,
            'date_range': {'start': None, 'end': None},
            'disk_usage_mb': 0,
            'summary': {}
        }
        
        # Calculate stats
        for date_dir in os.listdir(self.config.data_dir):
            if not date_dir.isdigit() or len(date_dir) != 8:
                continue
                
            stats['total_days'] += 1
            
            # Get file size
            file_path = os.path.join(
                self.config.data_dir,
                date_dir,
                f"SPY_options_minute_{date_dir}.parquet"
            )
            
            if os.path.exists(file_path):
                stats['disk_usage_mb'] += os.path.getsize(file_path) / (1024 * 1024)
                
                # Update date range
                if stats['date_range']['start'] is None or date_dir < stats['date_range']['start']:
                    stats['date_range']['start'] = date_dir
                if stats['date_range']['end'] is None or date_dir > stats['date_range']['end']:
                    stats['date_range']['end'] = date_dir
        
        stats.update(self.metadata)
        return stats


def main():
    """Example usage and database initialization"""
    # Initialize database
    db = OptionsDatabase()
    
    # Check connection
    dates = db.get_available_dates()
    if not dates:
        print("Could not connect to ThetaData API")
        return
    
    print(f"ThetaData API connected. {len(dates)} dates available.")
    
    # Example: Download last 5 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print(f"\nDownloading from {start_date.strftime('%Y%m%d')} to {end_date.strftime('%Y%m%d')}")
    
    db.download_date_range(
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d")
    )
    
    # Show database stats
    stats = db.get_database_stats()
    print("\nDatabase Statistics:")
    print(f"Total days: {stats['total_days']}")
    print(f"Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
    print(f"Disk usage: {stats['disk_usage_mb']:.1f} MB")


if __name__ == "__main__":
    main()