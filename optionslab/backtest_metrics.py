"""
Backtest metrics and performance calculations
Handles implementation metrics, compliance scoring, and performance analysis
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional


def create_implementation_metrics(trades: List[Dict], config: Dict) -> Dict:
    """Create metrics to verify strategy implementation correctness
    
    Args:
        trades: List of completed trade dictionaries
        config: Strategy configuration
        
    Returns:
        Dictionary containing implementation metrics and analysis
    """
    if not trades:
        return {'status': 'NO_TRADES', 'issues': ['No trades executed']}
    
    completed_trades = [t for t in trades if 'exit_date' in t]
    if not completed_trades:
        return {'status': 'NO_COMPLETED_TRADES', 'issues': ['No completed trades']}
    
    # Extract targets from config
    option_selection = config.get('option_selection', {})
    delta_criteria = option_selection.get('delta_criteria', {})
    dte_criteria = option_selection.get('dte_criteria', {})
    
    target_delta = delta_criteria.get('target', 0.30)
    delta_tolerance = delta_criteria.get('tolerance', 0.05)
    target_dte = dte_criteria.get('target', 45)
    dte_min = dte_criteria.get('minimum', 30)
    dte_max = dte_criteria.get('maximum', 60)
    
    # Initialize metrics
    metrics = {
        'target_delta': target_delta,
        'target_dte': target_dte,
        'delta_tolerance': delta_tolerance,
        'dte_range': [dte_min, dte_max],
        'total_trades': len(completed_trades),
        'issues': [],
        'warnings': [],
        'status': 'PASS'
    }
    
    # Delta analysis
    deltas = [abs(t.get('entry_delta', 0)) for t in completed_trades if t.get('entry_delta') is not None]
    if deltas:
        metrics['delta_analysis'] = {
            'mean': np.mean(deltas),
            'std': np.std(deltas),
            'min': min(deltas),
            'max': max(deltas),
            'within_tolerance': sum(1 for d in deltas if abs(d - target_delta) <= delta_tolerance),
            'outside_tolerance': sum(1 for d in deltas if abs(d - target_delta) > delta_tolerance)
        }
        
        # Check if deltas are systematically off target
        if metrics['delta_analysis']['mean'] < target_delta - delta_tolerance:
            metrics['issues'].append(f"Delta selection too low: mean {metrics['delta_analysis']['mean']:.3f} vs target {target_delta}")
            metrics['status'] = 'FAIL'
        elif metrics['delta_analysis']['mean'] > target_delta + delta_tolerance:
            metrics['issues'].append(f"Delta selection too high: mean {metrics['delta_analysis']['mean']:.3f} vs target {target_delta}")
            metrics['status'] = 'FAIL'
    else:
        metrics['issues'].append("No delta data available in trades")
        metrics['status'] = 'FAIL'
    
    # DTE analysis
    dtes = [t.get('dte_actual', 0) for t in completed_trades if t.get('dte_actual') is not None]
    if dtes:
        metrics['dte_analysis'] = {
            'mean': np.mean(dtes),
            'std': np.std(dtes),
            'min': min(dtes),
            'max': max(dtes),
            'within_range': sum(1 for d in dtes if dte_min <= d <= dte_max),
            'outside_range': sum(1 for d in dtes if d < dte_min or d > dte_max)
        }
        
        # Check DTE compliance
        if metrics['dte_analysis']['mean'] < dte_min:
            metrics['issues'].append(f"DTE selection too short: mean {metrics['dte_analysis']['mean']:.1f} vs min {dte_min}")
            metrics['status'] = 'FAIL'
        elif metrics['dte_analysis']['mean'] > dte_max:
            metrics['issues'].append(f"DTE selection too long: mean {metrics['dte_analysis']['mean']:.1f} vs max {dte_max}")
            metrics['status'] = 'FAIL'
    else:
        metrics['issues'].append("No DTE data available in trades")
        metrics['status'] = 'FAIL'
    
    # Selection process analysis
    selection_processes = [t.get('selection_process', {}) for t in completed_trades if t.get('selection_process')]
    if selection_processes:
        # Aggregate selection process data
        total_options_sum = sum(sp.get('total_options', 0) for sp in selection_processes)
        after_dte_sum = sum(sp.get('after_dte_filter', 0) for sp in selection_processes)
        after_delta_sum = sum(sp.get('after_delta_filter', 0) for sp in selection_processes)
        after_liquidity_sum = sum(sp.get('after_liquidity_filter', 0) for sp in selection_processes)
        
        metrics['selection_process_summary'] = {
            'avg_total_options': total_options_sum / len(selection_processes) if selection_processes else 0,
            'avg_after_dte': after_dte_sum / len(selection_processes) if selection_processes else 0,
            'avg_after_delta': after_delta_sum / len(selection_processes) if selection_processes else 0,
            'avg_after_liquidity': after_liquidity_sum / len(selection_processes) if selection_processes else 0,
            'trades_with_relaxed_criteria': sum(1 for sp in selection_processes if sp.get('criteria_relaxed', []))
        }
        
        # Check if criteria are being relaxed too often
        relaxation_rate = metrics['selection_process_summary']['trades_with_relaxed_criteria'] / len(selection_processes)
        if relaxation_rate > 0.5:
            metrics['warnings'].append(f"High criteria relaxation rate: {relaxation_rate:.1%} of trades required relaxed criteria")
    
    # Exit reason analysis
    exit_reasons = [t.get('exit_reason', 'unknown') for t in completed_trades]
    exit_reason_counts = pd.Series(exit_reasons).value_counts().to_dict()
    metrics['exit_reason_distribution'] = exit_reason_counts
    
    return metrics


def calculate_compliance_scorecard(trades: List[Dict]) -> Dict:
    """Calculate compliance metrics for all trades
    
    Args:
        trades: List of trade dictionaries
        
    Returns:
        Dictionary containing compliance scores and breakdowns
    """
    if not trades:
        return {
            'overall_score': 0,
            'delta_compliance': 0,
            'dte_compliance': 0,
            'entry_compliance': 0,
            'exit_compliance': 0,
            'total_trades': 0,
            'compliant_trades': 0,
            'non_compliant_trades': 0,
            'compliance_by_category': {}
        }
    
    # Count compliance by category
    delta_compliant = 0
    delta_total = 0
    dte_compliant = 0
    dte_total = len(trades)
    
    for trade in trades:
        # Delta compliance
        if 'delta_compliant' in trade and trade.get('delta_actual') is not None:
            delta_total += 1
            if trade['delta_compliant']:
                delta_compliant += 1
        
        # DTE compliance
        if 'dte_compliant' in trade and trade['dte_compliant']:
            dte_compliant += 1
    
    # Calculate percentages
    delta_compliance_pct = (delta_compliant / delta_total * 100) if delta_total > 0 else 0
    dte_compliance_pct = (dte_compliant / dte_total * 100) if dte_total > 0 else 100
    
    # Count fully compliant trades
    compliant_trades = sum(1 for t in trades if t.get('compliance_score', 0) == 100)
    
    # Overall score is average of all categories
    overall_score = (delta_compliance_pct + dte_compliance_pct) / 2
    
    return {
        'overall_score': overall_score,
        'delta_compliance': delta_compliance_pct,
        'dte_compliance': dte_compliance_pct,
        'entry_compliance': 100,  # Will enhance with entry timing checks
        'exit_compliance': 100,   # Will enhance with exit rule checks
        'total_trades': len(trades),
        'compliant_trades': compliant_trades,
        'non_compliant_trades': len(trades) - compliant_trades,
        'compliance_by_category': {
            'delta': {'compliant': delta_compliant, 'total': delta_total, 'pct': delta_compliance_pct},
            'dte': {'compliant': dte_compliant, 'total': dte_total, 'pct': dte_compliance_pct}
        }
    }


def calculate_performance_metrics(equity_curve: List[Dict], trades: List[Dict], 
                                initial_capital: float) -> Dict:
    """Calculate comprehensive performance metrics
    
    Args:
        equity_curve: List of equity snapshots
        trades: List of completed trades
        initial_capital: Starting capital
        
    Returns:
        Dictionary with performance metrics
    """
    metrics = {
        'total_return': 0,
        'sharpe_ratio': 0,
        'max_drawdown': 0,
        'win_rate': 0,
        'profit_factor': 0,
        'avg_win': 0,
        'avg_loss': 0,
        'total_trades': 0
    }
    
    if not equity_curve:
        return metrics
    
    # Calculate total return
    final_value = equity_curve[-1]['total_value']
    metrics['total_return'] = (final_value - initial_capital) / initial_capital
    
    # Calculate Sharpe ratio and max drawdown
    if len(equity_curve) > 1:
        equity_values = [point['total_value'] for point in equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        
        if len(returns) > 0 and np.std(returns) > 0:
            metrics['sharpe_ratio'] = np.mean(returns) / np.std(returns) * np.sqrt(252)
        
        # Max drawdown calculation
        peak = equity_values[0]
        max_dd = 0
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)
        metrics['max_drawdown'] = max_dd
    
    # Trade statistics
    completed_trades = [t for t in trades if 'pnl' in t]
    if completed_trades:
        metrics['total_trades'] = len(completed_trades)
        
        # Win rate
        winning_trades = [t for t in completed_trades if t['pnl'] > 0]
        losing_trades = [t for t in completed_trades if t['pnl'] <= 0]
        metrics['win_rate'] = len(winning_trades) / len(completed_trades)
        
        # Average win/loss
        if winning_trades:
            metrics['avg_win'] = np.mean([t['pnl'] for t in winning_trades])
        if losing_trades:
            metrics['avg_loss'] = np.mean([abs(t['pnl']) for t in losing_trades])
        
        # Profit factor
        if losing_trades and metrics['avg_loss'] > 0:
            total_wins = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
            total_losses = sum(abs(t['pnl']) for t in losing_trades)
            metrics['profit_factor'] = total_wins / total_losses if total_losses > 0 else 0
    
    return metrics