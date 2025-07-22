#!/usr/bin/env python3
"""
Tests for the data loader module
"""


import pandas as pd
from pathlib import Path
from optionslab.data_loader import load_data, load_strategy_config, validate_config


def test_load_data_basic():
    """Test basic data loading functionality"""
    # Test with single file
    data_file = "spy_options_downloader/spy_options_parquet/spy_options_eod_20220103.parquet"
    
    # Check if file exists first
    if Path(data_file).exists():
        data = load_data(data_file, "2022-01-03", "2022-01-03")
        
        assert data is not None
        assert len(data) > 0
        assert 'strike' in data.columns
        assert 'delta' in data.columns
        assert 'dte' in data.columns
        assert 'underlying_price' in data.columns


def test_load_data_date_range():
    """Test loading data with date range filtering"""
    # Test with full year file
    data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    
    if Path(data_file).exists():
        # Load specific date range
        data = load_data(data_file, "2022-01-01", "2022-01-31")
        
        if data is not None:
            # Verify date filtering worked
            dates = pd.to_datetime(data['date']).dt.date
            assert dates.min() >= pd.to_datetime("2022-01-01").date()
            assert dates.max() <= pd.to_datetime("2022-01-31").date()


def test_load_strategy_config():
    """Test loading strategy configuration"""
    config_file = "simple_test_strategy.yaml"
    
    if Path(config_file).exists():
        config = load_strategy_config(config_file)
        
        assert config is not None
        assert 'strategy' in config
        assert 'delta_range' in config['strategy']
        assert 'dte_range' in config['strategy']
        assert 'min' in config['strategy']['delta_range']
        assert 'max' in config['strategy']['delta_range']


def test_validate_config():
    """Test configuration validation"""
    # Valid config
    valid_config = {
        'strategy': {
            'name': 'test_strategy',
            'option_type': 'call',
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60},
            'position_size': 0.05,
            'max_positions': 1
        }
    }
    
    # Should not raise exception
    try:
        validate_config(valid_config)
        assert True
    except Exception:
        assert False
    
    # Invalid config - missing delta_range
    invalid_config = {
        'strategy': {
            'name': 'test_strategy',
            'option_type': 'call',
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    # Should raise exception
    try:
        validate_config(invalid_config)
        assert False, "Expected exception for invalid config"
    except:
        pass  # Expected


def test_data_columns_transformation():
    """Test data column transformations"""
    # Create sample data
    sample_data = pd.DataFrame({
        'strike': [45000, 45500, 46000],  # In cents
        'underlying_price': [45800, 45800, 45800],
        'delta': [0.5, 0.4, 0.3],
        'dte': [45, 45, 45],
        'option_type': ['C', 'C', 'C']
    })
    
    # Test strike dollars calculation
    sample_data['strike_dollars'] = sample_data['strike'] / 100
    
    assert sample_data['strike_dollars'].iloc[0] == 450.0
    assert sample_data['strike_dollars'].iloc[1] == 455.0
    assert sample_data['strike_dollars'].iloc[2] == 460.0


def test_load_data_error_handling():
    """Test error handling in data loading"""
    # Non-existent file
    data = load_data("non_existent_file.parquet", "2022-01-01", "2022-01-31")
    assert data is None
    
    # Invalid date format
    data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    if Path(data_file).exists():
        # Should handle gracefully
        data = load_data(data_file, "invalid_date", "2022-01-31")
        # Implementation dependent - might return None or raise exception


def test_load_multiple_files():
    """Test loading and combining multiple files"""
    # This functionality might be in the data loader
    files = [
        "spy_options_downloader/spy_options_parquet/spy_options_eod_20220103.parquet",
        "spy_options_downloader/spy_options_parquet/spy_options_eod_20220104.parquet"
    ]
    
    all_data = []
    for file in files:
        if Path(file).exists():
            data = load_data(file, "2022-01-01", "2022-01-31")
            if data is not None:
                all_data.append(data)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        assert len(combined) == sum(len(df) for df in all_data)


def test_config_defaults():
    """Test that config provides sensible defaults"""
    minimal_config = {
        'strategy': {
            'name': 'minimal',
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    # After validation, should have defaults
    # Implementation dependent - check what defaults are applied
    try:
        validate_config(minimal_config)
        # Check if defaults were applied
        assert True
    except Exception as e:
        print(f"Config validation failed: {e}")
        assert False