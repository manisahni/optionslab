import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from freezegun import freeze_time

@pytest.fixture
def sample_spy_data():
    """Create sample SPY data for testing"""
    # Create a date range for one trading day
    eastern = pytz.timezone('US/Eastern')
    base_date = datetime(2024, 1, 15, 9, 30, tzinfo=eastern)
    
    # Generate 390 minutes (6.5 hours of trading)
    dates = [base_date + timedelta(minutes=i) for i in range(390)]
    
    # Generate realistic price data
    np.random.seed(42)
    base_price = 450.0
    prices = []
    
    for i in range(390):
        # Add some volatility
        change = np.random.normal(0, 0.5)
        base_price += change
        prices.append(base_price)
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'open': prices + np.random.normal(0, 0.1, 390),
        'high': prices + abs(np.random.normal(0.2, 0.1, 390)),
        'low': prices - abs(np.random.normal(0.2, 0.1, 390)),
        'close': prices + np.random.normal(0, 0.05, 390),
        'volume': np.random.randint(100000, 1000000, 390).astype(float),
        'average': -1.0,  # Not used
        'barCount': -1.0  # Not used
    })
    
    # Ensure high >= close/open and low <= close/open
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    return df

@pytest.fixture
def multi_day_spy_data():
    """Create multi-day SPY data for testing"""
    eastern = pytz.timezone('US/Eastern')
    dfs = []
    
    # Create 5 trading days
    for day_offset in range(5):
        base_date = datetime(2024, 1, 15 + day_offset, 9, 30, tzinfo=eastern)
        
        # Skip weekends
        if base_date.weekday() >= 5:
            continue
            
        dates = [base_date + timedelta(minutes=i) for i in range(390)]
        
        # Generate price data with daily trend
        np.random.seed(42 + day_offset)
        base_price = 450.0 + day_offset * 2  # Slight upward trend
        prices = []
        
        for i in range(390):
            change = np.random.normal(0, 0.5)
            base_price += change
            prices.append(base_price)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices + np.random.normal(0, 0.1, 390),
            'high': prices + abs(np.random.normal(0.2, 0.1, 390)),
            'low': prices - abs(np.random.normal(0.2, 0.1, 390)),
            'close': prices + np.random.normal(0, 0.05, 390),
            'volume': np.random.randint(100000, 1000000, 390).astype(float),
            'average': -1.0,
            'barCount': -1.0
        })
        
        df['high'] = df[['open', 'close', 'high']].max(axis=1)
        df['low'] = df[['open', 'close', 'low']].min(axis=1)
        
        dfs.append(df)
    
    return pd.concat(dfs, ignore_index=True)

@pytest.fixture
def mock_trading_hours():
    """Mock trading hours for testing"""
    return {
        'market_open': datetime.strptime('09:30', '%H:%M').time(),
        'market_close': datetime.strptime('16:00', '%H:%M').time(),
        'pre_market_start': datetime.strptime('04:00', '%H:%M').time(),
        'after_hours_end': datetime.strptime('20:00', '%H:%M').time()
    }

@pytest.fixture
def strategy_config():
    """Default strategy configuration for testing"""
    return {
        'opening_range_minutes': 30,
        'vwap_threshold': 0.002,
        'gap_threshold': 0.005,
        'stop_loss': 0.01,
        'position_size': 100
    }

@pytest.fixture
def frozen_market_time():
    """Freeze time at market open for consistent testing"""
    eastern = pytz.timezone('US/Eastern')
    market_open = datetime(2024, 1, 15, 9, 30, tzinfo=eastern)
    with freeze_time(market_open):
        yield market_open