#!/usr/bin/env python3
"""
ThetaData Integration Module
Reads and processes historical 0DTE options data from ThetaData parquet files
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ThetaDataReader:
    """Read and process ThetaData 0DTE options data"""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize ThetaData reader
        
        Args:
            data_dir: Directory containing ThetaData parquet files
        """
        if data_dir is None:
            # Default to the existing ThetaData directory
            data_dir = "/Users/nish_macbook/theta-options-suite/intraday_strategies/0dte_backtesting/data_thetadata/spy_0dte"
        
        self.data_dir = data_dir
        self.ET = pytz.timezone('US/Eastern')
        
        # Cache for loaded data
        self._cache = {}
        self._cache_size_limit = 10  # Keep max 10 days in memory
        
        # Verify data directory exists
        if not os.path.exists(self.data_dir):
            raise ValueError(f"ThetaData directory not found: {self.data_dir}")
        
        # Load metadata
        self.metadata = self._load_metadata()
        logger.info(f"ThetaData reader initialized with {len(self.metadata.get('downloaded_dates', []))} days of data")
    
    def _load_metadata(self) -> dict:
        """Load database metadata"""
        metadata_file = os.path.join(self.data_dir, "metadata", "zero_dte_database_info.json")
        if os.path.exists(metadata_file):
            import json
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return {"downloaded_dates": []}
    
    def get_available_dates(self) -> List[str]:
        """Get list of available dates in the database"""
        return sorted(self.metadata.get('downloaded_dates', []))
    
    def load_day_data(self, date: str) -> Optional[pd.DataFrame]:
        """
        Load data for a specific date
        
        Args:
            date: Date string in YYYYMMDD format
            
        Returns:
            DataFrame with options data or None if not available
        """
        # Check cache first
        if date in self._cache:
            return self._cache[date]
        
        # Build file path
        file_path = os.path.join(self.data_dir, date, f"zero_dte_spy_{date}.parquet")
        
        if not os.path.exists(file_path):
            logger.warning(f"No data file found for {date}")
            return None
        
        try:
            # Load parquet file
            df = pd.read_parquet(file_path)
            
            # Manage cache size
            if len(self._cache) >= self._cache_size_limit:
                # Remove oldest cached item
                oldest = min(self._cache.keys())
                del self._cache[oldest]
            
            # Cache the data
            self._cache[date] = df
            
            logger.info(f"Loaded {len(df)} records for {date}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data for {date}: {e}")
            return None
    
    def get_spy_prices(self, date: str, start_time: str = "14:30", end_time: str = "16:00") -> Optional[pd.DataFrame]:
        """
        Get SPY prices for a specific date and time range
        
        Args:
            date: Date in YYYYMMDD format
            start_time: Start time in HH:MM format (ET)
            end_time: End time in HH:MM format (ET)
            
        Returns:
            DataFrame with SPY prices
        """
        df = self.load_day_data(date)
        if df is None:
            return None
        
        # Extract SPY price from the data
        # ThetaData includes underlying price with each option record
        spy_data = []
        
        # Get unique timestamps
        timestamps = df.index.unique() if hasattr(df.index, 'unique') else df['timestamp'].unique()
        
        for ts in timestamps:
            ts_data = df[df.index == ts] if ts in df.index else df[df['timestamp'] == ts]
            if len(ts_data) > 0:
                # Get the underlying price (should be same for all options at this timestamp)
                spy_price = ts_data.iloc[0].get('underlying_price', None)
                if spy_price:
                    spy_data.append({
                        'timestamp': ts,
                        'price': spy_price,
                        'bid': spy_price - 0.01,  # Approximate bid
                        'ask': spy_price + 0.01   # Approximate ask
                    })
        
        if not spy_data:
            return None
        
        spy_df = pd.DataFrame(spy_data)
        spy_df['timestamp'] = pd.to_datetime(spy_df['timestamp'])
        
        # Filter by time range
        start_dt = pd.to_datetime(f"{date} {start_time}").tz_localize(self.ET)
        end_dt = pd.to_datetime(f"{date} {end_time}").tz_localize(self.ET)
        
        mask = (spy_df['timestamp'] >= start_dt) & (spy_df['timestamp'] <= end_dt)
        return spy_df[mask]
    
    def get_option_chain(self, date: str, timestamp: str = "15:00") -> Optional[pd.DataFrame]:
        """
        Get option chain at a specific timestamp
        
        Args:
            date: Date in YYYYMMDD format
            timestamp: Time in HH:MM format (ET)
            
        Returns:
            DataFrame with option chain
        """
        df = self.load_day_data(date)
        if df is None:
            return None
        
        # Convert timestamp to datetime
        target_time = pd.to_datetime(f"{date} {timestamp}").tz_localize(self.ET)
        
        # Find closest timestamp in data
        timestamps = pd.to_datetime(df.index if hasattr(df, 'index') else df['timestamp'])
        if timestamps.tz is None:
            timestamps = timestamps.tz_localize(self.ET)
        
        time_diffs = abs(timestamps - target_time)
        closest_idx = time_diffs.argmin()
        
        # Get data at closest timestamp
        if hasattr(df, 'iloc'):
            chain_data = df.iloc[closest_idx:closest_idx+100]  # Get multiple strikes
        else:
            closest_time = timestamps.iloc[closest_idx]
            chain_data = df[df['timestamp'] == closest_time]
        
        return chain_data
    
    def get_strangle_prices(self, date: str, call_strike: float, put_strike: float,
                           start_time: str = "14:30", end_time: str = "16:00") -> Optional[pd.DataFrame]:
        """
        Get prices for a specific strangle over a time range
        
        Args:
            date: Date in YYYYMMDD format
            call_strike: Call strike price
            put_strike: Put strike price
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            
        Returns:
            DataFrame with strangle prices and Greeks
        """
        df = self.load_day_data(date)
        if df is None:
            return None
        
        # Filter for the specific strikes
        call_data = df[(df['strike'] == call_strike) & (df['option_type'] == 'CALL')]
        put_data = df[(df['strike'] == put_strike) & (df['option_type'] == 'PUT')]
        
        if call_data.empty or put_data.empty:
            logger.warning(f"No data found for strangle {call_strike}C/{put_strike}P on {date}")
            return None
        
        # Combine call and put data
        strangle_data = []
        
        timestamps = call_data.index.unique() if hasattr(call_data.index, 'unique') else call_data['timestamp'].unique()
        
        for ts in timestamps:
            call_row = call_data[call_data.index == ts].iloc[0] if ts in call_data.index else call_data[call_data['timestamp'] == ts].iloc[0]
            put_row = put_data[put_data.index == ts].iloc[0] if ts in put_data.index else put_data[put_data['timestamp'] == ts].iloc[0]
            
            strangle_data.append({
                'timestamp': ts,
                'spy_price': call_row.get('underlying_price', 0),
                'call_bid': call_row.get('bid', 0),
                'call_ask': call_row.get('ask', 0),
                'call_mid': (call_row.get('bid', 0) + call_row.get('ask', 0)) / 2,
                'call_delta': call_row.get('delta', 0),
                'call_gamma': call_row.get('gamma', 0),
                'call_theta': call_row.get('theta', 0),
                'call_vega': call_row.get('vega', 0),
                'call_iv': call_row.get('implied_volatility', 0),
                'put_bid': put_row.get('bid', 0),
                'put_ask': put_row.get('ask', 0),
                'put_mid': (put_row.get('bid', 0) + put_row.get('ask', 0)) / 2,
                'put_delta': put_row.get('delta', 0),
                'put_gamma': put_row.get('gamma', 0),
                'put_theta': put_row.get('theta', 0),
                'put_vega': put_row.get('vega', 0),
                'put_iv': put_row.get('implied_volatility', 0),
                'total_premium': (call_row.get('bid', 0) + put_row.get('bid', 0)),
                'total_vega': abs(call_row.get('vega', 0)) + abs(put_row.get('vega', 0)),
                'net_delta': call_row.get('delta', 0) + put_row.get('delta', 0)
            })
        
        strangle_df = pd.DataFrame(strangle_data)
        strangle_df['timestamp'] = pd.to_datetime(strangle_df['timestamp'])
        
        # Filter by time range
        start_dt = pd.to_datetime(f"{date} {start_time}").tz_localize(self.ET)
        end_dt = pd.to_datetime(f"{date} {end_time}").tz_localize(self.ET)
        
        mask = (strangle_df['timestamp'] >= start_dt) & (strangle_df['timestamp'] <= end_dt)
        
        return strangle_df[mask]
    
    def find_delta_strikes(self, date: str, target_delta: float = 0.15, 
                          timestamp: str = "15:00") -> Optional[Tuple[float, float]]:
        """
        Find strikes closest to target delta
        
        Args:
            date: Date in YYYYMMDD format
            target_delta: Target delta (e.g., 0.15)
            timestamp: Time to check
            
        Returns:
            Tuple of (call_strike, put_strike) or None
        """
        chain = self.get_option_chain(date, timestamp)
        if chain is None:
            return None
        
        # Separate calls and puts
        calls = chain[chain['option_type'] == 'CALL']
        puts = chain[chain['option_type'] == 'PUT']
        
        if calls.empty or puts.empty:
            return None
        
        # Find closest delta for calls
        call_deltas = abs(calls['delta'] - target_delta)
        best_call_idx = call_deltas.argmin() if hasattr(call_deltas, 'argmin') else call_deltas.idxmin()
        best_call_strike = calls.iloc[best_call_idx]['strike'] if hasattr(calls, 'iloc') else calls.loc[best_call_idx]['strike']
        
        # Find closest delta for puts (remember put deltas are negative)
        put_deltas = abs(abs(puts['delta']) - target_delta)
        best_put_idx = put_deltas.argmin() if hasattr(put_deltas, 'argmin') else put_deltas.idxmin()
        best_put_strike = puts.iloc[best_put_idx]['strike'] if hasattr(puts, 'iloc') else puts.loc[best_put_idx]['strike']
        
        return (best_call_strike, best_put_strike)
    
    def get_date_summary(self, date: str) -> Dict:
        """
        Get summary statistics for a date
        
        Args:
            date: Date in YYYYMMDD format
            
        Returns:
            Dictionary with summary stats
        """
        df = self.load_day_data(date)
        if df is None:
            return {}
        
        return {
            'date': date,
            'total_records': len(df),
            'unique_strikes': df['strike'].nunique() if 'strike' in df.columns else 0,
            'time_range': {
                'start': df.index.min() if hasattr(df, 'index') else df['timestamp'].min(),
                'end': df.index.max() if hasattr(df, 'index') else df['timestamp'].max()
            },
            'spy_range': {
                'low': df['underlying_price'].min() if 'underlying_price' in df.columns else 0,
                'high': df['underlying_price'].max() if 'underlying_price' in df.columns else 0
            }
        }


if __name__ == "__main__":
    # Test the reader
    reader = ThetaDataReader()
    
    print("Available dates:", len(reader.get_available_dates()))
    print("First 5 dates:", reader.get_available_dates()[:5])
    print("Last 5 dates:", reader.get_available_dates()[-5:])
    
    # Test loading a recent date
    test_date = "20250801"
    if test_date in reader.get_available_dates():
        print(f"\nTesting with {test_date}:")
        summary = reader.get_date_summary(test_date)
        print(f"Summary: {summary}")