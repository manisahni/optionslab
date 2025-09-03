#!/usr/bin/env python3
"""
ThetaData Loader for OptionsLab
Connects the existing ThetaData 0DTE options to OptionsLab dashboard
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
import pyarrow.parquet as pq

class ThetaDataLoader:
    """Load ThetaData 0DTE options for backtesting"""
    
    def __init__(self):
        """Initialize ThetaData loader"""
        # Path to ThetaData
        self.data_dir = Path("/Users/nish_macbook/trading/daily-optionslab/data/spy_options")
        
        # Check if data exists
        if not self.data_dir.exists():
            raise ValueError(f"ThetaData directory not found: {self.data_dir}")
        
        # Get available dates
        self.available_dates = self._get_available_dates()
        print(f"ThetaData Loader initialized with {len(self.available_dates)} days of 0DTE data")
    
    def _get_available_dates(self):
        """Get list of available dates"""
        dates = []
        for date_dir in sorted(self.data_dir.iterdir()):
            if date_dir.is_dir() and date_dir.name.isdigit():
                dates.append(date_dir.name)
        return dates
    
    def load_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load data for a date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Combined DataFrame for the date range
        """
        # Convert to YYYYMMDD format
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        
        # Filter dates
        dates_to_load = [d for d in self.available_dates if start <= d <= end]
        
        if not dates_to_load:
            print(f"No data available for {start_date} to {end_date}")
            return pd.DataFrame()
        
        print(f"Loading {len(dates_to_load)} days of data...")
        
        # Load and combine data
        all_data = []
        for date in dates_to_load:
            df = self.load_single_date(date)
            if not df.empty:
                all_data.append(df)
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"Loaded {len(combined):,} records")
            return combined
        
        return pd.DataFrame()
    
    def load_single_date(self, date: str) -> pd.DataFrame:
        """
        Load data for a single date
        
        Args:
            date: Date in YYYYMMDD format
            
        Returns:
            DataFrame with options data
        """
        file_path = self.data_dir / date / f"zero_dte_spy_{date}.parquet"
        
        if not file_path.exists():
            return pd.DataFrame()
        
        try:
            # Load parquet file
            df = pd.read_parquet(file_path)
            
            # Add date column if not present
            if 'date' not in df.columns:
                df['date'] = pd.to_datetime(date, format='%Y%m%d')
            
            # Ensure timestamp is datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Rename columns to match OptionsLab format
            column_mapping = {
                'symbol': 'underlying_symbol',
                'right': 'option_type',
                'implied_vol': 'implied_volatility',
                'underlying_price_dollar': 'underlying_price'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns and new_col not in df.columns:
                    df[new_col] = df[old_col]
            
            # Ensure option_type is uppercase
            if 'option_type' in df.columns:
                df['option_type'] = df['option_type'].str.upper()
            
            # Add missing columns with defaults
            if 'volume' not in df.columns:
                df['volume'] = 0
            if 'open_interest' not in df.columns:
                df['open_interest'] = 0
            
            # Calculate mid price if not present
            if 'mid' not in df.columns and 'bid' in df.columns and 'ask' in df.columns:
                df['mid'] = (df['bid'] + df['ask']) / 2
            
            return df
            
        except Exception as e:
            print(f"Error loading {date}: {e}")
            return pd.DataFrame()
    
    def convert_to_optionslab_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert ThetaData format to OptionsLab format
        
        Args:
            df: ThetaData DataFrame
            
        Returns:
            DataFrame in OptionsLab format
        """
        if df.empty:
            return df
        
        # Create a copy
        result = df.copy()
        
        # Ensure required columns exist
        required_columns = [
            'timestamp', 'strike', 'expiration', 'option_type',
            'bid', 'ask', 'delta', 'gamma', 'theta', 'vega',
            'implied_volatility', 'underlying_price'
        ]
        
        for col in required_columns:
            if col not in result.columns:
                print(f"Warning: Missing column {col}")
                if col in ['bid', 'ask', 'delta', 'gamma', 'theta', 'vega']:
                    result[col] = 0.0
        
        # Add additional OptionsLab columns
        result['underlying_symbol'] = 'SPY'
        result['data_source'] = 'thetadata'
        
        # Sort by timestamp
        if 'timestamp' in result.columns:
            result = result.sort_values('timestamp')
        
        return result
    
    def get_vegaware_window_data(self, date: str) -> pd.DataFrame:
        """
        Get data for VegaAware trading window (2:30-4:00 PM ET)
        
        Args:
            date: Date in YYYYMMDD format
            
        Returns:
            Filtered DataFrame for VegaAware window
        """
        df = self.load_single_date(date)
        
        if df.empty:
            return df
        
        # Filter for VegaAware window
        df['time'] = pd.to_datetime(df['timestamp']).dt.time
        start_time = time(14, 30)  # 2:30 PM
        end_time = time(16, 0)     # 4:00 PM
        
        mask = (df['time'] >= start_time) & (df['time'] <= end_time)
        vegaware_data = df[mask].copy()
        
        # Drop the temporary time column
        vegaware_data = vegaware_data.drop('time', axis=1)
        
        return vegaware_data


def create_combined_dataset(start_date: str, end_date: str, output_path: str = None):
    """
    Create a combined dataset for OptionsLab
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_path: Optional path to save the combined data
    
    Returns:
        Combined DataFrame
    """
    loader = ThetaDataLoader()
    
    # Load data
    df = loader.load_date_range(start_date, end_date)
    
    if df.empty:
        print("No data loaded")
        return df
    
    # Convert to OptionsLab format
    df = loader.convert_to_optionslab_format(df)
    
    # Save if path provided
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.endswith('.parquet'):
            df.to_parquet(output_file, index=False)
        else:
            df.to_csv(output_file, index=False)
        
        print(f"Saved {len(df):,} records to {output_file}")
    
    return df


if __name__ == "__main__":
    # Test the loader
    loader = ThetaDataLoader()
    
    print(f"\nAvailable dates: {len(loader.available_dates)}")
    print(f"Date range: {loader.available_dates[0]} to {loader.available_dates[-1]}")
    
    # Test loading a single day
    test_date = "20250801"
    if test_date in loader.available_dates:
        print(f"\nLoading {test_date}...")
        df = loader.get_vegaware_window_data(test_date)
        
        if not df.empty:
            print(f"Loaded {len(df):,} records for VegaAware window")
            print(f"Columns: {df.columns.tolist()}")
            print(f"\nSample data:")
            print(df[['timestamp', 'strike', 'option_type', 'bid', 'ask', 'delta', 'vega']].head())
    
    # Test creating combined dataset for last week of July
    print("\nCreating combined dataset for last week of July 2025...")
    combined = create_combined_dataset(
        "2025-07-28", 
        "2025-08-01",
        "/Users/nish_macbook/trading/daily-optionslab/data/spy_options/SPY_0DTE_VEGAWARE_202507.parquet"
    )