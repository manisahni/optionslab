#!/usr/bin/env python3
"""
Comprehensive Test Suite for YAML Integration
Tests all components of the YAML-based strategy configuration system
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yaml
import json
from typing import Dict, Any, List

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "optionslab-core"))
sys.path.append(str(Path(__file__).parent / "optionslab-ui"))

# Import all components to test
from core.strategy_config_manager import StrategyConfigManager
from core.advanced_exit_manager import AdvancedExitManager
from core.volatility_stop_calculator import VolatilityStopCalculator
from optionslab_core.greeks_tracker import GreeksTracker, GreeksSnapshot
from spy_backtester.strategy_base import SimpleStrategy
from spy_backtester.portfolio_manager import PortfolioManager
from spy_backtester.config import DEFAULT_PARAMS

# Test results tracking
test_results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}


def test_pass(test_name: str, message: str = ""):
    """Record a passing test"""
    test_results['passed'] += 1
    print(f"✅ PASS: {test_name}")
    if message:
        print(f"   {message}")


def test_fail(test_name: str, error: str):
    """Record a failing test"""
    test_results['failed'] += 1
    test_results['errors'].append(f"{test_name}: {error}")
    print(f"❌ FAIL: {test_name}")
    print(f"   Error: {error}")


def test_strategy_config_manager():
    """Test StrategyConfigManager functionality"""
    print("\n" + "="*60)
    print("Testing StrategyConfigManager")
    print("="*60)
    
    try:
        # Initialize manager
        manager = StrategyConfigManager()
        test_pass("StrategyConfigManager initialization")
        
        # Test available files discovery
        strategies = manager.get_available_strategies()
        templates = manager.get_available_templates()
        test_pass(f"File discovery", f"Found {len(strategies)} strategies, {len(templates)} templates")
        
        # Test loading a template
        if templates:
            template_file = templates[0]
            config = manager.load_strategy_config(template_file)
            test_pass(f"Load template config", f"Loaded {template_file}")
            
            # Test validation
            if 'name' in config and 'legs' in config:
                test_pass("Config validation", "Required fields present")
            else:
                test_fail("Config validation", "Missing required fields")
            
            # Test template variable extraction
            variables = manager.extract_template_variables(config)
            if isinstance(variables, list):
                test_pass("Template variable extraction", f"Found {len(variables)} variables")
            else:
                test_fail("Template variable extraction", "Invalid return type")
            
            # Test Greeks parsing
            greeks_config = manager.parse_greeks_exits_config(config)
            if isinstance(greeks_config, dict):
                test_pass("Greeks exits parsing", f"Parsed config: {list(greeks_config.keys())}")
            else:
                test_fail("Greeks exits parsing", "Invalid return type")
            
            # Test dynamic stops parsing
            dynamic_config = manager.parse_dynamic_stops_config(config)
            if isinstance(dynamic_config, dict):
                test_pass("Dynamic stops parsing", f"Parsed config: {list(dynamic_config.keys())}")
            else:
                test_fail("Dynamic stops parsing", "Invalid return type")
            
            # Test enhanced summary
            summary = manager.get_enhanced_config_summary(config)
            if 'has_dynamic_stops' in summary and 'has_greeks_exits' in summary:
                test_pass("Enhanced config summary", f"Features: {summary}")
            else:
                test_fail("Enhanced config summary", "Missing expected fields")
                
        else:
            test_fail("Template loading", "No templates found")
            
    except Exception as e:
        test_fail("StrategyConfigManager", str(e))


def test_advanced_exit_manager():
    """Test AdvancedExitManager functionality"""
    print("\n" + "="*60)
    print("Testing AdvancedExitManager")
    print("="*60)
    
    try:
        # Test configuration
        config = {
            'enable_dynamic_stops': True,
            'enable_greeks_exits': True,
            'enable_iv_exits': True,
            'enable_time_exits': True,
            'signal_threshold': 0.6,
            'profit_target_pct': 1.0,
            'stop_loss_pct': 0.5,
            'dte_exit_threshold': 5
        }
        
        # Initialize manager
        manager = AdvancedExitManager(config)
        test_pass("AdvancedExitManager initialization")
        
        # Test Greeks threshold configuration
        manager.configure_greeks_thresholds(
            delta_threshold=0.15,
            iv_rank_threshold=20,
            theta_acceleration_threshold=2.0
        )
        test_pass("Greeks threshold configuration")
        
        # Test exit condition checking
        position_data = {
            'entry_price': 10.0,
            'current_price': 11.0,
            'quantity': 1,
            'entry_date': datetime.now() - timedelta(days=10),
            'current_date': datetime.now(),
            'dte': 20,
            'entry_dte': 30,
            'is_long': True
        }
        
        greeks_data = {
            'delta': 0.3,
            'gamma': 0.05,
            'theta': -0.1,
            'vega': 0.2,
            'iv': 0.25,
            'iv_rank': 50,
            'entry_delta': 0.5,
            'entry_gamma': 0.03,
            'entry_theta': -0.05,
            'entry_vega': 0.15,
            'entry_iv': 0.20
        }
        
        exit_decision = manager.check_exit_conditions(position_data, greeks_data)
        
        if isinstance(exit_decision, dict) and 'should_exit' in exit_decision:
            test_pass("Exit condition checking", f"Decision: {exit_decision['should_exit']}")
        else:
            test_fail("Exit condition checking", "Invalid return format")
            
        # Test with volatility calculator
        vol_calc = VolatilityStopCalculator({'atr_period': 14})
        manager.set_volatility_calculator(vol_calc)
        test_pass("Volatility calculator integration")
        
    except Exception as e:
        test_fail("AdvancedExitManager", str(e))


def test_greeks_tracker():
    """Test GreeksTracker functionality"""
    print("\n" + "="*60)
    print("Testing GreeksTracker")
    print("="*60)
    
    try:
        # Initialize tracker
        tracker = GreeksTracker()
        test_pass("GreeksTracker initialization")
        
        # Create test option data
        option_data = pd.Series({
            'underlying_price': 450.0,
            'dte': 30,
            'delta': 0.5,
            'gamma': 0.02,
            'theta': -0.05,
            'vega': 0.15,
            'rho': 0.01,
            'implied_volatility': 0.20,
            'mid_price': 10.0,
            'iv_rank': 45,
            'iv_percentile': 50
        })
        
        # Test position tracking creation
        position_id = "P_450_20240131"
        entry_data = {'timestamp': datetime.now()}
        tracker.create_position_tracking(position_id, entry_data, option_data, quantity=1)
        test_pass("Position tracking creation")
        
        # Test position update
        tracker.update_position_greeks(
            position_id=position_id,
            current_data=option_data,
            quantity=1,
            entry_price=10.0,
            timestamp=datetime.now()
        )
        test_pass("Position Greeks update")
        
        # Test Greeks pattern analysis
        patterns = tracker.analyze_greeks_patterns(position_id)
        if isinstance(patterns, dict):
            test_pass("Greeks pattern analysis", f"Patterns: {list(patterns.keys())}")
        else:
            test_fail("Greeks pattern analysis", "Invalid return type")
        
        # Test exit signals
        thresholds = {
            'delta_decay_threshold': 50,
            'theta_acceleration_threshold': 2.0,
            'iv_crush_threshold': -20,
            'gamma_risk_threshold': 0.10
        }
        signals = tracker.get_exit_signals_from_greeks(position_id, thresholds)
        if isinstance(signals, list):
            test_pass("Exit signal generation", f"Generated {len(signals)} signals")
        else:
            test_fail("Exit signal generation", "Invalid return type")
        
        # Test history retrieval
        history_df = tracker.get_position_greeks_history(position_id)
        if history_df is not None:
            test_pass("Greeks history retrieval", f"History shape: {history_df.shape}")
        else:
            test_fail("Greeks history retrieval", "No history found")
            
    except Exception as e:
        test_fail("GreeksTracker", str(e))


def test_yaml_cli_integration():
    """Test YAML integration with CLI"""
    print("\n" + "="*60)
    print("Testing YAML CLI Integration")
    print("="*60)
    
    try:
        # Create a test YAML configuration
        test_yaml = {
            'name': 'Test Strategy',
            'description': 'Integration test strategy',
            'category': 'test',
            'version': '1.0',
            'legs': [{
                'type': 'put',
                'direction': 'long',
                'quantity': 1,
                'delta_target': -0.40,
                'delta_tolerance': 0.10
            }],
            'entry_rules': {
                'dte': 30,
                'dte_tolerance': 5,
                'target_delta': -0.40,
                'delta_tolerance': 0.10,
                'volume_min': 100
            },
            'exit_rules': {
                'profit_target_pct': 0.75,
                'stop_loss_pct': 0.40,
                'exit_on_dte': 5
            },
            'dynamic_stops': {
                'enabled': True,
                'atr_settings': {
                    'period': 14,
                    'volatility_lookback': 30
                },
                'component_weights': {
                    'atr_weight': 0.4,
                    'vega_weight': 0.35,
                    'theta_weight': 0.25
                }
            },
            'greeks_exits': {
                'enabled': True,
                'delta_threshold_exit': {
                    'enabled': True,
                    'threshold': 0.15
                }
            }
        }
        
        # Save test YAML
        test_yaml_path = Path("spy_backtester/config/strategies/test_integration.yaml")
        test_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(test_yaml_path, 'w') as f:
            yaml.dump(test_yaml, f)
        test_pass("Test YAML creation", f"Saved to {test_yaml_path}")
        
        # Test loading with StrategyConfigManager
        manager = StrategyConfigManager()
        loaded_config = manager.load_strategy_config(test_yaml_path.name)
        test_pass("YAML loading through manager")
        
        # Test parameter extraction
        params = DEFAULT_PARAMS.copy()
        
        # Test dynamic stops parsing
        if loaded_config.get('dynamic_stops', {}).get('enabled'):
            params['use_advanced_exits'] = True
            params['enable_dynamic_stops'] = True
            test_pass("Dynamic stops parameter extraction")
        
        # Test Greeks exits parsing
        if loaded_config.get('greeks_exits', {}).get('enabled'):
            params['enable_greeks_exits'] = True
            test_pass("Greeks exits parameter extraction")
        
        # Clean up test file
        test_yaml_path.unlink()
        test_pass("Test cleanup")
        
    except Exception as e:
        test_fail("YAML CLI Integration", str(e))


def test_strategy_integration():
    """Test integration with strategy base class"""
    print("\n" + "="*60)
    print("Testing Strategy Integration")
    print("="*60)
    
    try:
        # Create test parameters with advanced features
        params = DEFAULT_PARAMS.copy()
        params.update({
            'use_advanced_exits': True,
            'enable_dynamic_stops': True,
            'enable_greeks_exits': True,
            'delta_exit_threshold': 0.15,
            'atr_period': 14,
            'atr_weight': 0.4,
            'vega_weight': 0.35,
            'theta_weight': 0.25
        })
        
        # Create a test strategy
        from spy_backtester.strategies.simple_strategies import LongPutStrategy
        strategy = LongPutStrategy(params)
        test_pass("Strategy creation with advanced exits")
        
        # Verify advanced exit components
        if hasattr(strategy, 'exit_manager') and strategy.exit_manager is not None:
            test_pass("Exit manager initialization")
        else:
            test_fail("Exit manager initialization", "Exit manager not found")
            
        if hasattr(strategy, 'volatility_calculator') and strategy.volatility_calculator is not None:
            test_pass("Volatility calculator initialization")
        else:
            test_fail("Volatility calculator initialization", "Volatility calculator not found")
            
    except Exception as e:
        test_fail("Strategy Integration", str(e))


def test_portfolio_greeks_integration():
    """Test Greeks tracking in portfolio manager"""
    print("\n" + "="*60)
    print("Testing Portfolio Greeks Integration")
    print("="*60)
    
    try:
        # Initialize portfolio manager with Greeks tracking
        portfolio = PortfolioManager(initial_capital=100000, track_greeks=True)
        test_pass("Portfolio manager with Greeks tracking")
        
        # Verify Greeks tracker exists
        if hasattr(portfolio, 'greeks_tracker') and portfolio.greeks_tracker is not None:
            test_pass("Greeks tracker in portfolio")
        else:
            test_fail("Greeks tracker in portfolio", "Greeks tracker not found")
            
        # Test Greeks history methods
        if hasattr(portfolio, 'get_greeks_history_df'):
            history_df = portfolio.get_greeks_history_df()
            test_pass("Greeks history method", f"DataFrame type: {type(history_df)}")
        else:
            test_fail("Greeks history method", "Method not found")
            
    except Exception as e:
        test_fail("Portfolio Greeks Integration", str(e))


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("YAML INTEGRATION TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all test suites
    test_strategy_config_manager()
    test_advanced_exit_manager()
    test_greeks_tracker()
    test_yaml_cli_integration()
    test_strategy_integration()
    test_portfolio_greeks_integration()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"📊 Total:  {test_results['passed'] + test_results['failed']}")
    
    if test_results['failed'] > 0:
        print("\n❌ FAILED TESTS:")
        for error in test_results['errors']:
            print(f"  - {error}")
    else:
        print("\n🎉 ALL TESTS PASSED!")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Return exit code
    return 0 if test_results['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)