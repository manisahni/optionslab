#!/usr/bin/env python3
"""
Tests for the exit conditions module
"""

import pytest
from optionslab.exit_conditions import ExitConditions
from optionslab.trade_recorder import Position


def test_exit_conditions_initialization():
    """Test exit conditions initialization"""
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {
                'profit_target': 0.5,      # 50% profit
                'stop_loss': -0.2,         # 20% loss
                'dte_threshold': 21,       # Exit at 21 DTE
                'delta_threshold': 0.7,    # Exit if delta exceeds 0.7
                'max_days_in_trade': 30    # Maximum holding period
            }
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    assert exit_conditions.config == config
    assert exit_conditions.profit_target == 0.5
    assert exit_conditions.stop_loss == -0.2
    assert exit_conditions.dte_threshold == 21
    assert exit_conditions.delta_threshold == 0.7
    assert exit_conditions.max_days_in_trade == 30


def test_profit_target_exit():
    """Test profit target exit condition"""
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {
                'profit_target': 0.5  # 50% profit
            }
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    position = Position(
        entry_date='2022-01-01',
        strike=450,
        option_type='C',
        expiration='2022-02-15',
        contracts=1,
        entry_price=5.00,
        strategy_type='long_call'
    )
    
    # Test below profit target
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=200,  # 40% profit
        cash_used=500,
        current_option={'bid': 7.00, 'delta': 0.5, 'dte': 40},
        current_date='2022-01-05',
        underlying_price=455
    )
    
    assert should_exit is False
    
    # Test at profit target
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=250,  # 50% profit
        cash_used=500,
        current_option={'bid': 7.50, 'delta': 0.5, 'dte': 40},
        current_date='2022-01-05',
        underlying_price=455
    )
    
    assert should_exit is True
    assert reason == 'profit_target'


def test_stop_loss_exit():
    """Test stop loss exit condition"""
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {
                'stop_loss': -0.2  # 20% loss
            }
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    position = Position(
        entry_date='2022-01-01',
        strike=450,
        option_type='C',
        expiration='2022-02-15',
        contracts=1,
        entry_price=5.00,
        strategy_type='long_call'
    )
    
    # Test above stop loss
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=-50,   # 10% loss
        cash_used=500,
        current_option={'bid': 4.50, 'delta': 0.5, 'dte': 40},
        current_date='2022-01-05',
        underlying_price=445
    )
    
    assert should_exit is False
    
    # Test at stop loss
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=-100,  # 20% loss
        cash_used=500,
        current_option={'bid': 4.00, 'delta': 0.5, 'dte': 40},
        current_date='2022-01-05',
        underlying_price=445
    )
    
    assert should_exit is True
    assert reason == 'stop_loss'


def test_dte_threshold_exit():
    """Test DTE threshold exit condition"""
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {
                'dte_threshold': 21  # Exit at 21 DTE
            }
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    position = Position(
        entry_date='2022-01-01',
        strike=450,
        option_type='C',
        expiration='2022-02-15',
        contracts=1,
        entry_price=5.00,
        strategy_type='long_call'
    )
    
    # Test above DTE threshold
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=0,
        cash_used=500,
        current_option={'bid': 5.00, 'delta': 0.5, 'dte': 25},
        current_date='2022-01-21',
        underlying_price=450
    )
    
    assert should_exit is False
    
    # Test at DTE threshold
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=0,
        cash_used=500,
        current_option={'bid': 5.00, 'delta': 0.5, 'dte': 21},
        current_date='2022-01-25',
        underlying_price=450
    )
    
    assert should_exit is True
    assert reason == 'dte_threshold'


def test_delta_threshold_exit():
    """Test delta threshold exit condition"""
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {
                'delta_threshold': 0.7  # Exit if delta exceeds 0.7
            }
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    position = Position(
        entry_date='2022-01-01',
        strike=450,
        option_type='C',
        expiration='2022-02-15',
        contracts=1,
        entry_price=5.00,
        strategy_type='long_call'
    )
    
    # Test below delta threshold
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=100,
        cash_used=500,
        current_option={'bid': 6.00, 'delta': 0.65, 'dte': 40},
        current_date='2022-01-05',
        underlying_price=455
    )
    
    assert should_exit is False
    
    # Test at delta threshold
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=200,
        cash_used=500,
        current_option={'bid': 7.00, 'delta': 0.7, 'dte': 40},
        current_date='2022-01-05',
        underlying_price=458
    )
    
    assert should_exit is True
    assert reason == 'delta_threshold'


def test_max_days_in_trade_exit():
    """Test maximum days in trade exit condition"""
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {
                'max_days_in_trade': 30  # Maximum 30 days
            }
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    position = Position(
        entry_date='2022-01-01',
        strike=450,
        option_type='C',
        expiration='2022-03-15',  # Long expiration
        contracts=1,
        entry_price=5.00,
        strategy_type='long_call'
    )
    
    # Test before max days
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=0,
        cash_used=500,
        current_option={'bid': 5.00, 'delta': 0.5, 'dte': 45},
        current_date='2022-01-29',  # 28 days in trade
        underlying_price=450
    )
    
    assert should_exit is False
    
    # Test at max days
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=0,
        cash_used=500,
        current_option={'bid': 5.00, 'delta': 0.5, 'dte': 43},
        current_date='2022-01-31',  # 30 days in trade
        underlying_price=450
    )
    
    assert should_exit is True
    assert reason == 'max_days'


def test_exit_priority_order():
    """Test that exit conditions are checked in proper priority order"""
    # This test is from test_profit_stop_exits.py
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {
                'profit_target': 0.5,
                'stop_loss': -0.2,
                'dte_threshold': 21,
                'delta_threshold': 0.7
            }
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    position = Position(
        entry_date='2022-01-01',
        strike=450,
        option_type='C',
        expiration='2022-02-15',
        contracts=1,
        entry_price=5.00,
        strategy_type='long_call'
    )
    
    # Multiple conditions met - profit target should take precedence
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=250,  # 50% profit (meets profit target)
        cash_used=500,
        current_option={'bid': 7.50, 'delta': 0.75, 'dte': 20},  # Also meets delta and DTE
        current_date='2022-01-26',
        underlying_price=460
    )
    
    assert should_exit is True
    assert reason == 'profit_target'  # Profit target has highest priority


def test_expiration_exit():
    """Test automatic exit at expiration"""
    config = {
        'parameters': {'max_hold_days': 30},
        'strategy': {
            'exit_conditions': {}  # No specific conditions
        }
    }
    
    exit_conditions = ExitConditions(config)
    
    position = Position(
        entry_date='2022-01-01',
        strike=450,
        option_type='C',
        expiration='2022-01-15',
        contracts=1,
        entry_price=5.00,
        strategy_type='long_call'
    )
    
    # Test at expiration
    should_exit, reason = exit_conditions.check_all_exits(
        position=position,
        current_pnl=-500,  # Total loss
        cash_used=500,
        current_option={'bid': 0.00, 'delta': 0.0, 'dte': 0},
        current_date='2022-01-15',
        underlying_price=440
    )
    
    assert should_exit is True
    assert reason == 'expiration'