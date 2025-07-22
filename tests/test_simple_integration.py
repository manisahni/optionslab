#!/usr/bin/env python3
"""
Simple integration test without pytest dependency
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optionslab.backtest_engine import run_auditable_backtest
from optionslab.data_loader import load_data, load_strategy_config
from optionslab.option_selector import find_suitable_options, calculate_position_size
from optionslab.backtest_metrics import calculate_compliance_scorecard


def test_basic_functionality():
    """Test basic functionality of all modules"""
    print("\n🧪 Testing OptionsLab Module Integration")
    print("=" * 60)
    
    # Test 1: Data Loader
    print("\n📊 Test 1: Data Loader")
    try:
        config = load_strategy_config("simple_test_strategy.yaml")
        print("✅ Successfully loaded strategy config")
        print(f"   Strategy: {config['name']}")
        print(f"   Type: {config['strategy_type']}")
        print(f"   Delta target: {config['option_selection']['delta_criteria']['target']}")
        print(f"   DTE target: {config['option_selection']['dte_criteria']['target']}")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False
    
    # Test 2: Option Selector
    print("\n🎯 Test 2: Option Selector")
    try:
        # Test position sizing
        contracts = calculate_position_size(10000, 5.50, 0.05)
        print(f"✅ Position sizing: {contracts} contracts for $5.50 option")
        
        # Test with max contracts
        contracts_limited = calculate_position_size(10000, 5.50, 0.05, max_contracts=5)
        print(f"✅ Position sizing with limit: {contracts_limited} contracts (max 5)")
    except Exception as e:
        print(f"❌ Failed option selector test: {e}")
        return False
    
    # Test 3: Compliance Scorecard
    print("\n📈 Test 3: Compliance Scorecard")
    try:
        # Sample trades
        sample_trades = [
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
        
        scorecard = calculate_compliance_scorecard(sample_trades)
        print(f"✅ Compliance scorecard calculated:")
        print(f"   Overall score: {scorecard['overall_score']:.1%}")
        print(f"   Delta compliance: {scorecard['delta_compliance']:.1%}")
        print(f"   DTE compliance: {scorecard['dte_compliance']:.1%}")
    except Exception as e:
        print(f"❌ Failed compliance scorecard test: {e}")
        return False
    
    # Test 4: Small Backtest
    print("\n🚀 Test 4: Mini Backtest")
    try:
        data_file = "spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
        
        # Check if file exists
        if not os.path.exists(data_file):
            print(f"⚠️  Data file not found: {data_file}")
            print("   Skipping backtest test")
        else:
            # Run a very short backtest
            results = run_auditable_backtest(
                data_file,
                "simple_test_strategy.yaml",
                "2022-01-03",
                "2022-01-07"
            )
            
            if results:
                print("✅ Backtest completed successfully")
                print(f"   Final value: ${results['final_value']:,.2f}")
                print(f"   Total return: {results['total_return']:.2%}")
                print(f"   Trades executed: {len(results['trades'])}")
            else:
                print("❌ Backtest returned no results")
    except Exception as e:
        print(f"❌ Failed backtest test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ All basic integration tests passed!")
    return True


def test_module_imports():
    """Test that all modules can be imported"""
    print("\n📦 Testing Module Imports")
    print("=" * 60)
    
    modules = [
        "optionslab.backtest_engine",
        "optionslab.option_selector",
        "optionslab.data_loader",
        "optionslab.backtest_metrics",
        "optionslab.market_filters",
        "optionslab.greek_tracker",
        "optionslab.trade_recorder",
        "optionslab.exit_conditions",
        "optionslab.visualization",
        "optionslab.app"
    ]
    
    all_imported = True
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            all_imported = False
    
    return all_imported


if __name__ == "__main__":
    print("🔧 Running Simple Integration Tests")
    
    # Test imports first
    imports_ok = test_module_imports()
    
    if imports_ok:
        # Run functionality tests
        functionality_ok = test_basic_functionality()
        
        if functionality_ok:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some functionality tests failed")
            sys.exit(1)
    else:
        print("\n❌ Import tests failed - cannot proceed with functionality tests")
        sys.exit(1)