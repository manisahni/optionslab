"""
Data loader for SPY options parquet files
"""
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import glob
from config import DATA_DIR, OPTION_COLUMNS


class SPYDataLoader:
    """Load and process SPY options data from parquet files"""
    
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self._file_cache = {}
        self._data_cache = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def get_available_dates(self) -> List[str]:
        """Get list of available trading dates"""
        pattern = str(self.data_dir / "spy_options_eod_*.parquet")
        files = glob.glob(pattern)
        dates = []
        for file in files:
            # Extract date from filename: spy_options_eod_YYYYMMDD.parquet
            date_str = Path(file).stem.split('_')[-1]
            dates.append(date_str)
        return sorted(dates)
    
    def load_date(self, date: str) -> pd.DataFrame:
        """Load options data for a specific date"""
        if date in self._data_cache:
            return self._data_cache[date].copy()
            
        file_path = self.data_dir / f"spy_options_eod_{date}.parquet"
        if not file_path.exists():
            raise FileNotFoundError(f"No data file found for date {date}")
            
        try:
            # Try PyArrow first (default engine)
            df = pd.read_parquet(file_path, engine='pyarrow')
            df = self._process_dataframe(df, date)
            self._data_cache[date] = df
            return df.copy()
        except Exception as pyarrow_error:
            # Fallback to fastparquet if PyArrow fails
            try:
                self.logger.warning(f"PyArrow failed for {date}, trying fastparquet: {pyarrow_error}")
                df = pd.read_parquet(file_path, engine='fastparquet')
                df = self._process_dataframe(df, date)
                self._data_cache[date] = df
                return df.copy()
            except Exception as fastparquet_error:
                raise RuntimeError(f"Error loading data for {date}. PyArrow: {pyarrow_error}. Fastparquet: {fastparquet_error}")
    
    def load_date_range(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Load options data for a date range"""
        available_dates = self.get_available_dates()
        
        # Filter dates within range
        date_range = [d for d in available_dates if start_date <= d <= end_date]
        
        if not date_range:
            raise ValueError(f"No data available between {start_date} and {end_date}")
        
        data = {}
        for date in date_range:
            try:
                data[date] = self.load_date(date)
            except (FileNotFoundError, RuntimeError) as e:
                print(f"Warning: Skipping {date} - {e}")
                continue
                
        return data
    
    def _process_dataframe(self, df: pd.DataFrame, date: str) -> pd.DataFrame:
        """Process and clean the raw dataframe"""
        # Convert date strings to datetime
        df['date'] = pd.to_datetime(date)
        df['expiration'] = pd.to_datetime(df['expiration'])
        
        # Calculate days to expiration
        df['dte'] = (df['expiration'] - df['date']).dt.days
        
        # Convert strike prices from thousandths to dollars
        df['strike'] = df['strike'] / 1000
        
        # Calculate mid price
        df['mid_price'] = (df['bid'] + df['ask']) / 2
        
        # Filter out options with zero bid/ask
        df = df[(df['bid'] > 0) & (df['ask'] > 0)].copy()
        
        # Calculate moneyness
        df['moneyness'] = df['underlying_price'] / df['strike']
        
        # Add ITM/OTM flags
        df['itm'] = ((df['right'] == 'C') & (df['underlying_price'] > df['strike'])) | \
                   ((df['right'] == 'P') & (df['underlying_price'] < df['strike']))
        
        # Filter out extreme strikes (more than 50% away from underlying)
        min_strike = df['underlying_price'].iloc[0] * 0.5
        max_strike = df['underlying_price'].iloc[0] * 1.5
        df = df[(df['strike'] >= min_strike) & (df['strike'] <= max_strike)].copy()
        
        # Sort by expiration, strike, and right
        df = df.sort_values(['expiration', 'strike', 'right']).reset_index(drop=True)
        
        return df
    
    def get_option_chain(self, date: str, min_dte: int = 0, max_dte: int = 365,
                        option_type: Optional[str] = None) -> pd.DataFrame:
        """Get filtered option chain for a specific date"""
        df = self.load_date(date)
        
        # Filter by DTE
        df = df[(df['dte'] >= min_dte) & (df['dte'] <= max_dte)].copy()
        
        # Filter by option type if specified
        if option_type:
            df = df[df['right'] == option_type.upper()].copy()
        
        return df
    
    def find_option_by_delta(self, date: str, target_delta: float, 
                           option_type: str, min_dte: int = 10, 
                           max_dte: int = 60, add_diagnostics: bool = True) -> Optional[pd.Series]:
        """Find option closest to target delta with detailed diagnostics"""
        df = self.get_option_chain(date, min_dte, max_dte, option_type)
        
        if df.empty:
            if add_diagnostics:
                self.logger.warning(f"No options found for {date}, {option_type}, DTE {min_dte}-{max_dte}")
            return None
        
        # Filter by delta sign (calls positive, puts negative)
        original_target = target_delta
        if option_type.upper() == 'C':
            df = df[df['delta'] > 0].copy()
        else:
            df = df[df['delta'] < 0].copy()
            target_delta = -abs(target_delta)  # Make target negative for puts
        
        if df.empty:
            if add_diagnostics:
                self.logger.warning(f"No {option_type} options with correct delta sign found for {date}")
            return None
        
        # Find closest delta
        df['delta_diff'] = abs(df['delta'] - target_delta)
        
        if add_diagnostics:
            # Add comprehensive delta targeting diagnostics
            sorted_options = df.sort_values('delta_diff')
            top_candidates = sorted_options.head(3)
            
            self.logger.info(f"DataLoader delta search for {date}, {option_type} targeting {original_target:.3f}:")
            self.logger.info(f"  Total {option_type} options found: {len(df)}")
            self.logger.info(f"  Delta range available: {df['delta'].min():.3f} to {df['delta'].max():.3f}")
            self.logger.info(f"  DTE range: {df['dte'].min():.0f} to {df['dte'].max():.0f}")
            
            for i, (_, candidate) in enumerate(top_candidates.iterrows()):
                self.logger.info(f"  Top {i+1}: Strike={candidate['strike']:.0f}, "
                               f"Delta={candidate['delta']:.3f}, "
                               f"DTE={candidate['dte']:.0f}, "
                               f"Diff={candidate['delta_diff']:.3f}, "
                               f"Bid/Ask={candidate['bid']:.2f}/{candidate['ask']:.2f}")
            
            best_option = sorted_options.iloc[0]
            delta_tolerance = 0.05
            
            if best_option['delta_diff'] > delta_tolerance:
                self.logger.warning(f"⚠️  DataLoader DELTA TARGET MISS: "
                                  f"Target={original_target:.3f}, "
                                  f"Selected={best_option['delta']:.3f}, "
                                  f"Difference={best_option['delta_diff']:.3f}")
            else:
                self.logger.info(f"✅ DataLoader delta target achieved: "
                               f"Target={original_target:.3f}, "
                               f"Selected={best_option['delta']:.3f}")
        
        closest_idx = df['delta_diff'].idxmin()
        return df.loc[closest_idx]
    
    def find_option_by_strike(self, date: str, strike: float, option_type: str,
                            min_dte: int = 10, max_dte: int = 60) -> Optional[pd.Series]:
        """Find option by specific strike and expiration criteria"""
        df = self.get_option_chain(date, min_dte, max_dte, option_type)
        
        if df.empty:
            return None
        
        # Find closest strike
        df['strike_diff'] = abs(df['strike'] - strike)
        closest_idx = df['strike_diff'].idxmin()
        
        return df.loc[closest_idx]
    
    def get_underlying_price(self, date: str) -> float:
        """Get SPY underlying price for a date"""
        df = self.load_date(date)
        return df['underlying_price'].iloc[0]
    
    def clear_cache(self):
        """Clear data cache to free memory"""
        self._data_cache.clear()
        self._file_cache.clear()


def test_data_loader():
    """Test the data loader functionality"""
    loader = SPYDataLoader()
    
    # Test available dates
    dates = loader.get_available_dates()
    print(f"Available dates: {len(dates)} from {dates[0]} to {dates[-1]}")
    
    # Test loading a single date
    test_date = dates[0]
    df = loader.load_date(test_date)
    print(f"\nData for {test_date}:")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Date range: {df['dte'].min()} to {df['dte'].max()} DTE")
    print(f"Strike range: ${df['strike'].min():.0f} to ${df['strike'].max():.0f}")
    print(f"Underlying price: ${df['underlying_price'].iloc[0]:.2f}")
    
    # Test finding options by delta
    call_option = loader.find_option_by_delta(test_date, 0.30, 'C', 10, 45)
    if call_option is not None:
        print(f"\n30-delta call:")
        print(f"Strike: ${call_option['strike']:.0f}, Delta: {call_option['delta']:.3f}")
        print(f"DTE: {call_option['dte']}, Mid: ${call_option['mid_price']:.2f}")


if __name__ == "__main__":
    test_data_loader()