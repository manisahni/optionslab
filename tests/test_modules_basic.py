#!/usr/bin/env python3
"""
Basic module testing without pytest
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optionslab.backtest_engine import run_auditable_backtest
from optionslab.data_loader import load_data, load_strategy_config
from optionslab.option_selector import find_suitable_options, calculate_position_size
from optionslab.backtest_metrics import calculate_compliance_scorecard, calculate_performance_metrics
from optionslab.market_filters import MarketFilters
from optionslab.greek_tracker import GreekTracker, GreekSnapshot
from optionslab.trade_recorder import TradeRecorder
from optionslab.exit_conditions import ExitConditions


def test_data_loader():
    """Test data loader functionality"""
    print("\n📊 Testing Data Loader")
    print("-" * 40)
    
    # Test config loading
    config = load_strategy_config("simple_test_strategy.yaml")
    print(f"✅ Loaded config: {config['name']}")
    
    # Print actual structure
    print("\nConfig structure:")
    print(f"  - name: {config.get('name', 'N/A')}")
    print(f"  - strategy_type: {config.get('strategy_type', 'N/A')}")
    if 'strategy' in config:
        print(f"  - strategy: {list(config['strategy'].keys())}")
    else:
        print("  - strategy: NOT FOUND")
    
    return True


def test_option_selector():
    """Test option selector"""
    print("\n🎯 Testing Option Selector")
    print("-" * 40)
    
    # Test position sizing
    contracts = calculate_position_size(10000, 5.50, 0.05)
    print(f"✅ Position sizing: {contracts} contracts")
    
    # Test with limit
    contracts = calculate_position_size(10000, 5.50, 0.05, max_contracts=5)
    print(f"✅ With limit: {contracts} contracts (max 5)")
    
    return True


def test_greek_tracker():
    """Test Greek tracker"""
    print("\n🏛️ Testing Greek Tracker")
    print("-" * 40)
    
    # Create snapshot
    snapshot = GreekSnapshot(
        delta=0.5, gamma=0.02, theta=-0.05, vega=0.15,
        iv=0.25, underlying_price=450.0, option_price=5.50, dte=45
    )
    
    # Create tracker
    tracker = GreekTracker(entry_greeks=snapshot)
    print(f"✅ Created Greek tracker")
    print(f"   Entry delta: {tracker.entry_greeks.delta}")
    print(f"   Entry price: ${tracker.entry_greeks.option_price}")
    
    return True


def test_compliance_scorecard():
    """Test compliance scorecard"""
    print("\n📈 Testing Compliance Scorecard")
    print("-" * 40)
    
    trades = [
        {
            'entry_delta': 0.45,
            'entry_dte': 45,
            'delta_compliant': True,
            'dte_compliant': True,
            'exit_reason': 'profit_target'
        }
    ]
    
    scorecard = calculate_compliance_scorecard(trades)
    print(f"✅ Scorecard calculated")
    print(f"   Overall: {scorecard['overall_score']:.1%}")
    print(f"   Delta: {scorecard['delta_compliance']:.1%}")
    print(f"   DTE: {scorecard['dte_compliance']:.1%}")
    
    return True


def test_performance_metrics():
    """Test performance metrics"""
    print("\n💰 Testing Performance Metrics")
    print("-" * 40)
    
    equity_curve = [
        {'date': '2022-01-01', 'equity': 10000},
        {'date': '2022-01-02', 'equity': 10100}
    ]
    
    trades = [
        {'pnl': 100, 'return_pct': 0.01}
    ]
    
    metrics = calculate_performance_metrics(equity_curve, trades, 10000)
    print(f"✅ Metrics calculated")
    print(f"   Total return: {metrics['total_return']:.2%}")
    print(f"   Win rate: {metrics['win_rate']:.1%}")
    
    return True


def main():
    """Run all tests"""
    print("🧪 Running Basic Module Tests")
    print("=" * 60)
    
    tests = [
        ("Data Loader", test_data_loader),
        ("Option Selector", test_option_selector),
        ("Greek Tracker", test_greek_tracker),
        ("Compliance Scorecard", test_compliance_scorecard),
        ("Performance Metrics", test_performance_metrics)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())