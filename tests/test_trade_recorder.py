#!/usr/bin/env python3
"""
Tests for the trade recorder module
"""

import pytest
from datetime import datetime
from optionslab.trade_recorder import TradeRecorder, Trade, Position
from optionslab.greek_tracker import GreekSnapshot


def test_trade_recorder_initialization():
    """Test trade recorder initialization"""
    config = {
        'strategy': {
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    recorder = TradeRecorder(config)
    
    assert recorder.trades == []
    assert recorder.config == config


def test_record_entry():
    """Test recording trade entry"""
    config = {
        'strategy': {
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    recorder = TradeRecorder(config)
    
    # Record entry
    selected_option = {
        'strike': 450,
        'option_type': 'C',
        'expiration': '2022-02-15',
        'delta': 0.5,
        'gamma': 0.02,
        'theta': -0.05,
        'vega': 0.15,
        'iv': 0.25,
        'ask': 5.50,
        'volume': 1000,
        'dte': 45
    }
    
    position = recorder.record_entry(
        selected_option=selected_option,
        current_date='2022-01-01',
        contracts=2,
        strategy_type='long_call',
        underlying_price=450.0,
        cash_used=1100.0  # 2 contracts * $5.50 * 100
    )
    
    # Verify position created
    assert isinstance(position, Position)
    assert position.contracts == 2
    assert position.entry_price == 5.50
    assert position.strategy_type == 'long_call'
    
    # Verify trade recorded
    assert len(recorder.trades) == 1
    trade = recorder.trades[0]
    assert trade.entry_date == '2022-01-01'
    assert trade.strike == 450
    assert trade.entry_delta == 0.5
    assert trade.entry_dte == 45


def test_record_exit():
    """Test recording trade exit"""
    config = {
        'strategy': {
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    recorder = TradeRecorder(config)
    
    # First record entry
    selected_option = {
        'strike': 450, 'option_type': 'C', 'expiration': '2022-02-15',
        'delta': 0.5, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.15,
        'iv': 0.25, 'ask': 5.50, 'volume': 1000, 'dte': 45
    }
    
    position = recorder.record_entry(
        selected_option=selected_option,
        current_date='2022-01-01',
        contracts=2,
        strategy_type='long_call',
        underlying_price=450.0,
        cash_used=1100.0
    )
    
    # Record exit
    exit_option = {
        'bid': 7.50,  # Profitable exit
        'delta': 0.65,
        'gamma': 0.018,
        'theta': -0.06,
        'vega': 0.14,
        'iv': 0.23,
        'dte': 40
    }
    
    recorder.record_exit(
        trade=recorder.trades[0],
        exit_option=exit_option,
        current_date='2022-01-06',
        exit_reason='profit_target',
        underlying_price=455.0,
        position=position
    )
    
    # Verify exit recorded
    trade = recorder.trades[0]
    assert trade.exit_date == '2022-01-06'
    assert trade.exit_price == 7.50
    assert trade.exit_reason == 'profit_target'
    assert trade.pnl == 400.0  # (7.50 - 5.50) * 2 * 100
    assert trade.return_pct == pytest.approx(0.3636, rel=0.01)  # 400/1100


def test_compliance_tracking():
    """Test compliance tracking in trades"""
    config = {
        'strategy': {
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    recorder = TradeRecorder(config)
    
    # Record compliant trade
    compliant_option = {
        'strike': 450, 'option_type': 'C', 'expiration': '2022-02-15',
        'delta': 0.5, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.15,
        'iv': 0.25, 'ask': 5.50, 'volume': 1000, 'dte': 45
    }
    
    recorder.record_entry(
        selected_option=compliant_option,
        current_date='2022-01-01',
        contracts=1,
        strategy_type='long_call',
        underlying_price=450.0,
        cash_used=550.0
    )
    
    # Check compliance
    trade = recorder.trades[0]
    assert trade.delta_compliant is True  # 0.5 is within 0.4-0.6
    assert trade.dte_compliant is True    # 45 is within 30-60
    
    # Record non-compliant trade
    non_compliant_option = {
        'strike': 450, 'option_type': 'C', 'expiration': '2022-02-15',
        'delta': 0.3,  # Below min delta
        'gamma': 0.02, 'theta': -0.05, 'vega': 0.15,
        'iv': 0.25, 'ask': 5.50, 'volume': 1000, 'dte': 25  # Below min DTE
    }
    
    recorder.record_entry(
        selected_option=non_compliant_option,
        current_date='2022-01-01',
        contracts=1,
        strategy_type='long_call',
        underlying_price=450.0,
        cash_used=550.0
    )
    
    # Check non-compliance
    trade = recorder.trades[1]
    assert trade.delta_compliant is False  # 0.3 is below 0.4
    assert trade.dte_compliant is False    # 25 is below 30


def test_greek_tracking_integration():
    """Test Greek tracking integration with trade recorder"""
    config = {
        'strategy': {
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    recorder = TradeRecorder(config)
    
    # Record entry with Greeks
    option = {
        'strike': 450, 'option_type': 'C', 'expiration': '2022-02-15',
        'delta': 0.5, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.15,
        'iv': 0.25, 'ask': 5.50, 'volume': 1000, 'dte': 45
    }
    
    position = recorder.record_entry(
        selected_option=option,
        current_date='2022-01-01',
        contracts=1,
        strategy_type='long_call',
        underlying_price=450.0,
        cash_used=550.0
    )
    
    # Verify Greek tracker created
    trade = recorder.trades[0]
    assert trade.greek_tracker is not None
    assert trade.greek_tracker.entry_greeks.delta == 0.5
    assert trade.greek_tracker.entry_greeks.gamma == 0.02


def test_trade_summary_generation():
    """Test generating trade summaries"""
    config = {
        'strategy': {
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    recorder = TradeRecorder(config)
    
    # Record a complete trade
    entry_option = {
        'strike': 450, 'option_type': 'C', 'expiration': '2022-02-15',
        'delta': 0.5, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.15,
        'iv': 0.25, 'ask': 5.50, 'volume': 1000, 'dte': 45
    }
    
    position = recorder.record_entry(
        selected_option=entry_option,
        current_date='2022-01-01',
        contracts=2,
        strategy_type='long_call',
        underlying_price=450.0,
        cash_used=1100.0
    )
    
    exit_option = {
        'bid': 8.00, 'delta': 0.7, 'gamma': 0.015, 'theta': -0.07,
        'vega': 0.13, 'iv': 0.22, 'dte': 35
    }
    
    recorder.record_exit(
        trade=recorder.trades[0],
        exit_option=exit_option,
        current_date='2022-01-11',
        exit_reason='profit_target',
        underlying_price=458.0,
        position=position
    )
    
    # Get trade summary
    trade = recorder.trades[0]
    summary = {
        'entry_date': trade.entry_date,
        'exit_date': trade.exit_date,
        'days_held': 10,
        'entry_price': trade.entry_price,
        'exit_price': trade.exit_price,
        'pnl': trade.pnl,
        'return_pct': trade.return_pct,
        'exit_reason': trade.exit_reason,
        'delta_change': 0.2,  # 0.7 - 0.5
        'underlying_move': 8.0  # 458 - 450
    }
    
    # Verify summary data
    assert summary['pnl'] == 500.0  # (8.00 - 5.50) * 2 * 100
    assert summary['return_pct'] == pytest.approx(0.4545, rel=0.01)
    assert summary['exit_reason'] == 'profit_target'