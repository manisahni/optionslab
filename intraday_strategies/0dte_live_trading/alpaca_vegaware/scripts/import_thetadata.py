#!/usr/bin/env python3
"""
Import ThetaData Historical Options Data
Imports existing ThetaData parquet files into unified SQLite database
Focuses on VegaAware trading window (2:30-4:00 PM ET)
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import logging
from tqdm import tqdm
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.thetadata import ThetaDataReader
from core.db import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ThetaDataImporter')

class ThetaDataImporter:
    """Import ThetaData files into unified database"""
    
    def __init__(self):
        """Initialize importer"""
        self.reader = ThetaDataReader()
        self.db = Database()
        self.ET = pytz.timezone('US/Eastern')
        
        # VegaAware trading window
        self.start_time = "14:30"  # 2:30 PM ET
        self.end_time = "16:00"    # 4:00 PM ET
        
        # Progress tracking
        self.progress_file = "import_progress.json"
        self.progress = self._load_progress()
    
    def _load_progress(self) -> dict:
        """Load import progress"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {"imported_dates": [], "failed_dates": []}
    
    def _save_progress(self):
        """Save import progress"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def import_date(self, date: str) -> bool:
        """
        Import data for a single date
        
        Args:
            date: Date in YYYYMMDD format
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Importing {date}...")
            
            # Load data from ThetaData
            df = self.reader.load_day_data(date)
            if df is None:
                logger.warning(f"No data available for {date}")
                return False
            
            # Convert date format
            date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            
            # Process SPY prices
            spy_prices = self._extract_spy_prices(df, date_formatted)
            if not spy_prices.empty:
                self.db.insert_spy_prices(spy_prices, source="thetadata")
                self.db.update_data_source(
                    date_formatted, "spy_prices", "thetadata",
                    len(spy_prices), 
                    spy_prices['timestamp'].min(),
                    spy_prices['timestamp'].max()
                )
            
            # Process options data
            options_data = self._extract_options_data(df, date_formatted)
            if not options_data.empty:
                self.db.insert_options_data(options_data, source="thetadata")
                self.db.update_data_source(
                    date_formatted, "options_data", "thetadata",
                    len(options_data),
                    options_data['timestamp'].min(),
                    options_data['timestamp'].max()
                )
            
            logger.info(f"Successfully imported {date}: {len(spy_prices)} SPY prices, {len(options_data)} options records")
            return True
            
        except Exception as e:
            logger.error(f"Error importing {date}: {e}")
            return False
    
    def _extract_spy_prices(self, df: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        Extract SPY prices from options data
        
        Args:
            df: ThetaData DataFrame
            date: Date string (YYYY-MM-DD)
            
        Returns:
            DataFrame with SPY prices
        """
        spy_data = []
        
        # Get unique timestamps in the trading window
        timestamps = df['timestamp'].unique()
        
        for ts in timestamps:
            # Get data for this timestamp
            ts_data = df[df['timestamp'] == ts]
            
            if len(ts_data) > 0:
                # Extract underlying price (divide by 100 as it's in cents)
                spy_price = ts_data.iloc[0].get('underlying_price_dollar', 
                                               ts_data.iloc[0].get('underlying_price', 0) / 100)
                if spy_price and spy_price > 0:
                    ts_dt = pd.to_datetime(ts)
                    
                    # Check if in trading window
                    ts_time = ts_dt.time()
                    start_time = time(14, 30)
                    end_time = time(16, 0)
                    
                    if start_time <= ts_time <= end_time:
                        spy_data.append({
                            'timestamp': ts_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'close': float(spy_price),
                            'bid': float(spy_price - 0.01),
                            'ask': float(spy_price + 0.01)
                        })
        
        return pd.DataFrame(spy_data)
    
    def _extract_options_data(self, df: pd.DataFrame, date: str) -> pd.DataFrame:
        """
        Extract options data
        
        Args:
            df: ThetaData DataFrame
            date: Date string (YYYY-MM-DD)
            
        Returns:
            DataFrame with options data
        """
        options_data = []
        
        # Filter for trading window
        for idx, row in df.iterrows():
            # Get timestamp from the row
            ts_dt = pd.to_datetime(row['timestamp'])
            
            # Check if in trading window
            ts_time = ts_dt.time()
            start_time = time(14, 30)
            end_time = time(16, 0)
            
            if start_time <= ts_time <= end_time:
                # Build option symbol (SPY format: SPYYMMDDCXXXXXXX)
                expiry = date.replace('-', '')
                strike_str = f"{int(row['strike'] * 1000):08d}"
                option_type = row['right'].upper()  # 'CALL' or 'PUT'
                option_type_char = 'C' if option_type == 'CALL' else 'P'
                symbol = f"SPY{expiry[2:]}{option_type_char}{strike_str}"
                
                # Get underlying price (divide by 100 as it's in cents)
                underlying = row.get('underlying_price_dollar', row.get('underlying_price', 0) / 100)
                
                options_data.append({
                    'timestamp': ts_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'strike': float(row['strike']),
                    'option_type': option_type,
                    'expiration': date,
                    'bid': float(row.get('bid', 0)),
                    'ask': float(row.get('ask', 0)),
                    'last': float(row.get('mid_price', 0)),
                    'mid': float(row.get('mid_price', (row.get('bid', 0) + row.get('ask', 0)) / 2)),
                    'delta': float(row.get('delta', 0)),
                    'gamma': float(row.get('gamma', 0)),
                    'theta': float(row.get('theta', 0)),
                    'vega': float(row.get('vega', 0)),
                    'rho': float(row.get('rho', 0)),
                    'implied_volatility': float(row.get('implied_vol', 0)),
                    'volume': 0,  # Not in this dataset
                    'open_interest': 0,  # Not in this dataset
                    'underlying_price': float(underlying)
                })
        
        return pd.DataFrame(options_data)
    
    def import_date_range(self, start_date: str = None, end_date: str = None,
                         skip_existing: bool = True):
        """
        Import a range of dates
        
        Args:
            start_date: Start date (YYYYMMDD), default is 3 months ago
            end_date: End date (YYYYMMDD), default is yesterday
            skip_existing: Skip dates already imported
        """
        available_dates = self.reader.get_available_dates()
        
        # Filter date range
        if start_date:
            available_dates = [d for d in available_dates if d >= start_date]
        if end_date:
            available_dates = [d for d in available_dates if d <= end_date]
        
        # Skip already imported dates
        if skip_existing:
            available_dates = [d for d in available_dates 
                             if d not in self.progress['imported_dates']]
        
        logger.info(f"Importing {len(available_dates)} dates...")
        
        # Import with progress bar
        for date in tqdm(available_dates, desc="Importing dates"):
            success = self.import_date(date)
            
            if success:
                self.progress['imported_dates'].append(date)
            else:
                self.progress['failed_dates'].append(date)
            
            # Save progress after each date
            self._save_progress()
        
        # Summary
        logger.info(f"\nImport complete!")
        logger.info(f"Successfully imported: {len(self.progress['imported_dates'])} dates")
        logger.info(f"Failed: {len(self.progress['failed_dates'])} dates")
        
        if self.progress['failed_dates']:
            logger.warning(f"Failed dates: {self.progress['failed_dates']}")
    
    def verify_import(self):
        """Verify imported data"""
        coverage = self.db.get_data_coverage()
        
        print("\n" + "="*60)
        print("DATABASE COVERAGE SUMMARY")
        print("="*60)
        
        if not coverage.empty:
            # Group by source
            by_source = coverage.groupby('source')['record_count'].sum()
            print("\nRecords by source:")
            for source, count in by_source.items():
                print(f"  {source}: {count:,} records")
            
            # Date range
            print(f"\nDate range: {coverage['date'].min()} to {coverage['date'].max()}")
            print(f"Total days: {coverage['date'].nunique()}")
            
            # Sample data
            print("\nRecent imports:")
            print(coverage.head(10))
        else:
            print("No data imported yet")


def main():
    """Main import function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import ThetaData to unified database')
    parser.add_argument('--start', help='Start date (YYYYMMDD)')
    parser.add_argument('--end', help='End date (YYYYMMDD)')
    parser.add_argument('--verify', action='store_true', help='Verify import only')
    parser.add_argument('--force', action='store_true', help='Re-import existing dates')
    
    args = parser.parse_args()
    
    importer = ThetaDataImporter()
    
    if args.verify:
        importer.verify_import()
    else:
        # Default to last 3 months if no dates specified
        if not args.start:
            # Get dates from 3 months ago
            three_months_ago = pd.Timestamp.now() - pd.Timedelta(days=90)
            args.start = three_months_ago.strftime('%Y%m%d')
        
        importer.import_date_range(
            start_date=args.start,
            end_date=args.end,
            skip_existing=not args.force
        )
        
        # Show verification
        importer.verify_import()


if __name__ == "__main__":
    main()