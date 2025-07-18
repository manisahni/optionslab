#!/usr/bin/env python3
"""
Simple backtesting engine for options strategies
Provides the core functions needed by the FastAPI backend
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from pathlib import Path

def load_spy_data(start_date, end_date):
    """
    Load SPY options data for the specified date range
    This is a simplified version - in production you'd load from your data source
    """
    # For now, generate synthetic data for demonstration
    # In a real implementation, you'd load from your parquet files
    
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Generate synthetic SPY price data
    np.random.seed(42)  # For reproducible results
    spy_prices = []
    current_price = 450.0
    
    for date in date_range:
        # Random walk with slight upward bias
        change = np.random.normal(0.001, 0.02)  # 0.1% daily return, 2% volatility
        current_price *= (1 + change)
        spy_prices.append({
            'date': date,
            'spy_price': current_price,
            'volume': np.random.randint(1000000, 5000000)
        })
    
    return pd.DataFrame(spy_prices)

def calculate_option_price(spot_price, strike, time_to_expiry, volatility, risk_free_rate, option_type='call'):
    """
    Simple Black-Scholes option pricing (simplified)
    """
    # Simplified option pricing for demonstration
    # In production, use a proper options pricing library
    
    if option_type == 'call':
        intrinsic_value = max(0, spot_price - strike)
    else:  # put
        intrinsic_value = max(0, strike - spot_price)
    
    # Add some time value (simplified)
    time_value = spot_price * 0.02 * (time_to_expiry / 365)  # 2% annual time value
    
    return intrinsic_value + time_value

def run_backtest(strategy_type, start_date, end_date, initial_capital=100000):
    """
    Run a backtest for the specified strategy and parameters
    
    Args:
        strategy_type: 'long_call' or 'long_put'
        start_date: Start date as string (YYYY-MM-DD)
        end_date: End date as string (YYYY-MM-DD)
        initial_capital: Initial capital amount
    
    Returns:
        dict: Backtest results with performance metrics and trade data
    """
    
    # Load market data
    spy_data = load_spy_data(start_date, end_date)
    
    if spy_data.empty:
        return None
    
    # Initialize portfolio
    cash = initial_capital
    positions = []
    equity_curve = []
    trade_logs = []
    
    # Strategy parameters
    position_size = 0.1  # 10% of capital per trade
    dte_target = 30  # Days to expiration target
    delta_target = 0.4 if strategy_type == 'long_call' else -0.4
    
    # Simulate trading
    for i, row in spy_data.iterrows():
        current_date = row['date']
        spy_price = row['spy_price']
        
        # Simple entry logic (every 5 days for demonstration)
        if i % 5 == 0 and len(positions) == 0:
            # Enter a new position
            strike = spy_price * 1.02 if strategy_type == 'long_call' else spy_price * 0.98
            option_price = calculate_option_price(
                spy_price, strike, dte_target, 0.2, 0.05, 
                'call' if strategy_type == 'long_call' else 'put'
            )
            
            # Calculate position size
            max_loss = option_price * 100  # $100 per contract
            contracts = int((cash * position_size) / max_loss)
            
            if contracts > 0:
                cost = contracts * option_price * 100
                if cost <= cash:
                    positions.append({
                        'entry_date': current_date,
                        'entry_price': option_price,
                        'strike': strike,
                        'contracts': contracts,
                        'option_type': 'call' if strategy_type == 'long_call' else 'put'
                    })
                    cash -= cost
                    
                    trade_logs.append({
                        'entry_date': current_date.strftime('%Y-%m-%d'),
                        'exit_date': None,
                        'option_type': 'call' if strategy_type == 'long_call' else 'put',
                        'strike': strike,
                        'quantity': contracts,
                        'entry_price': option_price,
                        'exit_price': None,
                        'pnl': None,
                        'exit_reason': None
                    })
        
        # Simple exit logic (hold for 5 days)
        for pos in positions[:]:  # Copy list to avoid modification during iteration
            days_held = (current_date - pos['entry_date']).days
            if days_held >= 5:
                # Exit position
                current_option_price = calculate_option_price(
                    spy_price, pos['strike'], max(1, dte_target - days_held), 0.2, 0.05,
                    pos['option_type']
                )
                
                proceeds = pos['contracts'] * current_option_price * 100
                cash += proceeds
                
                pnl = proceeds - (pos['contracts'] * pos['entry_price'] * 100)
                
                # Update trade log
                for trade in trade_logs:
                    if (trade['entry_date'] == pos['entry_date'].strftime('%Y-%m-%d') and 
                        trade['exit_date'] is None):
                        trade['exit_date'] = current_date.strftime('%Y-%m-%d')
                        trade['exit_price'] = current_option_price
                        trade['pnl'] = pnl
                        trade['exit_reason'] = 'time_exit'
                        break
                
                positions.remove(pos)
        
        # Calculate current portfolio value
        position_value = sum(
            pos['contracts'] * calculate_option_price(
                spy_price, pos['strike'], max(1, dte_target - (current_date - pos['entry_date']).days), 
                0.2, 0.05, pos['option_type']
            ) * 100 for pos in positions
        )
        
        total_value = cash + position_value
        
        equity_curve.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'cash': cash,
            'total_value': total_value,
            'positions': len(positions)
        })
    
    # Close any remaining positions
    final_spy_price = spy_data.iloc[-1]['spy_price']
    for pos in positions:
        current_option_price = calculate_option_price(
            final_spy_price, pos['strike'], 1, 0.2, 0.05, pos['option_type']
        )
        proceeds = pos['contracts'] * current_option_price * 100
        cash += proceeds
        
        pnl = proceeds - (pos['contracts'] * pos['entry_price'] * 100)
        
        # Update trade log
        for trade in trade_logs:
            if trade['exit_date'] is None:
                trade['exit_date'] = end_date
                trade['exit_price'] = current_option_price
                trade['pnl'] = pnl
                trade['exit_reason'] = 'end_of_period'
                break
    
    # Calculate performance metrics
    final_value = cash
    total_return = (final_value - initial_capital) / initial_capital
    
    # Calculate additional metrics
    equity_values = [point['total_value'] for point in equity_curve]
    returns = np.diff(equity_values) / equity_values[:-1]
    
    if len(returns) > 0:
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Calculate max drawdown
        peak = equity_values[0]
        max_drawdown = 0
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
    else:
        sharpe_ratio = 0
        max_drawdown = 0
    
    # Calculate win rate
    completed_trades = [trade for trade in trade_logs if trade['exit_date'] is not None]
    winning_trades = [trade for trade in completed_trades if trade['pnl'] > 0]
    win_rate = len(winning_trades) / len(completed_trades) if completed_trades else 0
    
    return {
        'metadata': {
            'strategy': strategy_type,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital
        },
        'performance_metrics': {
            'final_value': final_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(completed_trades)
        },
        'equity_curve': equity_curve,
        'trade_logs': trade_logs
    }

def plot_results(results, save_path=None):
    """
    Create and optionally save a plot of the backtest results
    
    Args:
        results: Backtest results dictionary
        save_path: Optional path to save the plot
    """
    if not results:
        return
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot 1: Equity Curve
    equity_data = pd.DataFrame(results['equity_curve'])
    equity_data['date'] = pd.to_datetime(equity_data['date'])
    
    ax1.plot(equity_data['date'], equity_data['total_value'], linewidth=2, color='blue')
    ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # Add initial capital line
    initial_capital = results['metadata']['initial_capital']
    ax1.axhline(y=initial_capital, color='red', linestyle='--', alpha=0.7, label=f'Initial Capital: ${initial_capital:,.0f}')
    ax1.legend()
    
    # Plot 2: Trade P&L
    trade_logs = results['trade_logs']
    completed_trades = [trade for trade in trade_logs if trade['exit_date'] is not None and trade['pnl'] is not None]
    
    if completed_trades:
        trade_pnls = [trade['pnl'] for trade in completed_trades]
        trade_numbers = list(range(1, len(completed_trades) + 1))
        
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
        ax2.bar(trade_numbers, trade_pnls, color=colors, alpha=0.7)
        ax2.set_title('Trade P&L', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Trade Number', fontsize=12)
        ax2.set_ylabel('P&L ($)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Add zero line
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {save_path}")
    
    return fig 