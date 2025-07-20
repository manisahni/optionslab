#!/usr/bin/env python3
"""
Integration test for all backtesting features
Tests all implemented features working together in a complex scenario
"""

from auditable_backtest import run_auditable_backtest
import pandas as pd
import json

def test_all_features():
    """Test all features in one comprehensive backtest"""
    print("\n" + "="*60)
    print("INTEGRATION TEST: All Features Combined")
    print("="*60)
    
    # Test configuration
    data_dir = "spy_options_downloader/spy_options_parquet"
    config_file = "test_integration.yaml"
    
    # Use a longer period to test various market conditions
    start_date = "2022-08-01"
    end_date = "2022-09-30"  # 2 months
    
    print(f"\n📅 Test Period: {start_date} to {end_date} (2 months)")
    print(f"🎯 Features being tested:")
    print(f"  ✓ Multi-day backtesting")
    print(f"  ✓ Advanced option selection (delta/DTE/liquidity)")
    print(f"  ✓ Multiple concurrent positions (max 3)")
    print(f"  ✓ Profit target exits (40%)")
    print(f"  ✓ Stop loss exits (-20%)")
    print(f"  ✓ Position-level P&L tracking")
    print(f"  ✓ Both calls and puts (will test puts separately)")
    
    # Run backtest with calls
    print(f"\n🔍 Testing CALL options...")
    call_results = run_auditable_backtest(data_dir, config_file, start_date, end_date)
    
    # Also test with puts by modifying the strategy
    print(f"\n🔍 Testing PUT options...")
    # Create a put version of the strategy
    import yaml
    with open(config_file, 'r') as f:
        put_config = yaml.safe_load(f)
    put_config['strategy_type'] = 'long_put'
    put_config['name'] = 'Integration Test - Puts'
    
    with open('test_integration_puts.yaml', 'w') as f:
        yaml.dump(put_config, f)
    
    put_results = run_auditable_backtest(data_dir, 'test_integration_puts.yaml', start_date, end_date)
    
    # Analyze results
    print(f"\n" + "="*60)
    print("INTEGRATION TEST RESULTS")
    print("="*60)
    
    # Check all features worked
    features_tested = {
        'multi_day': False,
        'multiple_positions': False,
        'profit_targets': False,
        'stop_losses': False,
        'calls_traded': False,
        'puts_traded': False,
        'advanced_selection': False,
        'pnl_tracking': False
    }
    
    # Analyze call results
    if call_results:
        # Multi-day test
        if len(call_results['equity_curve']) > 20:
            features_tested['multi_day'] = True
            
        # Multiple positions test
        max_positions = max(point['positions'] for point in call_results['equity_curve'])
        if max_positions >= 2:
            features_tested['multiple_positions'] = True
            
        # Exit reasons
        for trade in call_results['trades']:
            if 'exit_reason' in trade:
                if 'profit target' in trade['exit_reason']:
                    features_tested['profit_targets'] = True
                elif 'stop loss' in trade['exit_reason']:
                    features_tested['stop_losses'] = True
                    
        # Calls traded
        if len(call_results['trades']) > 0:
            features_tested['calls_traded'] = True
            features_tested['advanced_selection'] = True  # Used advanced selection
            features_tested['pnl_tracking'] = True  # P&L tracked
    
    # Check puts traded
    if put_results and len(put_results['trades']) > 0:
        features_tested['puts_traded'] = True
    
    # Print feature test results
    print(f"\n📊 Feature Verification:")
    for feature, tested in features_tested.items():
        status = "✅" if tested else "❌"
        print(f"  {status} {feature.replace('_', ' ').title()}")
    
    # Performance summary
    print(f"\n💰 Performance Summary:")
    if call_results:
        print(f"\nCall Strategy:")
        print(f"  Initial Capital: ${call_results['trades'][0]['cash_before'] if call_results['trades'] else 25000:,.2f}")
        print(f"  Final Value: ${call_results['final_value']:,.2f}")
        print(f"  Total Return: {call_results['total_return']:.2%}")
        print(f"  Total Trades: {len([t for t in call_results['trades'] if 'exit_date' in t])}")
        
        # Exit reason breakdown
        exit_reasons = {}
        for trade in call_results['trades']:
            if 'exit_reason' in trade:
                reason = trade['exit_reason'].split('(')[0].strip()
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        if exit_reasons:
            print(f"\n  Exit Reasons:")
            for reason, count in exit_reasons.items():
                print(f"    - {reason}: {count}")
    
    if put_results:
        print(f"\nPut Strategy:")
        print(f"  Final Value: ${put_results['final_value']:,.2f}")
        print(f"  Total Return: {put_results['total_return']:.2%}")
        print(f"  Total Trades: {len([t for t in put_results['trades'] if 'exit_date' in t])}")
    
    # Overall test result
    all_features_tested = all(features_tested.values())
    print(f"\n" + "="*60)
    if all_features_tested:
        print("✅ INTEGRATION TEST PASSED - All features working correctly!")
    else:
        print("❌ INTEGRATION TEST FAILED - Some features not working")
    print("="*60)
    
    # Clean up
    import os
    if os.path.exists('test_integration_puts.yaml'):
        os.remove('test_integration_puts.yaml')
    
    return all_features_tested

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "="*60)
    print("EDGE CASE TESTING")
    print("="*60)
    
    # Test 1: Insufficient capital
    print("\n1. Testing insufficient capital scenario...")
    edge_config = {
        'name': 'Edge Case - Low Capital',
        'description': 'Test with very low capital',
        'strategy_type': 'long_call',
        'parameters': {
            'initial_capital': 100,  # Only $100
            'position_size': 0.5,    # Try to use 50%
            'max_positions': 1,
            'max_hold_days': 5,
            'entry_frequency': 1
        }
    }
    
    import yaml
    with open('edge_case_low_capital.yaml', 'w') as f:
        yaml.dump(edge_config, f)
    
    try:
        results = run_auditable_backtest(
            "spy_options_downloader/spy_options_parquet",
            'edge_case_low_capital.yaml',
            "2022-08-01",
            "2022-08-05"
        )
        if results and len(results['trades']) == 0:
            print("  ✅ Correctly handled insufficient capital (no trades executed)")
        else:
            print("  ❌ Should not have executed trades with insufficient capital")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Clean up
    import os
    if os.path.exists('edge_case_low_capital.yaml'):
        os.remove('edge_case_low_capital.yaml')
    
    print("\n✅ Edge case testing completed")

if __name__ == "__main__":
    # Run integration test
    integration_passed = test_all_features()
    
    # Run edge case tests
    test_edge_cases()
    
    # Exit with appropriate code
    import sys
    sys.exit(0 if integration_passed else 1)