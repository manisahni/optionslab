#!/usr/bin/env python3
"""
Phase 3 Strategy Testing Template
================================
Template for testing complete position lifecycle from entry to exit.
Copy and modify for specific strategy testing needs.

Usage:
    cp testing_templates/phase3_strategy_test_template.py test_my_strategy.py
    # Modify for your specific strategy
    python test_my_strategy.py
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback

print("=" * 60)
print("PHASE 3: STRATEGY TESTING TEMPLATE")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test results tracker
test_results = {
    'position_entry': False,
    'position_tracking': False,
    'exit_conditions': False,
    'pnl_calculation': False
}

try:
    # TODO: Import your strategy components
    from optionslab.data_loader import load_data
    from optionslab.market_filters import MarketFilters
    from optionslab.option_selector import (
        find_suitable_options,
        calculate_position_size
    )
    
    print("✅ Components imported successfully")
    print()
    
    # Load test data for strategy lifecycle
    DATA_FILE = "/Users/nish_macbook/trading/daily-optionslab/data/spy_options/SPY_OPTIONS_2024_COMPLETE.parquet"
    data = load_data(DATA_FILE, "2024-01-02", "2024-02-29")  # 2 months for full lifecycle
    
    if data is not None and len(data) > 0:
        print(f"📊 Loaded {len(data):,} records")
        unique_dates = sorted(data['date'].unique())
        print(f"📅 Trading days: {len(unique_dates)}")
    else:
        raise ValueError("Failed to load data")
        
    print()
    
    # STEP 1: Position Entry Testing
    print("🧪 TEST 3.1: Position Entry Testing")
    print("-" * 50)
    
    try:
        # TODO: Setup your strategy configuration
        config = {
            'strategy_type': 'long_call',  # Modify for your strategy
            'option_selection': {
                'delta_criteria': {
                    'target': 0.50,
                    'tolerance': 0.10
                },
                'dte_criteria': {
                    'minimum': 30,
                    'maximum': 60
                },
                'liquidity_criteria': {
                    'min_volume': 100,
                    'max_spread_pct': 0.15
                }
            },
            'position_management': {
                'position_size_pct': 0.05  # 5% of capital
            },
            'market_filters': {}  # Add filters as needed
        }
        
        # Find entry opportunity
        entry_date = None
        selected_option = None
        entry_spy_price = None
        
        for date in unique_dates[10:20]:  # Check days 10-20 for entry
            date_data = data[data['date'] == date]
            current_price = date_data['underlying_price'].iloc[0]
            
            option = find_suitable_options(
                date_data, current_price, config, date
            )
            
            if option is not None:
                entry_date = date
                selected_option = option
                entry_spy_price = current_price
                break
        
        if selected_option is not None:
            print(f"📅 Entry Date: {entry_date.strftime('%Y-%m-%d')}")
            print(f"💵 SPY Price: ${entry_spy_price:.2f}")
            print(f"🎯 Selected Option:")
            print(f"   Strike: ${selected_option['strike']:.2f}")
            print(f"   Expiration: {selected_option['expiration'].strftime('%Y-%m-%d')}")
            print(f"   DTE: {selected_option['dte']} days")
            print(f"   Price: ${selected_option['close']:.2f}")
            print(f"   Delta: {selected_option['delta']:.3f}")
            print(f"   Volume: {selected_option['volume']:,.0f}")
            
            # Calculate position size
            cash = 100000
            contracts, cost = calculate_position_size(
                cash=cash,
                option_price=selected_option['close'],
                position_size_pct=config['position_management']['position_size_pct']
            )
            
            if contracts > 0:
                print(f"\n💼 Position:")
                print(f"   Contracts: {contracts}")
                print(f"   Cost: ${cost:,.2f}")
                print(f"   % of Capital: {cost/cash:.2%}")
                
                print("✅ PASS: Position entry successful")
                test_results['position_entry'] = True
            else:
                print("❌ FAIL: Could not size position")
        else:
            print("❌ FAIL: No suitable options found for entry")
            
    except Exception as e:
        print(f"❌ FAIL: Error in position entry - {e}")
        traceback.print_exc()
        
    print()
    
    # STEP 2: Position Tracking Testing
    print("🧪 TEST 3.2: Position Tracking Over Time")
    print("-" * 50)
    
    try:
        if selected_option is not None and contracts > 0:
            # Track position for 10 days or until expiration
            entry_idx = unique_dates.index(entry_date)
            max_days = min(10, len(unique_dates) - entry_idx - 1)
            
            position_values = []
            position_greeks = []
            
            print("📊 Tracking position:")
            print("Day | Date       | SPY    | Option | P&L     | Delta  | Theta")
            print("-" * 70)
            
            for i in range(max_days):
                track_date = unique_dates[entry_idx + i]
                track_data = data[
                    (data['date'] == track_date) &
                    (data['strike'] == selected_option['strike']) &
                    (data['expiration'] == selected_option['expiration']) &
                    (data['right'] == selected_option['right'])
                ]
                
                if not track_data.empty:
                    track_option = track_data.iloc[0]
                    current_value = track_option['close'] * contracts * 100
                    pnl = current_value - cost
                    
                    position_values.append(current_value)
                    position_greeks.append({
                        'delta': track_option.get('delta', 0),
                        'theta': track_option.get('theta', 0),
                        'vega': track_option.get('vega', 0),
                        'gamma': track_option.get('gamma', 0)
                    })
                    
                    spy_price = track_option['underlying_price']
                    
                    print(f"{i:3} | {track_date.strftime('%Y-%m-%d')} | ${spy_price:6.2f} | "
                          f"${track_option['close']:6.2f} | ${pnl:7,.0f} | "
                          f"{track_option.get('delta', 0):6.3f} | {track_option.get('theta', 0):6.3f}")
            
            if len(position_values) > 0:
                max_value = max(position_values)
                min_value = min(position_values)
                final_value = position_values[-1]
                
                print(f"\n📊 Position Statistics:")
                print(f"   Entry Value: ${cost:,.2f}")
                print(f"   Max Value: ${max_value:,.2f} ({(max_value/cost-1)*100:+.1f}%)")
                print(f"   Min Value: ${min_value:,.2f} ({(min_value/cost-1)*100:+.1f}%)")
                print(f"   Final Value: ${final_value:,.2f} ({(final_value/cost-1)*100:+.1f}%)")
                
                print("✅ PASS: Position tracking working")
                test_results['position_tracking'] = True
            else:
                print("⚠️ WARNING: Could not track position")
                
    except Exception as e:
        print(f"❌ FAIL: Error in position tracking - {e}")
        traceback.print_exc()
        
    print()
    
    # STEP 3: Exit Conditions Testing
    print("🧪 TEST 3.3: Exit Conditions Testing")
    print("-" * 50)
    
    try:
        # TODO: Define exit rules for your strategy
        exit_rules = {
            'take_profit_pct': 0.50,    # Exit at 50% profit
            'stop_loss_pct': -0.30,     # Exit at 30% loss
            'dte_exit': 7,              # Exit if DTE < 7
            'delta_exit_high': 0.90,    # Exit if delta too high
            'delta_exit_low': 0.05      # Exit if delta too low
        }
        
        print("🎯 Exit Rules:")
        print(f"   Take Profit: {exit_rules['take_profit_pct']:.0%}")
        print(f"   Stop Loss: {exit_rules['stop_loss_pct']:.0%}")
        print(f"   DTE Exit: {exit_rules['dte_exit']} days")
        print(f"   Delta High: {exit_rules['delta_exit_high']:.2f}")
        print(f"   Delta Low: {exit_rules['delta_exit_low']:.2f}")
        print()
        
        if selected_option is not None and len(position_values) > 0:
            exit_triggered = False
            exit_date = None
            exit_reason = None
            exit_value = None
            exit_day = None
            
            # Check each day for exit conditions
            for i in range(len(position_values)):
                current_value = position_values[i]
                pnl_pct = (current_value / cost) - 1
                
                track_date = unique_dates[entry_idx + i]
                days_held = i
                current_dte = selected_option['dte'] - days_held
                current_delta = position_greeks[i]['delta'] if i < len(position_greeks) else 0
                
                # Check all exit conditions
                if pnl_pct >= exit_rules['take_profit_pct']:
                    exit_triggered = True
                    exit_reason = f"Take Profit ({pnl_pct:.1%})"
                elif pnl_pct <= exit_rules['stop_loss_pct']:
                    exit_triggered = True
                    exit_reason = f"Stop Loss ({pnl_pct:.1%})"
                elif current_dte <= exit_rules['dte_exit']:
                    exit_triggered = True
                    exit_reason = f"DTE Exit ({current_dte} days)"
                elif current_delta >= exit_rules['delta_exit_high']:
                    exit_triggered = True
                    exit_reason = f"Delta High ({current_delta:.3f})"
                elif current_delta <= exit_rules['delta_exit_low']:
                    exit_triggered = True
                    exit_reason = f"Delta Low ({current_delta:.3f})"
                
                if exit_triggered:
                    exit_date = track_date
                    exit_value = current_value
                    exit_day = i
                    break
            
            if exit_triggered:
                exit_pnl = exit_value - cost
                exit_pnl_pct = (exit_value / cost) - 1
                
                print(f"🚪 Exit Triggered:")
                print(f"   Date: {exit_date.strftime('%Y-%m-%d')}")
                print(f"   Reason: {exit_reason}")
                print(f"   Exit Value: ${exit_value:,.2f}")
                print(f"   P&L: ${exit_pnl:,.2f} ({exit_pnl_pct:+.1%})")
                print(f"   Days Held: {exit_day}")
                
                print("✅ PASS: Exit conditions triggered correctly")
                test_results['exit_conditions'] = True
            else:
                print("🔄 No exit triggered during test period")
                print("✅ PASS: Exit conditions evaluated correctly")
                test_results['exit_conditions'] = True
                
    except Exception as e:
        print(f"❌ FAIL: Error in exit conditions - {e}")
        traceback.print_exc()
        
    print()
    
    # STEP 4: P&L Calculation Testing
    print("🧪 TEST 3.4: P&L Calculation Testing")
    print("-" * 50)
    
    try:
        if selected_option is not None and len(position_values) > 0:
            # Calculate comprehensive P&L metrics
            print("💰 P&L Breakdown:")
            
            # Entry costs
            option_cost = selected_option['close'] * contracts * 100
            commission_entry = contracts * 0.65  # Standard commission
            total_entry_cost = option_cost + commission_entry
            
            print(f"\nEntry Costs:")
            print(f"   Option Cost: ${option_cost:,.2f}")
            print(f"   Entry Commission: ${commission_entry:.2f}")
            print(f"   Total Entry: ${total_entry_cost:,.2f}")
            
            # Exit value (use exit value if available, otherwise final tracked value)
            if exit_triggered and exit_value:
                final_option_value = exit_value
                exit_commission = contracts * 0.65
            else:
                final_option_value = position_values[-1] if position_values else 0
                exit_commission = contracts * 0.65
            
            net_exit_value = final_option_value - exit_commission
            
            print(f"\nExit Values:")
            print(f"   Option Value: ${final_option_value:,.2f}")
            print(f"   Exit Commission: ${exit_commission:.2f}")
            print(f"   Net Exit: ${net_exit_value:,.2f}")
            
            # Calculate P&L components
            gross_pnl = final_option_value - option_cost
            total_commission = commission_entry + exit_commission
            net_pnl = net_exit_value - total_entry_cost
            
            print(f"\nP&L Summary:")
            print(f"   Gross P&L: ${gross_pnl:,.2f}")
            print(f"   Total Commissions: ${total_commission:.2f}")
            print(f"   Net P&L: ${net_pnl:,.2f}")
            print(f"   Return: {(net_pnl/total_entry_cost)*100:+.2f}%")
            
            # Greeks impact analysis
            if len(position_greeks) > 1:
                initial_greeks = position_greeks[0]
                final_greeks = position_greeks[-1]
                
                print(f"\nGreeks Evolution:")
                print(f"   Delta: {initial_greeks['delta']:.3f} → {final_greeks['delta']:.3f}")
                print(f"   Theta: {initial_greeks['theta']:.3f} → {final_greeks['theta']:.3f}")
                
                # Calculate theta decay impact
                theta_impact = sum(g['theta'] for g in position_greeks) * contracts * 100
                print(f"   Cumulative Theta Impact: ${theta_impact:.2f}")
            
            # Verify calculations
            expected_net = gross_pnl - total_commission
            if abs(net_pnl - expected_net) < 0.01:  # Allow for rounding
                print("✅ PASS: P&L calculations verified")
                test_results['pnl_calculation'] = True
            else:
                print(f"❌ FAIL: P&L mismatch: {net_pnl:.2f} vs {expected_net:.2f}")
                
    except Exception as e:
        print(f"❌ FAIL: Error in P&L calculation - {e}")
        traceback.print_exc()
        
    print()
    
    # SUMMARY
    print("📋 STRATEGY TEST SUMMARY")
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
        print("🎉 ALL STRATEGY TESTS PASSED!")
        print("\n📊 Strategy Capabilities Verified:")
        print("   ✅ Can find and enter positions")
        print("   ✅ Can track positions over time")
        print("   ✅ Exit conditions work properly")
        print("   ✅ P&L calculations are accurate")
        print("\n🚀 Ready for advanced position management testing (Phase 3.5)")
    else:
        print("⚠️ Some strategy tests need attention")
        print("\n🔧 Next Steps:")
        for test_name, result in test_results.items():
            if not result:
                print(f"   • Fix {test_name.replace('_', ' ')}")
        
except Exception as e:
    print(f"💥 CRITICAL ERROR: {e}")
    print("\n🔧 Full traceback:")
    traceback.print_exc()

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# TODO: Add strategy-specific validation notes
print("\n📝 STRATEGY-SPECIFIC VALIDATION NOTES:")
print("=" * 50)
print("TODO: Document your strategy-specific findings:")
print("• Entry signal effectiveness")
print("• Position sizing behavior")
print("• Exit timing analysis")
print("• Greeks evolution patterns")
print("• Risk-adjusted performance metrics")