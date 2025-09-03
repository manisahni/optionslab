"""
Research Utilities Module - Daily OptionsLab
============================================
Project-specific research functions that build on shared trading_utils.
"""

import sys
sys.path.append('/Users/nish_macbook/trading')

# Import shared utilities
from trading_utils import (
    check_missing_dates,
    validate_strike_range,
    check_strike_format,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_win_rate
)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


def validate_options_data(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Validate and clean options data using shared utilities.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Raw options data
    verbose : bool
        Print validation results
        
    Returns:
    --------
    pd.DataFrame
        Cleaned and validated dataframe
    """
    df = df.copy()
    issues = []
    
    # Use shared function to check strike format
    strike_format = check_strike_format(df)
    if strike_format == 'cents':
        issues.append("Strikes in cents - converting to dollars")
        df['strike'] = df['strike'] / 1000
    
    # Date columns
    date_cols = ['date', 'expiration']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    # Calculate DTE if not present
    if 'dte' not in df.columns and 'expiration' in df.columns and 'date' in df.columns:
        df['dte'] = (df['expiration'] - df['date']).dt.days
    
    # Calculate mid price if not present
    if 'mid_price' not in df.columns and 'bid' in df.columns and 'ask' in df.columns:
        df['mid_price'] = (df['bid'] + df['ask']) / 2
    
    # Data quality checks
    zero_bids = (df['bid'] == 0).sum()
    negative_prices = ((df['bid'] < 0) | (df['ask'] < 0)).sum()
    
    if zero_bids > len(df) * 0.5:
        issues.append(f"High proportion of zero bids: {zero_bids/len(df)*100:.1f}%")
    
    if negative_prices > 0:
        issues.append(f"Found {negative_prices} negative prices - removing")
        df = df[(df['bid'] >= 0) & (df['ask'] >= 0)]
    
    # Use shared function for missing dates (holiday-aware)
    missing_dates = check_missing_dates(df)
    if len(missing_dates) > 0:
        issues.append(f"Missing {len(missing_dates)} trading days")
    
    # Use shared function for strike validation
    outlier_strikes = validate_strike_range(df, buffer=0.5)
    if len(outlier_strikes) > len(df) * 0.01:
        issues.append(f"{len(outlier_strikes)} strikes far from underlying price")
    
    if verbose:
        print("DATA VALIDATION REPORT")
        print("=" * 50)
        print(f"Records: {len(df):,}")
        print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        print(f"Strike range: ${df['strike'].min():.0f} - ${df['strike'].max():.0f}")
        
        if issues:
            print("\nIssues found and addressed:")
            for issue in issues:
                print(f"  ⚠️  {issue}")
        else:
            print("✓ No major issues found")
    
    return df


def load_spy_data(years: List[int], data_path: str = 'daily_strategies/data/spy_options/') -> pd.DataFrame:
    """
    Load and validate SPY options data for specified years.
    
    Parameters:
    -----------
    years : List[int]
        Years to load (e.g., [2023, 2024])
    data_path : str
        Path to data directory
        
    Returns:
    --------
    pd.DataFrame
        Combined and validated data
    """
    dfs = []
    
    for year in years:
        try:
            df_year = pd.read_parquet(f'{data_path}SPY_OPTIONS_{year}_COMPLETE.parquet')
            dfs.append(df_year)
            print(f"✓ Loaded {year}: {len(df_year):,} records")
        except FileNotFoundError:
            print(f"✗ {year} data not found")
    
    if not dfs:
        raise ValueError("No data loaded! Check years and data path.")
    
    df = pd.concat(dfs, ignore_index=True)
    df = validate_options_data(df)
    
    return df


def calculate_performance_metrics(portfolio_values: pd.Series, 
                                 initial_capital: float = 10000) -> Dict[str, float]:
    """
    Calculate performance metrics using shared utilities.
    
    Parameters:
    -----------
    portfolio_values : pd.Series
        Time series of portfolio values
    initial_capital : float
        Starting capital
        
    Returns:
    --------
    Dict[str, float]
        Dictionary of performance metrics
    """
    metrics = {}
    
    # Basic returns
    total_return = (portfolio_values.iloc[-1] - initial_capital) / initial_capital * 100
    metrics['total_return'] = total_return
    metrics['final_value'] = portfolio_values.iloc[-1]
    
    # Daily returns
    daily_returns = portfolio_values.pct_change().dropna()
    
    if len(daily_returns) > 1:
        # Use shared functions for standard metrics
        metrics['sharpe'] = calculate_sharpe_ratio(daily_returns)
        metrics['sortino'] = calculate_sortino_ratio(daily_returns)
        metrics['max_drawdown'] = calculate_max_drawdown(portfolio_values)
        metrics['win_rate'] = calculate_win_rate(daily_returns)
        
        # Additional metrics specific to this project
        metrics['volatility'] = daily_returns.std() * np.sqrt(252) * 100
        metrics['best_day'] = daily_returns.max() * 100
        metrics['worst_day'] = daily_returns.min() * 100
    else:
        # Set defaults if not enough data
        for key in ['sharpe', 'sortino', 'max_drawdown', 'volatility', 'win_rate', 'best_day', 'worst_day']:
            metrics[key] = 0
    
    return metrics


def create_comparison_chart(results_dict: Dict[str, pd.DataFrame], 
                          title: str = "Strategy Comparison",
                          initial_capital: float = 10000) -> go.Figure:
    """
    Create a comparison chart for multiple strategies.
    
    Parameters:
    -----------
    results_dict : Dict[str, pd.DataFrame]
        Dictionary of strategy names to results dataframes
        Each dataframe should have 'date' and 'total_value' columns
    title : str
        Chart title
    initial_capital : float
        Initial capital for reference line
        
    Returns:
    --------
    go.Figure
        Plotly figure object
    """
    fig = go.Figure()
    
    colors = ['green', 'blue', 'red', 'purple', 'orange', 'brown']
    
    for i, (name, df) in enumerate(results_dict.items()):
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['total_value'],
            mode='lines',
            name=name,
            line=dict(color=color, width=2)
        ))
    
    # Add initial capital reference line
    fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray", 
                  annotation_text="Initial Capital")
    
    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Portfolio Value ($)',
        hovermode='x unified',
        height=500,
        yaxis=dict(tickformat='$,.0f'),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    return fig


def analyze_trades(trades_df: pd.DataFrame) -> Dict[str, any]:
    """
    Analyze a dataframe of trades for key statistics.
    
    Parameters:
    -----------
    trades_df : pd.DataFrame
        Dataframe with trade information
        Should have columns: 'profit', 'entry_date', 'exit_date'
        
    Returns:
    --------
    Dict[str, any]
        Trade statistics
    """
    if len(trades_df) == 0:
        return {'total_trades': 0}
    
    stats = {}
    
    # Basic counts
    stats['total_trades'] = len(trades_df)
    
    if 'profit' in trades_df.columns:
        stats['winning_trades'] = (trades_df['profit'] > 0).sum()
        stats['losing_trades'] = (trades_df['profit'] < 0).sum()
        stats['win_rate'] = stats['winning_trades'] / stats['total_trades'] * 100
        
        stats['avg_profit'] = trades_df['profit'].mean()
        stats['total_profit'] = trades_df['profit'].sum()
        stats['best_trade'] = trades_df['profit'].max()
        stats['worst_trade'] = trades_df['profit'].min()
        
        # Profit factor
        wins = trades_df[trades_df['profit'] > 0]['profit'].sum()
        losses = abs(trades_df[trades_df['profit'] < 0]['profit'].sum())
        stats['profit_factor'] = wins / losses if losses > 0 else np.inf
    
    # Trade duration if dates available
    if 'entry_date' in trades_df.columns and 'exit_date' in trades_df.columns:
        trades_df['duration'] = (trades_df['exit_date'] - trades_df['entry_date']).dt.days
        stats['avg_duration'] = trades_df['duration'].mean()
        stats['max_duration'] = trades_df['duration'].max()
        stats['min_duration'] = trades_df['duration'].min()
    
    return stats


def print_metrics_comparison(metrics_dict: Dict[str, Dict[str, float]]):
    """
    Print a formatted comparison of metrics across strategies.
    
    Parameters:
    -----------
    metrics_dict : Dict[str, Dict[str, float]]
        Dictionary of strategy names to metrics dictionaries
    """
    # Get all unique metrics
    all_metrics = set()
    for metrics in metrics_dict.values():
        all_metrics.update(metrics.keys())
    
    # Define display order and formatting
    metric_order = [
        ('total_return', 'Total Return', '.1f', '%'),
        ('sharpe', 'Sharpe Ratio', '.2f', ''),
        ('sortino', 'Sortino Ratio', '.2f', ''),
        ('max_drawdown', 'Max Drawdown', '.1f', '%'),
        ('volatility', 'Volatility', '.1f', '%'),
        ('win_rate', 'Win Rate', '.1f', '%'),
    ]
    
    # Print header
    strategies = list(metrics_dict.keys())
    print("\n" + "="*60)
    print("STRATEGY COMPARISON")
    print("="*60)
    
    # Column widths
    metric_width = 20
    value_width = 15
    
    # Print column headers
    header = f"{'Metric':<{metric_width}}"
    for strategy in strategies:
        header += f"{strategy:>{value_width}}"
    print(header)
    print("-" * (metric_width + value_width * len(strategies)))
    
    # Print metrics
    for metric_key, metric_name, fmt, suffix in metric_order:
        if metric_key in all_metrics:
            row = f"{metric_name:<{metric_width}}"
            for strategy in strategies:
                value = metrics_dict[strategy].get(metric_key, 0)
                formatted = f"{value:{fmt}}{suffix}"
                row += f"{formatted:>{value_width}}"
            print(row)


def quarterly_analysis(df: pd.DataFrame, strategy_func, initial_capital: float = 10000) -> pd.DataFrame:
    """
    Run strategy analysis by quarter.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Options data
    strategy_func : callable
        Function that takes df and returns results
    initial_capital : float
        Starting capital for each period
        
    Returns:
    --------
    pd.DataFrame
        Quarterly performance summary
    """
    quarters = []
    
    # Group by year and quarter
    df['year'] = df['date'].dt.year
    df['quarter'] = df['date'].dt.quarter
    
    for (year, quarter), group in df.groupby(['year', 'quarter']):
        if len(group) < 20:  # Skip if too few days
            continue
            
        # Run strategy for this quarter
        results = strategy_func(group, initial_capital)
        
        if len(results) > 0:
            metrics = calculate_performance_metrics(results['total_value'], initial_capital)
            
            quarters.append({
                'period': f"Q{quarter} {year}",
                'start_date': group['date'].min(),
                'end_date': group['date'].max(),
                'days': len(results),
                'return': metrics['total_return'],
                'sharpe': metrics['sharpe'],
                'max_dd': metrics['max_drawdown'],
                'volatility': metrics['volatility']
            })
    
    return pd.DataFrame(quarters)


# Export all functions
__all__ = [
    'validate_options_data',
    'load_spy_data',
    'calculate_performance_metrics',
    'create_comparison_chart',
    'analyze_trades',
    'print_metrics_comparison',
    'quarterly_analysis'
]