#!/usr/bin/env python3
"""
Working tests for the OptionsLab modules without pytest
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optionslab.option_selector import find_suitable_options, calculate_position_size
from optionslab.greek_tracker import GreekTracker, GreekSnapshot
from optionslab.backtest_metrics import calculate_compliance_scorecard, calculate_performance_metrics
from optionslab.data_loader import load_strategy_config
from optionslab.trade_recorder import TradeRecorder
from optionslab.exit_conditions import ExitConditions
from optionslab.market_filters import MarketFilters
import pandas as pd


def test_option_selector():
    """Test option selector functionality"""
    print("\n🎯 Testing Option Selector")
    
    # Test 1: Position sizing
    contracts, cost = calculate_position_size(10000, 5.50, 0.05)
    assert contracts == 0, f"Expected 0 contracts, got {contracts}"
    print("✅ Position sizing: correct for 5% of $10k at $5.50")
    
    # Test 2: With max contracts
    contracts, cost = calculate_position_size(100000, 5.50, 0.05, max_contracts=5)
    assert contracts <= 5, f"Expected <= 5 contracts, got {contracts}"
    print("✅ Max contracts limit working")
    
    return True


def test_greek_tracker():
    """Test Greek tracker functionality"""
    print("\n🏛️ Testing Greek Tracker")
    
    # Create snapshot with correct constructor
    snapshot = GreekSnapshot(
        date="2022-01-01",
        delta=0.5,
        gamma=0.02,
        theta=-0.05,
        vega=0.15,
        iv=0.25
    )
    
    # Create tracker
    tracker = GreekTracker(entry_greeks=snapshot)
    
    # Verify initialization
    assert tracker.entry_greeks.delta == 0.5, "Entry delta mismatch"
    assert tracker.current_greeks is not None, "Current Greeks should be initialized"
    assert len(tracker.history) == 1, "History should have entry Greeks"
    print("✅ Greek tracker initialization working")
    
    return True


def test_compliance_scorecard():
    """Test compliance scorecard calculation"""
    print("\n📈 Testing Compliance Scorecard")
    
    trades = [
        {
            'entry_delta': 0.45,
            'entry_dte': 45,
            'delta_compliant': True,
            'dte_compliant': True,
            'exit_reason': 'profit_target'
        },
        {
            'entry_delta': 0.50,
            'entry_dte': 40,
            'delta_compliant': True,
            'dte_compliant': True,
            'exit_reason': 'stop_loss'
        }
    ]
    
    scorecard = calculate_compliance_scorecard(trades)
    
    # Check scorecard structure
    assert 'overall_score' in scorecard, "Missing overall_score"
    assert 'delta_compliance' in scorecard, "Missing delta_compliance"
    assert 'dte_compliance' in scorecard, "Missing dte_compliance"
    print(f"✅ Compliance scorecard: {scorecard['overall_score']:.1%} overall")
    
    return True


def test_performance_metrics():
    """Test performance metrics calculation"""
    print("\n💰 Testing Performance Metrics")
    
    equity_curve = [
        {'date': '2022-01-01', 'total_value': 10000},
        {'date': '2022-01-02', 'total_value': 10100},
        {'date': '2022-01-03', 'total_value': 10200}
    ]
    
    trades = [
        {'pnl': 100, 'return_pct': 0.01},
        {'pnl': 100, 'return_pct': 0.01}
    ]
    
    metrics = calculate_performance_metrics(equity_curve, trades, 10000)
    
    # Check metrics
    assert metrics['total_return'] == 0.02, f"Expected 2% return, got {metrics['total_return']:.2%}"
    assert metrics['win_rate'] == 1.0, f"Expected 100% win rate, got {metrics['win_rate']:.1%}"
    print("✅ Performance metrics calculation working")
    
    return True


def test_config_loading():
    """Test configuration loading"""
    print("\n📁 Testing Config Loading")
    
    try:
        config = load_strategy_config("simple_test_strategy.yaml")
        assert config['name'] == "Simple Long Call", "Config name mismatch"
        assert config['strategy_type'] == "long_call", "Strategy type mismatch"
        print("✅ Config loading working")
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False


def test_trade_recorder():
    """Test trade recorder"""
    print("\n📝 Testing Trade Recorder")
    
    config = {
        'strategy': {
            'name': 'test',
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    recorder = TradeRecorder(config)
    assert recorder.trades == [], "Trades should be empty initially"
    print("✅ Trade recorder initialization working")
    
    return True


def test_exit_conditions():
    """Test exit conditions"""
    print("\n🚪 Testing Exit Conditions")
    
    config = {
        'strategy': {
            'exit_conditions': {
                'profit_target': 0.5,
                'stop_loss': -0.2
            }
        }
    }
    
    exit_cond = ExitConditions(config)
    assert exit_cond.profit_target == 0.5, "Profit target mismatch"
    assert exit_cond.stop_loss == -0.2, "Stop loss mismatch"
    print("✅ Exit conditions initialization working")
    
    return True


def test_market_filters():
    """Test market filters"""
    print("\n📊 Testing Market Filters")
    
    # Create sample data
    historical_data = pd.DataFrame({
        'date': pd.date_range('2022-01-01', periods=30, freq='D'),
        'close': [100 + i for i in range(30)]
    })
    
    config = {
        'strategy': {
            'market_filters': {
                'moving_average': {
                    'enabled': False
                }
            }
        }
    }
    
    filters = MarketFilters(config, historical_data)
    result = filters.check_all_filters('2022-01-15', 110, 14)
    assert result is True, "Disabled filters should return True"
    print("✅ Market filters working")
    
    return True


def main():
    """Run all tests"""
    print("🧪 Running OptionsLab Module Tests")
    print("=" * 60)
    
    tests = [
        test_config_loading,
        test_option_selector,
        test_greek_tracker,
        test_compliance_scorecard,
        test_performance_metrics,
        test_trade_recorder,
        test_exit_conditions,
        test_market_filters
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())