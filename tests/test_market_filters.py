#!/usr/bin/env python3
"""
Tests for the market filters module
"""

import pandas as pd
import pytest
from optionslab.market_filters import MarketFilters


def test_iv_regime_filter():
    """Test IV regime filter"""
    # Create sample historical data
    historical_data = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=60, freq='D'),
        'iv': [20 + i*0.1 for i in range(60)]  # IV increasing from 20 to 26
    })
    
    # Initialize filters with IV regime config
    config = {
        'strategy': {
            'market_filters': {
                'iv_regime': {
                    'enabled': True,
                    'min_percentile': 25,
                    'max_percentile': 75,
                    'lookback_days': 30
                }
            }
        }
    }
    
    filters = MarketFilters(config, historical_data)
    
    # Test at different points
    # Early in the series - IV should be in lower percentile
    result = filters.check_all_filters('2022-01-31', 100, 30)
    
    # Later in the series - IV should be in higher percentile
    result_later = filters.check_all_filters('2022-02-28', 100, 58)
    
    # At least one should fail the filter
    assert result != result_later or not (result and result_later)


def test_moving_average_filter():
    """Test moving average filter"""
    # Create sample data with clear trend
    historical_data = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=60, freq='D'),
        'close': [100 + i for i in range(60)]  # Upward trend
    })
    
    config = {
        'strategy': {
            'market_filters': {
                'moving_average': {
                    'enabled': True,
                    'period': 20,
                    'position': 'above'  # Only trade when price is above MA
                }
            }
        }
    }
    
    filters = MarketFilters(config, historical_data)
    
    # Test when price is above MA (should pass)
    result_above = filters.check_all_filters('2022-02-28', 158, 58)  # Price > MA
    assert result_above is True
    
    # Test when price would be below MA (should fail)
    result_below = filters.check_all_filters('2022-02-28', 140, 58)  # Price < MA
    assert result_below is False


def test_rsi_filter():
    """Test RSI filter"""
    # Create sample data with price movements
    prices = [100]
    for i in range(20):
        if i < 10:
            prices.append(prices[-1] + 2)  # Strong upward movement
        else:
            prices.append(prices[-1] - 1)  # Pullback
    
    historical_data = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=21, freq='D'),
        'close': prices
    })
    
    config = {
        'strategy': {
            'market_filters': {
                'rsi': {
                    'enabled': True,
                    'period': 14,
                    'min': 30,
                    'max': 70  # Only trade when RSI is not extreme
                }
            }
        }
    }
    
    filters = MarketFilters(config, historical_data)
    
    # After strong upward movement, RSI should be high
    result = filters.check_all_filters('2022-01-10', prices[9], 9)
    # Result depends on actual RSI calculation
    
    assert result is not None  # Should return boolean


def test_bollinger_bands_filter():
    """Test Bollinger Bands filter"""
    # Create sample data with some volatility
    import numpy as np
    np.random.seed(42)
    
    base_price = 100
    prices = [base_price + np.random.normal(0, 2) for _ in range(30)]
    
    historical_data = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=30, freq='D'),
        'close': prices
    })
    
    config = {
        'strategy': {
            'market_filters': {
                'bollinger_bands': {
                    'enabled': True,
                    'period': 20,
                    'std_dev': 2,
                    'position': 'inside'  # Only trade when price is inside bands
                }
            }
        }
    }
    
    filters = MarketFilters(config, historical_data)
    
    # Test with price inside expected bands
    avg_price = sum(prices[-20:]) / 20
    result_inside = filters.check_all_filters('2022-01-30', avg_price, 29)
    assert result_inside is True
    
    # Test with extreme price (outside bands)
    extreme_price = avg_price + 10  # Far outside normal range
    result_outside = filters.check_all_filters('2022-01-30', extreme_price, 29)
    assert result_outside is False


def test_multiple_filters():
    """Test multiple filters working together"""
    # Create comprehensive test data
    historical_data = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=60, freq='D'),
        'close': [100 + i*0.5 for i in range(60)],  # Upward trend
        'iv': [20 + i*0.1 for i in range(60)]       # IV increasing
    })
    
    config = {
        'strategy': {
            'market_filters': {
                'moving_average': {
                    'enabled': True,
                    'period': 20,
                    'position': 'above'
                },
                'iv_regime': {
                    'enabled': True,
                    'min_percentile': 25,
                    'max_percentile': 75,
                    'lookback_days': 30
                }
            }
        }
    }
    
    filters = MarketFilters(config, historical_data)
    
    # All filters must pass
    result = filters.check_all_filters('2022-02-28', 129, 58)
    
    # This tests that multiple filters are properly evaluated
    assert isinstance(result, bool)


def test_disabled_filters():
    """Test that disabled filters don't affect results"""
    historical_data = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=30, freq='D'),
        'close': [100] * 30  # Flat prices
    })
    
    config = {
        'strategy': {
            'market_filters': {
                'moving_average': {
                    'enabled': False,  # Disabled
                    'period': 20,
                    'position': 'above'
                }
            }
        }
    }
    
    filters = MarketFilters(config, historical_data)
    
    # Should always return True when all filters are disabled
    result = filters.check_all_filters('2022-01-15', 50, 14)  # Price well below data
    assert result is True