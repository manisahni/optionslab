#!/usr/bin/env python3
"""
Tests for the backtest metrics module
"""

import pytest
from optionslab.backtest_metrics import (
    calculate_performance_metrics,
    calculate_compliance_scorecard,
    create_implementation_metrics
)


def test_calculate_performance_metrics():
    """Test performance metrics calculation"""
    # Sample equity curve
    equity_curve = [
        {'date': '2022-01-01', 'total_value': 10000},
        {'date': '2022-01-02', 'total_value': 10100},
        {'date': '2022-01-03', 'total_value': 10050},
        {'date': '2022-01-04', 'total_value': 10200},
        {'date': '2022-01-05', 'total_value': 10150}
    ]
    
    # Sample trades
    trades = [
        {
            'entry_date': '2022-01-02',
            'exit_date': '2022-01-04',
            'pnl': 100,
            'return_pct': 0.01
        },
        {
            'entry_date': '2022-01-04',
            'exit_date': '2022-01-05',
            'pnl': -50,
            'return_pct': -0.005
        }
    ]
    
    initial_capital = 10000
    
    metrics = calculate_performance_metrics(equity_curve, trades, initial_capital)
    
    # Verify metrics structure
    assert 'total_return' in metrics
    assert 'sharpe_ratio' in metrics
    assert 'max_drawdown' in metrics
    assert 'win_rate' in metrics
    assert 'avg_win' in metrics
    assert 'avg_loss' in metrics
    assert 'profit_factor' in metrics
    
    # Verify calculations
    assert metrics['total_return'] == 0.015  # 1.5% return
    assert metrics['win_rate'] == 0.5  # 1 win, 1 loss
    assert metrics['avg_win'] == 100
    assert metrics['avg_loss'] == -50


def test_calculate_compliance_scorecard():
    """Test compliance scorecard calculation"""
    # Sample trades with compliance data
    trades = [
        {
            'entry_delta': 0.45,
            'entry_dte': 45,
            'delta_compliant': True,
            'dte_compliant': True,
            'exit_reason': 'profit_target'
        },
        {
            'entry_delta': 0.35,  # Out of range
            'entry_dte': 45,
            'delta_compliant': False,
            'dte_compliant': True,
            'exit_reason': 'stop_loss'
        },
        {
            'entry_delta': 0.50,
            'entry_dte': 25,  # Out of range
            'delta_compliant': True,
            'dte_compliant': False,
            'exit_reason': 'dte_threshold'
        }
    ]
    
    scorecard = calculate_compliance_scorecard(trades)
    
    # Verify scorecard structure
    assert 'overall_score' in scorecard
    assert 'delta_compliance' in scorecard
    assert 'dte_compliance' in scorecard
    assert 'delta_distribution' in scorecard
    assert 'dte_distribution' in scorecard
    assert 'exit_reasons' in scorecard
    
    # Verify calculations
    assert scorecard['delta_compliance'] == 2/3  # 2 out of 3 compliant
    assert scorecard['dte_compliance'] == 2/3    # 2 out of 3 compliant
    assert scorecard['overall_score'] == (2/3 + 2/3) / 2  # Average of both
    
    # Verify exit reasons
    assert scorecard['exit_reasons']['profit_target'] == 1
    assert scorecard['exit_reasons']['stop_loss'] == 1
    assert scorecard['exit_reasons']['dte_threshold'] == 1


def test_create_implementation_metrics():
    """Test implementation metrics creation"""
    trades = [
        {
            'entry_date': '2022-01-02',
            'exit_date': '2022-01-04',
            'entry_delta': 0.45,
            'entry_dte': 45,
            'pnl': 100,
            'return_pct': 0.01,
            'delta_compliant': True,
            'dte_compliant': True
        },
        {
            'entry_date': '2022-01-05',
            'exit_date': '2022-01-07',
            'entry_delta': 0.50,
            'entry_dte': 43,
            'pnl': 150,
            'return_pct': 0.015,
            'delta_compliant': True,
            'dte_compliant': True
        }
    ]
    
    config = {
        'strategy': {
            'delta_range': {'min': 0.4, 'max': 0.6},
            'dte_range': {'min': 30, 'max': 60}
        }
    }
    
    metrics = create_implementation_metrics(trades, config)
    
    # Verify metrics structure
    assert 'avg_entry_delta' in metrics
    assert 'avg_entry_dte' in metrics
    assert 'delta_range_adherence' in metrics
    assert 'dte_range_adherence' in metrics
    assert 'total_trades' in metrics
    
    # Verify calculations
    assert metrics['avg_entry_delta'] == 0.475  # (0.45 + 0.50) / 2
    assert metrics['avg_entry_dte'] == 44       # (45 + 43) / 2
    assert metrics['delta_range_adherence'] == 1.0  # Both trades compliant
    assert metrics['dte_range_adherence'] == 1.0    # Both trades compliant
    assert metrics['total_trades'] == 2


def test_win_rate_calculation():
    """Test win rate calculation edge cases"""
    # This test incorporates fixes from test_win_rate_fix.py
    
    # All winning trades
    winning_trades = [
        {'pnl': 100, 'return_pct': 0.01},
        {'pnl': 200, 'return_pct': 0.02},
        {'pnl': 50, 'return_pct': 0.005}
    ]
    
    metrics = calculate_performance_metrics(
        [{'date': '2022-01-01', 'total_value': 10000}],
        winning_trades,
        10000
    )
    
    assert metrics['win_rate'] == 1.0
    assert metrics['avg_loss'] == 0  # No losses
    
    # All losing trades
    losing_trades = [
        {'pnl': -100, 'return_pct': -0.01},
        {'pnl': -50, 'return_pct': -0.005}
    ]
    
    metrics = calculate_performance_metrics(
        [{'date': '2022-01-01', 'total_value': 10000}],
        losing_trades,
        10000
    )
    
    assert metrics['win_rate'] == 0.0
    assert metrics['avg_win'] == 0  # No wins
    
    # No trades
    metrics = calculate_performance_metrics(
        [{'date': '2022-01-01', 'total_value': 10000}],
        [],
        10000
    )
    
    assert metrics['win_rate'] == 0.0
    assert metrics['avg_win'] == 0
    assert metrics['avg_loss'] == 0