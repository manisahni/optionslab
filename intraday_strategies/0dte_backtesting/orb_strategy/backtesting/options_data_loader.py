"""
Options Data Loader for Real 0DTE Backtesting
Loads and processes actual 0DTE options data from parquet files
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptionsDataLoader:
    """
    Load and manage 0DTE options data for backtesting
    """
    
    def __init__(self, data_dir: str = '/Users/nish_macbook/0dte/data/options/spy_0dte_minute'):
        """
        Initialize options data loader
        
        Args:
            data_dir: Directory containing options data organized by date
        """
        self.data_dir = Path(data_dir)
        self.cache = {}  # Cache loaded data
        
        if not self.data_dir.exists():
            raise ValueError(f"Data directory not found: {data_dir}")
        
        logger.info(f"Options data loader initialized with {data_dir}")
    
    def get_available_dates(self) -> List[str]:
        """Get list of dates with available options data"""
        dates = []
        
        for folder in sorted(self.data_dir.iterdir()):
            if folder.is_dir() and folder.name.isdigit():
                # Convert YYYYMMDD to YYYY-MM-DD
                date_str = folder.name
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                dates.append(formatted_date)
        
        return dates
    
    def load_day_data(self, date: str, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        Load options data for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with options data or None if not found
        """
        # Check cache first
        if use_cache and date in self.cache:
            return self.cache[date]
        
        # Convert date format for folder name
        date_obj = pd.to_datetime(date)
        folder_name = date_obj.strftime('%Y%m%d')
        
        # Build file path
        file_path = self.data_dir / folder_name / f'zero_dte_spy_{folder_name}.parquet'
        
        if not file_path.exists():
            logger.warning(f"No options data found for {date}")
            return None
        
        try:
            # Load parquet file
            df = pd.read_parquet(file_path)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Add helper columns
            df['time'] = df['timestamp'].dt.time
            df['hour'] = df['timestamp'].dt.hour
            df['minute'] = df['timestamp'].dt.minute
            
            # Cache the data
            if use_cache:
                self.cache[date] = df
            
            logger.info(f"Loaded {len(df)} option quotes for {date}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data for {date}: {e}")
            return None
    
    def get_option_quote(self, df: pd.DataFrame, timestamp: pd.Timestamp, 
                        strike: float, right: str) -> Optional[pd.Series]:
        """
        Get specific option quote at given time
        
        Args:
            df: Options data DataFrame
            timestamp: Time to get quote
            strike: Strike price
            right: 'CALL' or 'PUT'
            
        Returns:
            Series with option data or None
        """
        # Filter to specific option
        mask = (
            (df['timestamp'] == timestamp) &
            (df['strike'] == strike) &
            (df['right'] == right)
        )
        
        filtered = df[mask]
        
        if filtered.empty:
            return None
        
        return filtered.iloc[0]
    
    def find_nearest_strikes(self, df: pd.DataFrame, target_price: float, 
                           right: str, num_strikes: int = 5) -> List[float]:
        """
        Find nearest available strikes to target price
        
        Args:
            df: Options data
            target_price: Target strike price
            right: 'CALL' or 'PUT'
            num_strikes: Number of strikes to return
            
        Returns:
            List of nearest strikes
        """
        # Get unique strikes for this option type
        strikes = df[df['right'] == right]['strike'].unique()
        strikes = sorted(strikes)
        
        if not strikes:
            return []
        
        # Find nearest strikes
        distances = [abs(s - target_price) for s in strikes]
        sorted_indices = np.argsort(distances)
        
        nearest = [strikes[i] for i in sorted_indices[:num_strikes]]
        
        return sorted(nearest)
    
    def get_spread_quote(self, df: pd.DataFrame, timestamp: pd.Timestamp,
                        short_strike: float, long_strike: float, 
                        right: str) -> Dict:
        """
        Get credit spread quote at specific time
        
        Args:
            df: Options data
            timestamp: Time for quote
            short_strike: Short option strike
            long_strike: Long option strike  
            right: 'CALL' or 'PUT'
            
        Returns:
            Dict with spread details
        """
        # Get individual option quotes
        short_option = self.get_option_quote(df, timestamp, short_strike, right)
        long_option = self.get_option_quote(df, timestamp, long_strike, right)
        
        if short_option is None or long_option is None:
            return None
        
        # Calculate credit spread metrics
        # For credit spread: we receive bid on short, pay ask on long
        credit_per_contract = (short_option['bid'] - long_option['ask']) * 100
        
        # Calculate max loss (spread width minus credit)
        spread_width = abs(short_strike - long_strike)
        max_loss = (spread_width * 100) - credit_per_contract
        
        # Greeks for the spread
        net_delta = short_option['delta'] - long_option['delta']
        net_gamma = short_option['gamma'] - long_option['gamma']
        net_theta = short_option['theta'] - long_option['theta']
        net_vega = short_option['vega'] - long_option['vega']
        
        return {
            'timestamp': timestamp,
            'short_strike': short_strike,
            'long_strike': long_strike,
            'right': right,
            'spread_width': spread_width,
            'short_bid': short_option['bid'],
            'short_ask': short_option['ask'],
            'long_bid': long_option['bid'],
            'long_ask': long_option['ask'],
            'credit': credit_per_contract,
            'max_loss': max_loss,
            'net_delta': net_delta,
            'net_gamma': net_gamma,
            'net_theta': net_theta,
            'net_vega': net_vega,
            'underlying_price': short_option['underlying_price_dollar']
        }
    
    def scan_for_best_spread(self, df: pd.DataFrame, timestamp: pd.Timestamp,
                            target_short: float, spread_width: float,
                            right: str) -> Dict:
        """
        Find best available spread near target strikes
        
        Args:
            df: Options data
            timestamp: Time for quote
            target_short: Target short strike
            spread_width: Desired spread width
            right: 'CALL' or 'PUT'
            
        Returns:
            Best available spread
        """
        # Find nearest available strikes
        available_shorts = self.find_nearest_strikes(df, target_short, right, num_strikes=3)
        
        best_spread = None
        best_credit = 0
        
        for short_strike in available_shorts:
            # Calculate long strike
            if right == 'PUT':
                long_strike = short_strike - spread_width
            else:
                long_strike = short_strike + spread_width
            
            # Find nearest available long strike
            available_longs = self.find_nearest_strikes(df, long_strike, right, num_strikes=1)
            
            if not available_longs:
                continue
            
            actual_long = available_longs[0]
            
            # Get spread quote
            spread = self.get_spread_quote(df, timestamp, short_strike, actual_long, right)
            
            if spread and spread['credit'] > best_credit:
                best_spread = spread
                best_credit = spread['credit']
        
        return best_spread


def main():
    """Test the options data loader"""
    
    loader = OptionsDataLoader()
    
    # Get available dates
    dates = loader.get_available_dates()
    print(f"Found {len(dates)} days of options data")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    
    # Load sample day
    if dates:
        test_date = dates[0]
        print(f"\nLoading data for {test_date}...")
        
        df = loader.load_day_data(test_date)
        
        if df is not None:
            print(f"Loaded {len(df)} option quotes")
            
            # Test getting a spread quote at 10:30 AM
            test_time = pd.Timestamp(f'{test_date} 10:30:00')
            
            # Get underlying price
            sample = df[df['timestamp'] == test_time].iloc[0]
            spy_price = sample['underlying_price_dollar']
            
            print(f"\nAt 10:30 AM, SPY = ${spy_price:.2f}")
            
            # Test put spread
            short_put = spy_price - 2  # 2 points OTM
            long_put = short_put - 15  # $15 wide
            
            spread = loader.get_spread_quote(
                df, test_time, 
                short_put, long_put, 'PUT'
            )
            
            if spread:
                print(f"\nPut Spread ${short_put}/{long_put}:")
                print(f"  Credit: ${spread['credit']:.2f}")
                print(f"  Max Loss: ${spread['max_loss']:.2f}")
                print(f"  Net Delta: {spread['net_delta']:.3f}")
                print(f"  Net Vega: {spread['net_vega']:.3f}")


if __name__ == "__main__":
    main()