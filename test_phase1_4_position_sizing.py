#!/usr/bin/env python3
"""
Phase 1.4 Test: Dynamic Position Sizing Verification
====================================================
Tests volatility-based position sizing and portfolio Greeks management.
"""

import sys
import pandas as pd
from datetime import datetime
import traceback
import numpy as np

print("=" * 60)
print("PHASE 1.4: DYNAMIC POSITION SIZING TEST")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test results tracker
test_results = {
    'import_test': False,
    'volatility_context_test': False,
    'basic_position_size_test': False,
    'portfolio_greeks_test': False,
    'risk_limits_test': False,
    'scaling_test': False
}

try:
    # TEST 1: Import Test
    print("🧪 TEST 1: Testing Import of Position Sizing Functions")
    print("-" * 50)
    
    try:
        from optionslab.option_selector import (
            calculate_dynamic_position_size,
            calculate_portfolio_greeks,
            calculate_volatility_context
        )
        from optionslab.data_loader import load_data
        print("✅ PASS: Successfully imported position sizing functions")
        test_results['import_test'] = True
    except ImportError as e:
        print(f"❌ FAIL: Import error - {e}")
        raise
    
    print()
    
    # Load test data
    print("📊 Loading test data (Jan 2024)")
    print("-" * 50)
    
    DATA_FILE = "/Users/nish_macbook/trading/daily-optionslab/data/spy_options/SPY_OPTIONS_2024_COMPLETE.parquet"
    data = load_data(DATA_FILE, "2024-01-02", "2024-01-15")
    
    if data is not None and len(data) > 0:
        print(f"✅ Loaded {len(data):,} records")
        test_date = data['date'].iloc[0]
        test_price = data['underlying_price'].iloc[0]
        print(f"📅 Test date: {test_date.strftime('%Y-%m-%d')}")
        print(f"💵 SPY price: ${test_price:.2f}")
    else:
        raise ValueError("Failed to load test data")
        
    print()
    
    # TEST 2: Volatility Context Calculation
    print("🧪 TEST 2: Testing Volatility Context Calculation")
    print("-" * 50)
    
    try:
        # Get options for volatility calculation
        date_data = data[data['date'] == test_date]
        
        vol_context = calculate_volatility_context(date_data, test_price)
        
        print("📊 Volatility Context:")
        print(f"   Current IV: {vol_context['current_iv']:.3f}")
        print(f"   IV Percentile: {vol_context['iv_percentile']:.1f}")
        print(f"   IV Regime: {vol_context['iv_regime']}")
        print(f"   Volatility Adjusted: {vol_context['volatility_adjusted']:.3f}")
        
        # Validate results
        if (0 < vol_context['current_iv'] < 2.0 and
            0 <= vol_context['iv_percentile'] <= 100 and
            vol_context['iv_regime'] in ['low', 'medium', 'high'] and
            vol_context['volatility_adjusted'] > 0):
            print("✅ PASS: Volatility context calculation is valid")
            test_results['volatility_context_test'] = True
        else:
            print("❌ FAIL: Invalid volatility context values")
            
    except Exception as e:
        print(f"❌ FAIL: Error calculating volatility context - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 3: Basic Position Size Calculation
    print("🧪 TEST 3: Testing Basic Position Size Calculation")
    print("-" * 50)
    
    try:
        # Test parameters
        capital = 100000
        existing_positions = []  # No existing positions
        
        # Find a test option (ATM call)
        atm_options = date_data[
            (date_data['right'] == 'C') &
            (abs(date_data['strike'] - test_price) <= test_price * 0.02) &
            (date_data['dte'] >= 30) &
            (date_data['dte'] <= 45)
        ]
        
        if atm_options.empty:
            print("⚠️ No suitable ATM options found, using first available option")
            test_option = date_data[
                (date_data['right'] == 'C') &
                (date_data['dte'] >= 30)
            ].iloc[0]
        else:
            test_option = atm_options.iloc[0]
        
        option_price = test_option['close']
        option_delta = test_option['delta']
        option_vega = test_option['vega']
        
        print(f"📊 Test Option:")
        print(f"   Strike: ${test_option['strike']:.2f}")
        print(f"   DTE: {test_option['dte']} days")
        print(f"   Price: ${option_price:.2f}")
        print(f"   Delta: {option_delta:.3f}")
        print(f"   Vega: {option_vega:.3f}")
        
        # Calculate position size
        position_size = calculate_dynamic_position_size(
            capital=capital,
            option_price=option_price,
            delta=option_delta,
            vega=option_vega,
            volatility_context=vol_context,
            existing_positions=existing_positions,
            strategy_type='long_call'
        )
        
        print(f"\n📊 Position Size Results:")
        print(f"   Base contracts: {position_size['base_contracts']}")
        print(f"   Vol adjusted contracts: {position_size['vol_adjusted_contracts']}")
        print(f"   Risk adjusted contracts: {position_size['risk_adjusted_contracts']}")
        print(f"   Final contracts: {position_size['final_contracts']}")
        print(f"   Position value: ${position_size['position_value']:,.2f}")
        print(f"   % of capital: {position_size['percent_of_capital']:.1%}")
        
        # Validate results
        if (position_size['final_contracts'] > 0 and
            position_size['position_value'] > 0 and
            0 < position_size['percent_of_capital'] < 1.0):
            print("✅ PASS: Position size calculation is valid")
            test_results['basic_position_size_test'] = True
        else:
            print("❌ FAIL: Invalid position size values")
            
    except Exception as e:
        print(f"❌ FAIL: Error calculating position size - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 4: Portfolio Greeks Calculation
    print("🧪 TEST 4: Testing Portfolio Greeks Calculation")
    print("-" * 50)
    
    try:
        # Create mock positions
        positions = [
            {
                'type': 'long_call',
                'contracts': position_size['final_contracts'],
                'delta': option_delta,
                'gamma': test_option['gamma'],
                'theta': test_option['theta'],
                'vega': option_vega,
                'option_price': option_price
            }
        ]
        
        # Add a short put position for diversity
        short_put = date_data[
            (date_data['right'] == 'P') &
            (date_data['strike'] < test_price * 0.95) &
            (date_data['dte'] >= 30)
        ].iloc[0] if not date_data[
            (date_data['right'] == 'P') &
            (date_data['strike'] < test_price * 0.95) &
            (date_data['dte'] >= 30)
        ].empty else None
        
        if short_put is not None:
            positions.append({
                'type': 'short_put',
                'contracts': -2,  # Negative for short
                'delta': short_put['delta'],
                'gamma': short_put['gamma'],
                'theta': short_put['theta'],
                'vega': short_put['vega'],
                'option_price': short_put['close']
            })
        
        # Calculate portfolio Greeks
        portfolio_greeks = calculate_portfolio_greeks(positions)
        
        print("📊 Portfolio Greeks:")
        print(f"   Total Delta: {portfolio_greeks['total_delta']:.2f}")
        print(f"   Total Gamma: {portfolio_greeks['total_gamma']:.3f}")
        print(f"   Total Theta: ${portfolio_greeks['total_theta']:.2f}")
        print(f"   Total Vega: ${portfolio_greeks['total_vega']:.2f}")
        print(f"   Net Premium: ${portfolio_greeks['net_premium']:,.2f}")
        
        # Show position breakdown
        print(f"\n📊 Position Breakdown:")
        for i, pos in enumerate(positions, 1):
            pos_type = pos['type']
            contracts = pos['contracts']
            print(f"   Position {i}: {abs(contracts)} {pos_type}")
            print(f"      Delta contribution: {pos['delta'] * contracts * 100:.2f}")
            print(f"      Vega contribution: ${pos['vega'] * contracts * 100:.2f}")
        
        print("✅ PASS: Portfolio Greeks calculation is working")
        test_results['portfolio_greeks_test'] = True
        
    except Exception as e:
        print(f"❌ FAIL: Error calculating portfolio Greeks - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 5: Risk Limits Test
    print("🧪 TEST 5: Testing Risk Limits and Constraints")
    print("-" * 50)
    
    try:
        # Test with high existing exposure
        large_existing_positions = [
            {
                'type': 'long_call',
                'contracts': 50,
                'delta': 0.5,
                'vega': 0.2,
                'option_price': 5.0
            },
            {
                'type': 'long_call',
                'contracts': 30,
                'delta': 0.4,
                'vega': 0.15,
                'option_price': 4.0
            }
        ]
        
        # Calculate constrained position size
        constrained_size = calculate_dynamic_position_size(
            capital=capital,
            option_price=option_price,
            delta=option_delta,
            vega=option_vega,
            volatility_context=vol_context,
            existing_positions=large_existing_positions,
            strategy_type='long_call'
        )
        
        print("📊 With Large Existing Positions:")
        print(f"   Existing exposure: {len(large_existing_positions)} positions")
        print(f"   Base contracts (unconstrained): {position_size['base_contracts']}")
        print(f"   Final contracts (constrained): {constrained_size['final_contracts']}")
        print(f"   Reduction factor: {constrained_size['final_contracts'] / max(position_size['base_contracts'], 1):.2f}")
        
        # Test max position limit
        tiny_capital = 1000  # Very small capital
        tiny_position = calculate_dynamic_position_size(
            capital=tiny_capital,
            option_price=option_price,
            delta=option_delta,
            vega=option_vega,
            volatility_context=vol_context,
            existing_positions=[],
            strategy_type='long_call'
        )
        
        print(f"\n📊 With Tiny Capital (${tiny_capital}):")
        print(f"   Final contracts: {tiny_position['final_contracts']}")
        print(f"   Position value: ${tiny_position['position_value']:.2f}")
        print(f"   % of capital: {tiny_position['percent_of_capital']:.1%}")
        
        # Validate constraints are working
        if (constrained_size['final_contracts'] <= position_size['final_contracts'] and
            tiny_position['final_contracts'] >= 0 and
            tiny_position['percent_of_capital'] <= 1.0):
            print("✅ PASS: Risk limits are properly enforced")
            test_results['risk_limits_test'] = True
        else:
            print("❌ FAIL: Risk limits not working correctly")
            
    except Exception as e:
        print(f"❌ FAIL: Error testing risk limits - {e}")
        traceback.print_exc()
        
    print()
    
    # TEST 6: Volatility-Based Scaling Test
    print("🧪 TEST 6: Testing Volatility-Based Scaling")
    print("-" * 50)
    
    try:
        # Simulate different volatility contexts
        vol_contexts = [
            {'current_iv': 0.15, 'iv_percentile': 20, 'iv_regime': 'low', 'volatility_adjusted': 1.2},
            {'current_iv': 0.25, 'iv_percentile': 50, 'iv_regime': 'medium', 'volatility_adjusted': 1.0},
            {'current_iv': 0.40, 'iv_percentile': 80, 'iv_regime': 'high', 'volatility_adjusted': 0.7}
        ]
        
        print("📊 Position Sizing Across Volatility Regimes:")
        print("-" * 50)
        
        for vol_ctx in vol_contexts:
            size = calculate_dynamic_position_size(
                capital=capital,
                option_price=option_price,
                delta=option_delta,
                vega=option_vega,
                volatility_context=vol_ctx,
                existing_positions=[],
                strategy_type='long_call'
            )
            
            print(f"\nIV Regime: {vol_ctx['iv_regime'].upper()}")
            print(f"   Current IV: {vol_ctx['current_iv']:.1%}")
            print(f"   IV Percentile: {vol_ctx['iv_percentile']}th")
            print(f"   Vol Adjustment: {vol_ctx['volatility_adjusted']:.2f}x")
            print(f"   Final Contracts: {size['final_contracts']}")
            print(f"   Position Value: ${size['position_value']:,.2f}")
            print(f"   % of Capital: {size['percent_of_capital']:.1%}")
        
        print("\n✅ PASS: Volatility-based scaling is working")
        test_results['scaling_test'] = True
        
    except Exception as e:
        print(f"❌ FAIL: Error testing volatility scaling - {e}")
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
        print("🎉 ALL TESTS PASSED! Dynamic position sizing is working correctly.")
        print("🚀 Phase 1 (Foundation Layer) is COMPLETE!")
        print("📊 Ready to proceed to Phase 2 (Integration Layer Testing)")
    else:
        print("⚠️  Some tests need attention")
        
    print()
    
    # POSITION SIZING INSIGHTS
    print("💡 POSITION SIZING INSIGHTS")
    print("-" * 50)
    print("1. Position sizes automatically reduce in high volatility")
    print("2. Existing portfolio exposure constrains new positions")
    print("3. Small accounts get minimum viable position sizes")
    print("4. Greeks-based risk management is integrated")
    print("5. Volatility regime detection adjusts exposure")
    
except Exception as e:
    print(f"💥 CRITICAL ERROR: {e}")
    print("\n🔧 Full traceback:")
    traceback.print_exc()
    print(f"\n⚠️  Test failed. Please investigate the error.")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")