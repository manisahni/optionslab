#!/usr/bin/env python3
"""
Data Scientist Utilities for OptionsLab
Provides efficient access to SPY options parquet data for analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import pyarrow.parquet as pq
import pyarrow as pa

class DataScientistUtils:
    """Utilities for accessing and analyzing SPY options data"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.master_file = self.data_dir / "SPY_OPTIONS_MASTER_20200715_20250711.parquet"
        self._cached_data = None
        self._cache_dates = None
        
    def load_data_range(self, start_date: str, end_date: str, 
                       columns: Optional[List[str]] = None) -> pd.DataFrame:
        """Load options data for a specific date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            columns: Optional list of columns to load (None = all columns)
            
        Returns:
            DataFrame with options data
        """
        # Convert string dates to datetime
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Use pyarrow for efficient filtering
        filters = [
            ('date', '>=', start),
            ('date', '<=', end)
        ]
        
        if columns:
            # Always include date for filtering
            if 'date' not in columns:
                columns = ['date'] + columns
                
        df = pd.read_parquet(self.master_file, 
                           columns=columns,
                           filters=filters,
                           engine='pyarrow')
        
        return df
    
    def get_unique_expirations(self, as_of_date: Optional[str] = None) -> List[str]:
        """Get unique expiration dates available in dataset
        
        Args:
            as_of_date: Optional date to filter expirations after
            
        Returns:
            List of expiration dates as strings
        """
        # Load just expiration column for efficiency
        df = pd.read_parquet(self.master_file, columns=['expiration', 'date'])
        
        if as_of_date:
            cutoff = pd.to_datetime(as_of_date)
            df = df[df['date'] <= cutoff]
            
        unique_exp = df['expiration'].drop_duplicates().sort_values()
        return unique_exp.dt.strftime('%Y-%m-%d').tolist()
    
    def get_iv_surface(self, date: str, expiration: Optional[str] = None) -> pd.DataFrame:
        """Get implied volatility surface for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format
            expiration: Optional specific expiration to filter
            
        Returns:
            DataFrame with strike, expiration, IV data
        """
        filters = [('date', '=', pd.to_datetime(date))]
        if expiration:
            filters.append(('expiration', '=', pd.to_datetime(expiration)))
            
        df = pd.read_parquet(self.master_file,
                           columns=['strike', 'expiration', 'right', 'implied_vol', 
                                   'underlying_price', 'volume', 'open_interest'],
                           filters=filters,
                           engine='pyarrow')
        
        # Convert strike from cents to dollars
        df['strike'] = df['strike'] / 100
        
        # Calculate moneyness
        df['moneyness'] = df['strike'] / df['underlying_price']
        
        # Calculate days to expiration
        df['dte'] = (df['expiration'] - pd.to_datetime(date)).dt.days
        
        return df.sort_values(['expiration', 'strike'])
    
    def get_greeks_distribution(self, date: str, greek: str = 'delta') -> pd.DataFrame:
        """Get distribution of a specific Greek for a date
        
        Args:
            date: Date in YYYY-MM-DD format
            greek: Greek to analyze (delta, gamma, theta, vega, rho)
            
        Returns:
            DataFrame with Greek distributions
        """
        valid_greeks = ['delta', 'gamma', 'theta', 'vega', 'rho']
        if greek not in valid_greeks:
            raise ValueError(f"Greek must be one of: {valid_greeks}")
            
        df = pd.read_parquet(self.master_file,
                           columns=['strike', 'expiration', 'right', greek, 
                                   'volume', 'open_interest', 'underlying_price'],
                           filters=[('date', '=', pd.to_datetime(date))],
                           engine='pyarrow')
        
        # Convert strike from cents to dollars
        df['strike'] = df['strike'] / 100
        
        # Add DTE
        df['dte'] = (df['expiration'] - pd.to_datetime(date)).dt.days
        
        return df
    
    def analyze_option_flow(self, date: str, min_volume: int = 1000) -> pd.DataFrame:
        """Analyze option flow for unusual activity
        
        Args:
            date: Date in YYYY-MM-DD format
            min_volume: Minimum volume threshold
            
        Returns:
            DataFrame with high-volume options
        """
        # Get current day data
        df = pd.read_parquet(self.master_file,
                           columns=['strike', 'expiration', 'right', 'volume',
                                   'open_interest', 'close', 'underlying_price',
                                   'implied_vol', 'delta'],
                           filters=[('date', '=', pd.to_datetime(date))],
                           engine='pyarrow')
        
        # Filter for high volume
        df = df[df['volume'] >= min_volume]
        
        # Convert strike from cents to dollars
        df['strike'] = df['strike'] / 100
        
        # Calculate volume/OI ratio
        df['volume_oi_ratio'] = df['volume'] / df['open_interest'].clip(lower=1)
        
        # Calculate premium
        df['premium'] = df['close'] * df['volume']
        
        # Add DTE
        df['dte'] = (df['expiration'] - pd.to_datetime(date)).dt.days
        
        # Sort by premium
        return df.sort_values('premium', ascending=False)
    
    def get_historical_iv_percentile(self, date: str, lookback_days: int = 252) -> pd.DataFrame:
        """Calculate IV percentile ranks
        
        Args:
            date: Current date
            lookback_days: Days to look back for percentile calculation
            
        Returns:
            DataFrame with IV percentiles by strike/expiration
        """
        end_date = pd.to_datetime(date)
        start_date = end_date - timedelta(days=lookback_days)
        
        # Load historical IV data
        df = pd.read_parquet(self.master_file,
                           columns=['date', 'strike', 'expiration', 'right', 'implied_vol'],
                           filters=[
                               ('date', '>=', start_date),
                               ('date', '<=', end_date),
                               ('expiration', '>', end_date)  # Only future expirations
                           ],
                           engine='pyarrow')
        
        # Calculate percentile for each strike/expiration/right combo
        current_iv = df[df['date'] == end_date].copy()
        
        # Calculate historical stats
        hist_stats = df.groupby(['strike', 'expiration', 'right'])['implied_vol'].agg([
            'mean', 'std', 'min', 'max',
            lambda x: np.percentile(x, 25),
            lambda x: np.percentile(x, 75)
        ])
        hist_stats.columns = ['mean', 'std', 'min', 'max', 'p25', 'p75']
        
        # Merge with current
        result = current_iv.merge(hist_stats, on=['strike', 'expiration', 'right'])
        
        # Calculate percentile rank
        result['iv_percentile'] = result.apply(
            lambda row: self._calculate_percentile_rank(
                row['implied_vol'], 
                df[(df['strike'] == row['strike']) & 
                   (df['expiration'] == row['expiration']) & 
                   (df['right'] == row['right'])]['implied_vol']
            ), axis=1
        )
        
        # Convert strike to dollars
        result['strike'] = result['strike'] / 100
        
        return result
    
    def _calculate_percentile_rank(self, value: float, series: pd.Series) -> float:
        """Calculate percentile rank of a value in a series"""
        return (series < value).sum() / len(series) * 100
    
    def get_market_summary(self, date: str) -> Dict:
        """Get market summary statistics for a date
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with market summary stats
        """
        df = pd.read_parquet(self.master_file,
                           filters=[('date', '=', pd.to_datetime(date))],
                           engine='pyarrow')
        
        # Get unique underlying price (should be same for all options on same date)
        underlying_price = df['underlying_price'].iloc[0]
        
        # Calculate summary stats
        summary = {
            'date': date,
            'underlying_price': underlying_price,
            'total_volume': df['volume'].sum(),
            'total_open_interest': df['open_interest'].sum(),
            'put_call_volume_ratio': df[df['right'] == 'P']['volume'].sum() / df[df['right'] == 'C']['volume'].sum(),
            'avg_iv_calls': df[df['right'] == 'C']['implied_vol'].mean(),
            'avg_iv_puts': df[df['right'] == 'P']['implied_vol'].mean(),
            'unique_expirations': df['expiration'].nunique(),
            'unique_strikes': df['strike'].nunique(),
            'avg_bid_ask_spread': (df['ask'] - df['bid']).mean()
        }
        
        # Add put/call OI ratio
        call_oi = df[df['right'] == 'C']['open_interest'].sum()
        put_oi = df[df['right'] == 'P']['open_interest'].sum()
        summary['put_call_oi_ratio'] = put_oi / call_oi if call_oi > 0 else 0
        
        return summary
    
    def calculate_gamma_exposure(self, date: str) -> pd.DataFrame:
        """Calculate gamma exposure by strike
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            DataFrame with gamma exposure by strike
        """
        df = pd.read_parquet(self.master_file,
                           columns=['strike', 'right', 'gamma', 'open_interest', 
                                   'underlying_price'],
                           filters=[('date', '=', pd.to_datetime(date))],
                           engine='pyarrow')
        
        # Convert strike from cents to dollars
        df['strike'] = df['strike'] / 100
        
        # Calculate gamma exposure (gamma * OI * 100 * spot^2 / 100)
        spot = df['underlying_price'].iloc[0]
        df['gamma_exposure'] = df['gamma'] * df['open_interest'] * 100 * spot * spot / 100
        
        # Adjust for put gamma (negative for market makers)
        df.loc[df['right'] == 'P', 'gamma_exposure'] *= -1
        
        # Aggregate by strike
        gamma_by_strike = df.groupby('strike')['gamma_exposure'].sum().reset_index()
        gamma_by_strike['cumulative_gamma'] = gamma_by_strike['gamma_exposure'].cumsum()
        
        return gamma_by_strike.sort_values('strike')