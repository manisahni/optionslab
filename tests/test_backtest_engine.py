#!/usr/bin/env python3
"""
Tests for the backtest engine module
"""

import pytest
from optionslab.backtest_engine import run_auditable_backtest


def test_basic_backtest_execution():
    """Test basic backtest execution"""
    # Test configuration
    data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    config_file = "simple_test_strategy.yaml"
    start_date = "2022-01-01"
    end_date = "2022-01-31"
    
    # Run backtest
    results = run_auditable_backtest(data_file, config_file, start_date, end_date)
    
    # Verify results structure
    assert results is not None
    assert 'metrics' in results
    assert 'trades' in results
    assert 'equity_curve' in results
    assert 'final_value' in results
    assert 'total_return' in results


def test_multi_position_handling():
    """Test handling of multiple concurrent positions"""
    # This test was moved from test_multi_positions.py
    data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    config_file = "simple_test_strategy.yaml"
    start_date = "2022-06-01"
    end_date = "2022-06-30"
    
    results = run_auditable_backtest(data_file, config_file, start_date, end_date)
    
    # Check for proper position tracking
    assert 'trades' in results
    if len(results['trades']) > 1:
        # Verify no overlapping positions if not allowed
        for i in range(1, len(results['trades'])):
            prev_trade = results['trades'][i-1]
            curr_trade = results['trades'][i]
            if 'exit_date' in prev_trade and 'entry_date' in curr_trade:
                # Current trade should start after previous trade exits
                assert curr_trade['entry_date'] >= prev_trade['exit_date']


def test_weekend_handling():
    """Test proper handling of weekends"""
    # This test was moved from test_multiday_backtest.py
    data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    config_file = "simple_test_strategy.yaml"
    # Pick a date range that includes weekends
    start_date = "2022-01-07"  # Friday
    end_date = "2022-01-14"    # Following Friday
    
    results = run_auditable_backtest(data_file, config_file, start_date, end_date)
    
    # Verify no trades on weekends
    if results and results['trades']:
        for trade in results['trades']:
            entry_date = trade['entry_date']
            # Check that entry dates are weekdays (Mon=0, Sun=6)
            from datetime import datetime
            dt = datetime.strptime(entry_date, "%Y-%m-%d")
            assert dt.weekday() < 5  # Monday to Friday only


def test_error_handling():
    """Test error handling for invalid inputs"""
    # Test with non-existent file
    with pytest.raises(Exception):
        run_auditable_backtest(
            "non_existent_file.parquet",
            "simple_test_strategy.yaml",
            "2022-01-01",
            "2022-01-31"
        )
    
    # Test with invalid date range
    data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    config_file = "simple_test_strategy.yaml"
    
    # End date before start date should handle gracefully
    results = run_auditable_backtest(data_file, config_file, "2022-01-31", "2022-01-01")
    assert results is not None  # Should handle gracefully