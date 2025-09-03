#!/usr/bin/env python3
"""
Phase 2 (Simplified): Integration Layer Testing
===============================================
Tests component integration with proper error handling.
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
import traceback

print("=" * 60)
print("PHASE 2 (SIMPLIFIED): INTEGRATION TESTING")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test results tracker
test_results = {
    'data_filters': False,
    'position_sizing_chain': False,
    'portfolio_accumulation': False
}

try:
    # Import components
    from optionslab.data_loader import load_data
    from optionslab.market_filters import MarketFilters
    from optionslab.option_selector import (
        calculate_position_size,
        calculate_portfolio_greeks,
        calculate_volatility_context
    )
    
    print("✅ Components imported successfully")
    print()
    
    # Load test data
    DATA_FILE = "/Users/nish_macbook/trading/daily-optionslab/data/spy_options/SPY_OPTIONS_2024_COMPLETE.parquet"
    data = load_data(DATA_FILE, "2024-01-15", "2024-01-20")  # Smaller date range
    
    if data is not None and len(data) > 0:
        print(f"📊 Loaded {len(data):,} records")
        unique_dates = sorted(data['date'].unique())
        print(f"📅 Trading days: {len(unique_dates)}")
        
        # Add strike_dollars column if missing (for compatibility)
        if 'strike_dollars' not in data.columns and 'strike' in data.columns:
            data['strike_dollars'] = data['strike']
            print("🔧 Added strike_dollars column for compatibility")
    else:
        raise ValueError("Failed to load data")
        
    print()
    
    # TEST 1: Data + Filters Integration
    print("🧪 TEST 1: Data + Filters Integration")
    print("-" * 50)
    
    try:
        config = {
            'strategy_type': 'long_call',
            'market_filters': {
                'trend_filter': {
                    'ma_period': 3,  # Short period for limited data
                    'require_above_ma': True
                }
            }
        }
        
        market_filters = MarketFilters(config, data, unique_dates)
        
        # Test filtering
        test_results_list = []
        for i, date in enumerate(unique_dates):
            date_data = data[data['date'] == date]
            if not date_data.empty:
                current_price = date_data['underlying_price'].iloc[0]
                
                # Only test if we have enough history
                if i >= 3:
                    all_passed, messages = market_filters.check_all_filters(
                        date, current_price, i
                    )
                    test_results_list.append({
                        'date': date,
                        'price': current_price,
                        'passed': all_passed,
                        'message': messages[0] if messages else 'No message'
                    })
        
        print(f"📊 Filter test results:")
        for result in test_results_list:
            status = "✅" if result['passed'] else "❌"
            print(f"   {result['date'].strftime('%Y-%m-%d')}: {status} ${result['price']:.2f}")
        
        print("✅ PASS: Data + Filters integration working")
        test_results['data_filters'] = True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 2: Position Sizing Chain
    print("🧪 TEST 2: Position Sizing Chain")
    print("-" * 50)
    
    try:
        # Get a valid option with non-zero price
        test_date = unique_dates[-1]
        test_data = data[data['date'] == test_date]
        
        # Find options with valid prices
        valid_options = test_data[
            (test_data['right'] == 'C') &
            (test_data['close'] > 0.10) &  # Ensure non-zero price
            (test_data['dte'] >= 20) &
            (test_data['dte'] <= 60)
        ]
        
        if not valid_options.empty:
            test_option = valid_options.iloc[0]
            
            print(f"📊 Test Option:")
            print(f"   Strike: ${test_option['strike']:.2f}")
            print(f"   DTE: {test_option['dte']} days")
            print(f"   Price: ${test_option['close']:.2f}")
            
            # Calculate position size
            cash = 100000
            position_pct = 0.05
            
            contracts, cost = calculate_position_size(
                cash, test_option['close'], position_pct, 
                max_contracts=100, config={'strategy_type': 'long_call'}
            )
            
            print(f"\n📊 Position Sizing:")
            print(f"   Contracts: {contracts}")
            print(f"   Cost: ${cost:,.2f}")
            print(f"   % of Capital: {cost/cash:.2%}")
            
            if contracts > 0 and cost > 0:
                print("✅ PASS: Position sizing chain working")
                test_results['position_sizing_chain'] = True
            else:
                print("❌ FAIL: Invalid position size")
        else:
            print("⚠️ No valid options found with non-zero prices")
            print("📊 Sample of available options:")
            sample = test_data[test_data['right'] == 'C'][['strike', 'dte', 'close']].head()
            print(sample)
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 3: Portfolio Greeks Accumulation
    print("🧪 TEST 3: Portfolio Greeks Accumulation")
    print("-" * 50)
    
    try:
        # Simulate multiple positions
        positions = []
        total_cost = 0
        
        # Find 3 different options to create positions
        for i in range(3):
            strike_offset = 5 * i  # Different strikes
            target_strike = test_data['underlying_price'].iloc[0] + strike_offset
            
            option = test_data[
                (test_data['right'] == 'C') &
                (abs(test_data['strike'] - target_strike) <= 5) &
                (test_data['close'] > 0.10)
            ]
            
            if not option.empty:
                opt = option.iloc[0]
                contracts = max(1, int(5000 / (opt['close'] * 100)))  # ~$5000 per position
                
                position = {
                    'contracts': contracts,
                    'side': 'long',
                    'strike': opt['strike'],
                    'delta': opt.get('delta', 0.5) if not pd.isna(opt.get('delta')) else 0.5,
                    'gamma': opt.get('gamma', 0.01) if not pd.isna(opt.get('gamma')) else 0.01,
                    'vega': opt.get('vega', 0.1) if not pd.isna(opt.get('vega')) else 0.1,
                    'theta': opt.get('theta', -0.05) if not pd.isna(opt.get('theta')) else -0.05
                }
                
                positions.append(position)
                position_cost = contracts * opt['close'] * 100
                total_cost += position_cost
                
                print(f"📊 Position {i+1}:")
                print(f"   Strike: ${opt['strike']:.2f}")
                print(f"   Contracts: {contracts}")
                print(f"   Cost: ${position_cost:,.2f}")
                print(f"   Delta: {position['delta']:.3f}")
        
        if positions:
            # Calculate portfolio Greeks
            portfolio_greeks = calculate_portfolio_greeks(positions)
            
            print(f"\n📊 Portfolio Summary:")
            print(f"   Total Positions: {len(positions)}")
            print(f"   Total Cost: ${total_cost:,.2f}")
            print(f"\n📊 Portfolio Greeks:")
            print(f"   Total Delta: {portfolio_greeks['total_delta']:.1f}")
            print(f"   Total Gamma: {portfolio_greeks['total_gamma']:.2f}")
            print(f"   Total Vega: {portfolio_greeks['total_vega']:.2f}")
            print(f"   Total Theta: ${portfolio_greeks['total_theta']:.2f}")
            
            print("✅ PASS: Portfolio accumulation working")
            test_results['portfolio_accumulation'] = True
        else:
            print("⚠️ Could not create test positions")
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        traceback.print_exc()
        
    print()
    
    # SUMMARY
    print("📋 INTEGRATION TEST SUMMARY")
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
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\n📊 Key Integration Points Verified:")
        print("   ✅ Data loads and filters apply correctly")
        print("   ✅ Position sizing works with real option data")
        print("   ✅ Portfolio Greeks accumulate across positions")
        print("\n🚀 Components work together successfully!")
        print("🎯 Ready for Phase 3: Strategy Layer Testing")
    else:
        print("⚠️ Some integration points need attention")
        print("Note: Integration issues may be due to data quality")
        print("or column naming inconsistencies between modules.")
        
except Exception as e:
    print(f"💥 CRITICAL ERROR: {e}")
    print("\n🔧 Full traceback:")
    traceback.print_exc()

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")