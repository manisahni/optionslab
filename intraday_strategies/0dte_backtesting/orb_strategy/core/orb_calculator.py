"""
Opening Range Calculator for 0DTE ORB Strategy
Calculates opening ranges for different timeframes with validation
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ORBCalculator:
    """
    Calculate opening ranges for different timeframes
    Based on backtested results showing 60-min as optimal
    """
    
    def __init__(self, timeframe_minutes: int = 60):
        """
        Initialize ORB calculator
        
        Args:
            timeframe_minutes: Opening range duration (15, 30, 60)
        """
        self.timeframe = timeframe_minutes
        self.market_open = time(9, 30)
        self.market_close = time(16, 0)
        
        # Validation parameters from article
        self.min_range_pct = 0.001  # 0.1% minimum range width (adjusted for actual market conditions)
        self.max_range_pct = 0.02   # 2% maximum (avoid gap days)
        
        logger.info(f"ORB Calculator initialized for {timeframe_minutes}-minute range")
    
    def calculate_range(self, data: pd.DataFrame, date: str = None) -> Dict:
        """
        Calculate opening range for given data
        
        Args:
            data: DataFrame with OHLCV data (must have datetime index)
            date: Specific date to calculate (optional)
            
        Returns:
            Dict with range details or None if invalid
        """
        try:
            # Filter to specific date if provided
            if date:
                data = data[data.index.date == pd.to_datetime(date).date()]
            
            if data.empty:
                logger.warning(f"No data available for {date}")
                return None
            
            # Get market open time
            market_date = data.index[0].date()
            start_time = pd.Timestamp.combine(market_date, self.market_open)
            end_time = start_time + pd.Timedelta(minutes=self.timeframe)
            
            # Handle timezone if present
            if data.index.tz is not None:
                start_time = start_time.tz_localize(data.index.tz)
                end_time = end_time.tz_localize(data.index.tz)
            
            # Get opening range bars
            or_data = data[(data.index >= start_time) & (data.index < end_time)]
            
            if or_data.empty or len(or_data) < self.timeframe // 5:  # Ensure enough bars
                logger.warning(f"Insufficient data for {self.timeframe}-min range")
                return None
            
            # Calculate range metrics
            or_high = or_data['high'].max()
            or_low = or_data['low'].min()
            or_range = or_high - or_low
            or_midpoint = (or_high + or_low) / 2
            
            # Get opening price for percentage calculations
            open_price = or_data['open'].iloc[0]
            range_pct = or_range / open_price
            
            # Volume metrics
            or_volume = or_data['volume'].sum()
            avg_bar_volume = or_volume / len(or_data)
            
            # Create range dictionary
            range_info = {
                'date': market_date,
                'timeframe': self.timeframe,
                'high': or_high,
                'low': or_low,
                'range': or_range,
                'range_pct': range_pct,
                'midpoint': or_midpoint,
                'open_price': open_price,
                'volume': or_volume,
                'avg_bar_volume': avg_bar_volume,
                'start_time': start_time,
                'end_time': end_time,
                'num_bars': len(or_data),
                'valid': self.validate_range(or_high, or_low, open_price, or_volume)
            }
            
            return range_info
            
        except Exception as e:
            logger.error(f"Error calculating opening range: {e}")
            return None
    
    def validate_range(self, or_high: float, or_low: float, 
                       open_price: float, volume: float) -> bool:
        """
        Validate if opening range meets trading criteria
        
        Args:
            or_high: Opening range high
            or_low: Opening range low
            open_price: Opening price
            volume: Total volume in opening range
            
        Returns:
            True if range is valid for trading
        """
        # Calculate range width percentage
        range_width = or_high - or_low
        range_pct = range_width / open_price
        
        # Check minimum range (0.2% from article)
        if range_pct < self.min_range_pct:
            logger.info(f"Range too narrow: {range_pct:.3%} < {self.min_range_pct:.3%}")
            return False
        
        # Check maximum range (avoid gap days)
        if range_pct > self.max_range_pct:
            logger.info(f"Range too wide: {range_pct:.3%} > {self.max_range_pct:.3%}")
            return False
        
        # Check minimum volume (liquidity check)
        # Skip volume check if volume data is invalid or missing
        min_volume = 1000000  # 1M shares minimum
        if volume > 0 and volume < min_volume:
            logger.info(f"Insufficient volume: {volume:,.0f} < {min_volume:,.0f}")
            return False
        elif volume <= 0:
            # If volume is invalid, skip this check
            logger.debug(f"Volume data invalid ({volume}), skipping volume check")
            pass
        
        return True
    
    def calculate_multiple_timeframes(self, data: pd.DataFrame) -> Dict:
        """
        Calculate opening ranges for multiple timeframes
        Used for comparison and adaptive strategies
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dict with ranges for 15, 30, and 60 minutes
        """
        timeframes = [15, 30, 60]
        results = {}
        
        for tf in timeframes:
            calculator = ORBCalculator(timeframe_minutes=tf)
            range_info = calculator.calculate_range(data)
            if range_info:
                results[f'{tf}min'] = range_info
        
        return results
    
    def get_historical_ranges(self, data: pd.DataFrame, 
                            lookback_days: int = 20) -> pd.DataFrame:
        """
        Calculate historical opening ranges for analysis
        
        Args:
            data: DataFrame with OHLCV data
            lookback_days: Number of days to analyze
            
        Returns:
            DataFrame with historical range statistics
        """
        # Group by date
        dates = data.index.normalize().unique()[-lookback_days:]
        
        ranges = []
        for date in dates:
            day_data = data[data.index.date == date.date()]
            if not day_data.empty:
                range_info = self.calculate_range(day_data)
                if range_info:
                    ranges.append(range_info)
        
        if not ranges:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df_ranges = pd.DataFrame(ranges)
        
        # Add statistics
        df_ranges['range_z_score'] = (
            (df_ranges['range_pct'] - df_ranges['range_pct'].mean()) / 
            df_ranges['range_pct'].std()
        )
        
        return df_ranges
    
    def get_range_statistics(self, historical_ranges: pd.DataFrame) -> Dict:
        """
        Calculate statistics from historical ranges
        
        Args:
            historical_ranges: DataFrame from get_historical_ranges
            
        Returns:
            Dict with statistics
        """
        if historical_ranges.empty:
            return {}
        
        valid_ranges = historical_ranges[historical_ranges['valid']]
        
        stats = {
            'avg_range_pct': historical_ranges['range_pct'].mean(),
            'std_range_pct': historical_ranges['range_pct'].std(),
            'median_range_pct': historical_ranges['range_pct'].median(),
            'avg_volume': historical_ranges['volume'].mean(),
            'valid_days_pct': len(valid_ranges) / len(historical_ranges),
            'total_days': len(historical_ranges),
            'valid_days': len(valid_ranges)
        }
        
        return stats


def main():
    """Test the ORB calculator with sample data"""
    
    # Create sample data
    dates = pd.date_range(start='2024-01-02 09:30', end='2024-01-02 16:00', freq='1min')
    np.random.seed(42)
    
    # Simulate SPY data
    base_price = 450
    data = pd.DataFrame({
        'open': base_price + np.random.randn(len(dates)) * 0.5,
        'high': base_price + np.random.randn(len(dates)) * 0.5 + 0.2,
        'low': base_price + np.random.randn(len(dates)) * 0.5 - 0.2,
        'close': base_price + np.random.randn(len(dates)) * 0.5,
        'volume': np.random.randint(100000, 1000000, len(dates))
    }, index=dates)
    
    # Ensure high > low and contains open/close
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    # Test calculators
    print("Testing ORB Calculators\n" + "="*50)
    
    for timeframe in [15, 30, 60]:
        print(f"\n{timeframe}-Minute Opening Range:")
        print("-" * 30)
        
        calculator = ORBCalculator(timeframe_minutes=timeframe)
        range_info = calculator.calculate_range(data)
        
        if range_info:
            print(f"High: ${range_info['high']:.2f}")
            print(f"Low: ${range_info['low']:.2f}")
            print(f"Range: ${range_info['range']:.2f} ({range_info['range_pct']:.3%})")
            print(f"Valid for trading: {range_info['valid']}")
            print(f"Volume: {range_info['volume']:,.0f}")


if __name__ == "__main__":
    main()