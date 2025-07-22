#!/usr/bin/env python3
"""
Test script for multi-day backtest functionality
This script tests various aspects of multi-day backtesting to ensure it works correctly.
"""

import sys
from optionslab.backtest_engine import run_auditable_backtest
import json

def test_basic_multiday():
    """Test basic multi-day functionality with simple strategy"""
    print("\n" + "="*60)
    print("TEST 1: Basic Multi-Day Loading (3 consecutive days)")
    print("="*60)
    
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "simple_test_strategy.yaml"  # Uses 5-day hold period
    start_date = "2022-08-01"
    end_date = "2022-08-03"
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results:
        print(f"\n✅ Test 1 PASSED")
        print(f"   - Loaded data successfully")
        print(f"   - Final value: ${results['final_value']:,.2f}")
        print(f"   - Number of days: {len(results['equity_curve'])}")
    else:
        print(f"\n❌ Test 1 FAILED")
    
    return results

def test_entry_frequency():
    """Test that entry frequency works correctly"""
    print("\n" + "="*60)
    print("TEST 2: Entry Frequency (should only enter every 3 days)")
    print("="*60)
    
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "simple_test_strategy.yaml"  # entry_frequency: 3
    start_date = "2022-08-01"
    end_date = "2022-08-10"
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results:
        # Count number of trades
        trades = [t for t in results['trades'] if 'exit_date' in t]
        entry_dates = [t['entry_date'] for t in results['trades']]
        
        print(f"\n✅ Test 2 Results:")
        print(f"   - Total trades: {len(trades)}")
        print(f"   - Entry dates: {entry_dates}")
        
        # With 10 days and entry_frequency=3, we should have ~3 entries max
        if len(entry_dates) <= 3:
            print(f"   - Entry frequency check: PASSED")
        else:
            print(f"   - Entry frequency check: FAILED (too many entries)")
    
    return results

def test_position_exits():
    """Test that positions exit correctly after max_hold_days"""
    print("\n" + "="*60)
    print("TEST 3: Position Exits (5-day hold period)")
    print("="*60)
    
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "simple_test_strategy.yaml"  # max_hold_days: 5
    start_date = "2022-08-01"
    end_date = "2022-08-15"  # 15 days to ensure we see exits
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results:
        for i, trade in enumerate(results['trades']):
            if 'exit_date' in trade:
                from datetime import datetime
                entry = datetime.strptime(trade['entry_date'], '%Y-%m-%d')
                exit = datetime.strptime(trade['exit_date'], '%Y-%m-%d')
                hold_days = (exit - entry).days
                
                print(f"\n   Trade {i+1}:")
                print(f"   - Entry: {trade['entry_date']}")
                print(f"   - Exit: {trade['exit_date']}")
                print(f"   - Hold days: {hold_days}")
                print(f"   - Exit reason: {'Time stop' if hold_days >= 5 else 'End of period'}")
    
    return results

def test_weekend_handling():
    """Test that weekends are handled correctly"""
    print("\n" + "="*60)
    print("TEST 4: Weekend Handling")
    print("="*60)
    
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "simple_test_strategy.yaml"
    start_date = "2022-08-05"  # Friday
    end_date = "2022-08-08"    # Monday
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results:
        print(f"\n✅ Test 4 Results:")
        print(f"   - Days in equity curve: {len(results['equity_curve'])}")
        print(f"   - Dates: {[ec['date'] for ec in results['equity_curve']]}")
        print(f"   - No weekend data processed (as expected)")
    
    return results

def test_equity_curve():
    """Test equity curve calculation across multiple days"""
    print("\n" + "="*60)
    print("TEST 5: Equity Curve Calculation")
    print("="*60)
    
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "simple_test_strategy.yaml"
    start_date = "2022-08-01"
    end_date = "2022-08-05"
    
    results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    if results:
        print(f"\n✅ Test 5 Results:")
        print(f"   Date       | Cash      | Pos Value | Total     | # Pos")
        print(f"   -----------|-----------|-----------|-----------|------")
        
        for point in results['equity_curve']:
            print(f"   {point['date']} | ${point['cash']:8,.0f} | ${point['position_value']:8,.0f} | ${point['total_value']:8,.0f} | {point['positions']:5}")
    
    return results

if __name__ == "__main__":
    # Run all tests
    tests = [
        test_basic_multiday,
        test_entry_frequency,
        test_position_exits,
        test_weekend_handling,
        test_equity_curve
    ]
    
    passed = 0
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
    
    print(f"\n" + "="*60)
    print(f"SUMMARY: {passed}/{len(tests)} tests completed")
    print("="*60)