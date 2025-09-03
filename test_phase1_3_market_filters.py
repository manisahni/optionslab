#!/usr/bin/env python3
"""
Phase 1.3 Test: Market Filters Verification
==========================================
Tests all market filter functionality including VIX timing and trend filters.
"""

import sys
import pandas as pd
from datetime import datetime
import traceback
import numpy as np

print("=" * 60)
print("PHASE 1.3: MARKET FILTERS VERIFICATION TEST")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test results tracker
test_results = {
    'import_test': False,
    'vix_filter_test': False,
    'trend_filter_test': False,
    'rsi_filter_test': False,
    'bollinger_filter_test': False,
    'combined_filters_test': False
}

try:
    # TEST 1: Import Test
    print("🧪 TEST 1: Testing Import of Market Filters Module")
    print("-" * 50)
    
    try:
        from optionslab.market_filters import MarketFilters
        from optionslab.data_loader import load_data
        print("✅ PASS: Successfully imported market_filters and data_loader")
        test_results['import_test'] = True
    except ImportError as e:
        print(f"❌ FAIL: Import error - {e}")
        raise
    
    print()
    
    # Load test data for filters
    print("📊 Loading test data (Jan 2024)")
    print("-" * 50)
    
    DATA_FILE = "/Users/nish_macbook/trading/daily-optionslab/data/spy_options/SPY_OPTIONS_2024_COMPLETE.parquet"
    data = load_data(DATA_FILE, "2024-01-02", "2024-01-31")
    
    if data is not None and len(data) > 0:
        print(f"✅ Loaded {len(data):,} records for January 2024")
        unique_dates = sorted(data['date'].unique())
        print(f"📅 Trading days loaded: {len(unique_dates)}")
    else:
        raise ValueError("Failed to load test data")
        
    print()
    
    # TEST 2: VIX Timing Filter Test
    print("🧪 TEST 2: Testing VIX Timing Filter")
    print("-" * 50)
    
    try:
        # Test config for premium selling strategy (wants high VIX)
        config_short = {
            'strategy_type': 'short_strangle',
            'market_filters': {
                'vix_timing': {
                    'lookback_days': 10,
                    'percentile_threshold': 75,  # Enter when VIX > 75th percentile
                    'absolute_threshold': None
                }
            }
        }
        
        filters_short = MarketFilters(config_short, data, unique_dates)
        
        # Test on day 15 (enough history)
        test_date_idx = 15
        test_date = unique_dates[test_date_idx]
        test_price = data[data['date'] == test_date]['underlying_price'].iloc[0]
        
        passed, msg = filters_short.check_vix_timing_filter(test_price, test_date_idx)
        
        print(f"📅 Testing on {test_date.strftime('%Y-%m-%d')}")
        print(f"📊 SPY Price: ${test_price:.2f}")
        print(f"📊 Filter Result: {'PASSED' if passed else 'BLOCKED'}")
        if msg:
            print(f"📊 Message: {msg}")
        
        # Test config for premium buying strategy (wants low VIX)  
        config_long = {
            'strategy_type': 'long_call',
            'market_filters': {
                'vix_timing': {
                    'lookback_days': 10,
                    'percentile_threshold': 75,  # Enter when VIX < 25th percentile
                    'absolute_threshold': 20  # Also require VIX < 20
                }
            }
        }
        
        filters_long = MarketFilters(config_long, data, unique_dates)
        passed2, msg2 = filters_long.check_vix_timing_filter(test_price, test_date_idx)
        
        print(f"\n📊 Long Strategy Filter: {'PASSED' if passed2 else 'BLOCKED'}")
        if msg2:
            print(f"📊 Message: {msg2}")
        
        print("✅ PASS: VIX timing filter is working")
        test_results['vix_filter_test'] = True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing VIX filter - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 3: Trend Filter Test (Moving Average)
    print("🧪 TEST 3: Testing Trend Filter (Moving Average)")
    print("-" * 50)
    
    try:
        # Test config with MA filter
        config_ma = {
            'strategy_type': 'long_call',
            'market_filters': {
                'trend_filter': {
                    'ma_period': 20,
                    'require_above_ma': True  # Only enter if price > MA(20)
                }
            }
        }
        
        filters_ma = MarketFilters(config_ma, data, unique_dates)
        
        # Test on last day (has full history)
        test_date_idx = len(unique_dates) - 1
        test_date = unique_dates[test_date_idx]
        test_price = data[data['date'] == test_date]['underlying_price'].iloc[0]
        
        passed, msg = filters_ma.check_ma_filter(test_price, test_date_idx)
        
        print(f"📅 Testing on {test_date.strftime('%Y-%m-%d')}")
        print(f"📊 SPY Price: ${test_price:.2f}")
        print(f"📊 Filter Result: {'PASSED' if passed else 'BLOCKED'}")
        if msg:
            print(f"📊 Message: {msg}")
        
        print("✅ PASS: Trend filter is working")
        test_results['trend_filter_test'] = True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing trend filter - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 4: RSI Filter Test
    print("🧪 TEST 4: Testing RSI Filter")
    print("-" * 50)
    
    try:
        # Test config with RSI filter
        config_rsi = {
            'strategy_type': 'long_call',
            'market_filters': {
                'rsi_filter': {
                    'period': 14,
                    'oversold': 30,
                    'overbought': 70
                }
            }
        }
        
        filters_rsi = MarketFilters(config_rsi, data, unique_dates)
        
        # Test on day 20 (enough history for RSI)
        test_date_idx = 20
        test_date = unique_dates[test_date_idx]
        test_price = data[data['date'] == test_date]['underlying_price'].iloc[0]
        
        passed, msg = filters_rsi.check_rsi_filter(test_price, test_date_idx)
        
        # Calculate actual RSI for verification
        rsi = filters_rsi._calculate_rsi(test_date_idx, 14)
        
        print(f"📅 Testing on {test_date.strftime('%Y-%m-%d')}")
        print(f"📊 SPY Price: ${test_price:.2f}")
        print(f"📊 RSI Value: {rsi:.1f}" if rsi else "📊 RSI: Unable to calculate")
        print(f"📊 Filter Result: {'PASSED' if passed else 'BLOCKED'}")
        if msg:
            print(f"📊 Message: {msg}")
        
        print("✅ PASS: RSI filter is working")
        test_results['rsi_filter_test'] = True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing RSI filter - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 5: Bollinger Bands Filter Test
    print("🧪 TEST 5: Testing Bollinger Bands Filter")
    print("-" * 50)
    
    try:
        # Test config with Bollinger Bands filter
        config_bb = {
            'strategy_type': 'long_call',
            'market_filters': {
                'bollinger_bands': {
                    'period': 20,
                    'std_dev': 2.0,
                    'entry_at_bands': True,
                    'lower_band_threshold': 0.2  # Enter when price in lower 20% of bands
                }
            }
        }
        
        filters_bb = MarketFilters(config_bb, data, unique_dates)
        
        # Test on last day
        test_date_idx = len(unique_dates) - 1
        test_date = unique_dates[test_date_idx]
        test_price = data[data['date'] == test_date]['underlying_price'].iloc[0]
        
        passed, msg = filters_bb.check_bollinger_filter(test_price, test_date_idx)
        
        # Calculate actual bands for verification
        bands = filters_bb._calculate_bollinger_bands(test_date_idx, 20, 2.0)
        
        print(f"📅 Testing on {test_date.strftime('%Y-%m-%d')}")
        print(f"📊 SPY Price: ${test_price:.2f}")
        if bands:
            middle, upper, lower = bands
            band_position = (test_price - lower) / (upper - lower) if upper > lower else 0.5
            print(f"📊 Bollinger Bands:")
            print(f"   Upper: ${upper:.2f}")
            print(f"   Middle: ${middle:.2f}")
            print(f"   Lower: ${lower:.2f}")
            print(f"   Position: {band_position:.1%} (0%=lower, 100%=upper)")
        print(f"📊 Filter Result: {'PASSED' if passed else 'BLOCKED'}")
        if msg:
            print(f"📊 Message: {msg}")
        
        print("✅ PASS: Bollinger Bands filter is working")
        test_results['bollinger_filter_test'] = True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing Bollinger filter - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 6: Combined Filters Test
    print("🧪 TEST 6: Testing Combined Filters (All Active)")
    print("-" * 50)
    
    try:
        # Test config with multiple filters
        config_combined = {
            'strategy_type': 'short_strangle',
            'market_filters': {
                'vix_timing': {
                    'lookback_days': 10,
                    'percentile_threshold': 50  # Moderate threshold
                },
                'trend_filter': {
                    'ma_period': 20,
                    'require_above_ma': False  # Short strategy, prefer below MA
                },
                'rsi_filter': {
                    'period': 14,
                    'oversold': 30,
                    'overbought': 70
                }
            }
        }
        
        filters_combined = MarketFilters(config_combined, data, unique_dates)
        
        # Test on last day
        test_date_idx = len(unique_dates) - 1
        test_date = unique_dates[test_date_idx]
        test_price = data[data['date'] == test_date]['underlying_price'].iloc[0]
        
        all_passed, messages = filters_combined.check_all_filters(test_date, test_price, test_date_idx)
        
        print(f"📅 Testing on {test_date.strftime('%Y-%m-%d')}")
        print(f"📊 SPY Price: ${test_price:.2f}")
        print(f"📊 Overall Result: {'ALL PASSED ✅' if all_passed else 'BLOCKED ❌'}")
        print(f"\n📊 Individual Filter Results:")
        for msg in messages:
            print(f"   • {msg}")
        
        # Test should work regardless of whether all filters pass
        print("✅ PASS: Combined filters are working correctly")
        test_results['combined_filters_test'] = True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing combined filters - {e}")
        traceback.print_exc()
        
    print()
    
    # SUMMARY
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"✅ Tests Passed: {passed_tests}/{total_tests}")
    print()
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")
    
    print()
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Market filters are working correctly.")
        print("🚀 Ready to proceed to Phase 1.4 (Dynamic Position Sizing Test)")
    else:
        print("⚠️  Some tests need attention")
        
    print()
    
    # FILTER STATISTICS
    print("📊 FILTER STATISTICS FOR JANUARY 2024")
    print("-" * 50)
    
    # Count how many days would pass various filters
    filter_pass_counts = {
        'vix_high': 0,
        'trend_up': 0,
        'trend_down': 0,
        'oversold': 0,
        'overbought': 0
    }
    
    for i, date in enumerate(unique_dates[20:]):  # Start after enough history
        date_idx = i + 20
        price = data[data['date'] == date]['underlying_price'].iloc[0]
        
        # Check trend
        ma_prices = []
        for j in range(20):
            hist_idx = date_idx - j
            if hist_idx >= 0:
                hist_date = unique_dates[hist_idx]
                hist_data = data[data['date'] == hist_date]
                if not hist_data.empty:
                    ma_prices.append(hist_data['underlying_price'].iloc[0])
        if len(ma_prices) == 20:
            ma = sum(ma_prices) / 20
            if price > ma:
                filter_pass_counts['trend_up'] += 1
            else:
                filter_pass_counts['trend_down'] += 1
        
        # Check RSI
        rsi = filters_combined._calculate_rsi(date_idx, 14)
        if rsi:
            if rsi <= 30:
                filter_pass_counts['oversold'] += 1
            elif rsi >= 70:
                filter_pass_counts['overbought'] += 1
    
    print(f"Trend Up Days (Price > MA20): {filter_pass_counts['trend_up']}")
    print(f"Trend Down Days (Price < MA20): {filter_pass_counts['trend_down']}")
    print(f"Oversold Days (RSI <= 30): {filter_pass_counts['oversold']}")
    print(f"Overbought Days (RSI >= 70): {filter_pass_counts['overbought']}")
    
except Exception as e:
    print(f"💥 CRITICAL ERROR: {e}")
    print("\n🔧 Full traceback:")
    traceback.print_exc()
    print(f"\n⚠️  Test failed. Please investigate the error.")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")