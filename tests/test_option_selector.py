#!/usr/bin/env python3
"""
Tests for the option selector module
"""

import pandas as pd
import pytest
from optionslab.option_selector import find_suitable_options, calculate_position_size
from optionslab.data_loader import load_data


def test_find_suitable_options_call():
    """Test finding suitable call options"""
    # Load sample data
    data_file = "spy_options_downloader/spy_options_parquet/spy_options_eod_20220103.parquet"
    data = load_data(data_file, "2022-01-03", "2022-01-03")
    
    if data is not None and len(data) > 0:
        current_price = data['underlying_price'].iloc[0]
        
        # Test configuration for call options
        config = {
            'strategy': {
                'option_type': 'call',
                'delta_range': {'min': 0.4, 'max': 0.6},
                'dte_range': {'min': 30, 'max': 60},
                'min_volume': 100
            }
        }
        
        # Find suitable options
        selected = find_suitable_options(data, current_price, config, "2022-01-03")
        
        # Verify selection meets criteria
        if selected is not None:
            assert 0.4 <= selected['delta'] <= 0.6
            assert 30 <= selected['dte'] <= 60
            assert selected['volume'] >= 100
            assert selected['option_type'] == 'C'


def test_find_suitable_options_put():
    """Test finding suitable put options"""
    # This test incorporates logic from test_put_options.py
    data_file = "spy_options_downloader/spy_options_parquet/spy_options_eod_20220815.parquet"
    data = load_data(data_file, "2022-08-15", "2022-08-15")
    
    if data is not None and len(data) > 0:
        current_price = data['underlying_price'].iloc[0]
        
        # Test configuration for put options
        config = {
            'strategy': {
                'option_type': 'put',
                'delta_range': {'min': -0.6, 'max': -0.4},
                'dte_range': {'min': 30, 'max': 60},
                'min_volume': 100
            }
        }
        
        # Find suitable options
        selected = find_suitable_options(data, current_price, config, "2022-08-15")
        
        # Verify selection meets criteria
        if selected is not None:
            assert -0.6 <= selected['delta'] <= -0.4
            assert 30 <= selected['dte'] <= 60
            assert selected['volume'] >= 100
            assert selected['option_type'] == 'P'


def test_calculate_position_size():
    """Test position size calculation"""
    # Test basic position sizing
    cash = 10000
    option_price = 2.50
    position_size_pct = 0.05  # 5% of capital
    
    contracts = calculate_position_size(cash, option_price, position_size_pct)
    
    # Should be 2 contracts: 10000 * 0.05 / (2.50 * 100) = 2
    assert contracts == 2
    
    # Test with max contracts limit
    contracts = calculate_position_size(cash, option_price, position_size_pct, max_contracts=1)
    assert contracts == 1
    
    # Test with very expensive option
    expensive_option = 50.0
    contracts = calculate_position_size(cash, expensive_option, position_size_pct)
    assert contracts == 0  # Can't afford even 1 contract


def test_delta_targeting():
    """Test delta-based option selection"""
    # Create sample data
    data = pd.DataFrame({
        'strike': [450, 455, 460, 465, 470],
        'delta': [0.7, 0.6, 0.5, 0.4, 0.3],
        'dte': [45, 45, 45, 45, 45],
        'volume': [1000, 1000, 1000, 1000, 1000],
        'ask': [10.0, 8.0, 6.0, 4.0, 2.0],
        'option_type': ['C', 'C', 'C', 'C', 'C'],
        'underlying_price': [460, 460, 460, 460, 460]
    })
    
    current_price = 460
    
    # Target 0.5 delta
    config = {
        'strategy': {
            'option_type': 'call',
            'delta_range': {'min': 0.45, 'max': 0.55},
            'dte_range': {'min': 30, 'max': 60},
            'min_volume': 100
        }
    }
    
    selected = find_suitable_options(data, current_price, config, "2022-01-03")
    
    if selected is not None:
        assert selected['delta'] == 0.5  # Should select the 0.5 delta option
        assert selected['strike'] == 460


def test_liquidity_filter():
    """Test liquidity filtering in option selection"""
    # Create data with varying liquidity
    data = pd.DataFrame({
        'strike': [460, 460, 460],
        'delta': [0.5, 0.5, 0.5],
        'dte': [45, 45, 45],
        'volume': [10, 500, 2000],  # Low, medium, high volume
        'ask': [6.0, 6.1, 6.2],
        'option_type': ['C', 'C', 'C'],
        'underlying_price': [460, 460, 460]
    })
    
    current_price = 460
    
    # Require minimum volume of 1000
    config = {
        'strategy': {
            'option_type': 'call',
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60},
            'min_volume': 1000
        }
    }
    
    selected = find_suitable_options(data, current_price, config, "2022-01-03")
    
    if selected is not None:
        assert selected['volume'] >= 1000  # Should only select high volume option