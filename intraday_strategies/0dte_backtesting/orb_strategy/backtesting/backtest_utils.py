"""
Utility functions for ORB backtesting
Shared functions for analysis and reporting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_drawdown_metrics(trades_df: pd.DataFrame, 
                              initial_capital: float = 15000) -> Dict:
    """
    Calculate comprehensive drawdown metrics
    
    Args:
        trades_df: DataFrame with trade results
        initial_capital: Starting capital assumption
        
    Returns:
        Dict with drawdown metrics
    """
    # Calculate cumulative P&L
    trades_df = trades_df.copy()
    trades_df['cumulative_pnl'] = trades_df['net_pnl'].cumsum()
    
    # Running capital
    trades_df['running_capital'] = initial_capital + trades_df['cumulative_pnl']
    
    # Calculate drawdown
    running_max = trades_df['cumulative_pnl'].expanding().max()
    drawdown_dollars = trades_df['cumulative_pnl'] - running_max
    
    # Percentage drawdown (from peak)
    peak_capital = initial_capital + running_max
    drawdown_pct_peak = (drawdown_dollars / peak_capital) * 100
    
    # Percentage drawdown (from initial)
    drawdown_pct_initial = (drawdown_dollars / initial_capital) * 100
    
    # Find max drawdown
    max_dd_dollars = drawdown_dollars.min()
    max_dd_idx = drawdown_dollars.idxmin()
    max_dd_date = trades_df.loc[max_dd_idx, 'date'] if max_dd_idx is not None else None
    
    # Recovery metrics
    if max_dd_idx is not None:
        # Find recovery point
        post_dd = trades_df.loc[max_dd_idx:]
        recovery_mask = post_dd['cumulative_pnl'] >= running_max[max_dd_idx]
        
        if recovery_mask.any():
            recovery_idx = recovery_mask.idxmax()
            recovery_trades = recovery_idx - max_dd_idx
            recovery_date = trades_df.loc[recovery_idx, 'date']
        else:
            recovery_trades = None
            recovery_date = None
    else:
        recovery_trades = None
        recovery_date = None
    
    # Calculate consecutive losses
    trades_df['is_loss'] = trades_df['net_pnl'] < 0
    
    # Group consecutive losses
    loss_groups = []
    current_streak = 0
    
    for is_loss in trades_df['is_loss']:
        if is_loss:
            current_streak += 1
        else:
            if current_streak > 0:
                loss_groups.append(current_streak)
            current_streak = 0
    
    if current_streak > 0:
        loss_groups.append(current_streak)
    
    max_consecutive_losses = max(loss_groups) if loss_groups else 0
    
    # Total return
    total_return = trades_df['cumulative_pnl'].iloc[-1] if len(trades_df) > 0 else 0
    total_return_pct = (total_return / initial_capital) * 100
    
    return {
        'initial_capital': initial_capital,
        'final_capital': initial_capital + total_return,
        'total_return': total_return,
        'total_return_pct': total_return_pct,
        'max_drawdown_dollars': max_dd_dollars,
        'max_drawdown_pct_peak': drawdown_pct_peak.min(),
        'max_drawdown_pct_initial': drawdown_pct_initial.min(),
        'max_drawdown_date': max_dd_date,
        'recovery_trades': recovery_trades,
        'recovery_date': recovery_date,
        'max_consecutive_losses': max_consecutive_losses,
        'avg_consecutive_losses': np.mean(loss_groups) if loss_groups else 0
    }


def calculate_performance_metrics(trades_df: pd.DataFrame) -> Dict:
    """
    Calculate comprehensive performance metrics
    
    Args:
        trades_df: DataFrame with trade results
        
    Returns:
        Dict with performance metrics
    """
    if len(trades_df) == 0:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0
        }
    
    # Basic metrics
    winning_trades = trades_df[trades_df['net_pnl'] > 0]
    losing_trades = trades_df[trades_df['net_pnl'] <= 0]
    
    total_trades = len(trades_df)
    win_rate = len(winning_trades) / total_trades * 100
    
    # P&L metrics
    total_pnl = trades_df['net_pnl'].sum()
    avg_pnl = trades_df['net_pnl'].mean()
    avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0
    
    # Profit factor
    total_wins = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
    total_losses = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 1
    profit_factor = total_wins / total_losses
    
    # Risk/Reward ratio
    if avg_loss != 0:
        risk_reward = abs(avg_win / avg_loss)
    else:
        risk_reward = 0
    
    # Sharpe ratio (simplified - daily)
    if len(trades_df) > 1:
        trades_df = trades_df.copy()
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        daily_pnl = trades_df.groupby(trades_df['date'].dt.date)['net_pnl'].sum()
        
        if len(daily_pnl) > 1 and daily_pnl.std() > 0:
            sharpe_ratio = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0
    else:
        sharpe_ratio = 0
    
    # Expectancy
    expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
    
    # Kelly Criterion
    if avg_loss != 0:
        kelly_pct = ((win_rate/100) * risk_reward - (1 - win_rate/100)) / risk_reward * 100
    else:
        kelly_pct = 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_win': trades_df['net_pnl'].max(),
        'max_loss': trades_df['net_pnl'].min(),
        'profit_factor': profit_factor,
        'risk_reward': risk_reward,
        'sharpe_ratio': sharpe_ratio,
        'expectancy': expectancy,
        'kelly_pct': kelly_pct
    }


def compare_with_option_alpha() -> pd.DataFrame:
    """
    Get Option Alpha benchmark results for comparison
    
    Returns:
        DataFrame with Option Alpha results
    """
    oa_results = pd.DataFrame([
        {
            'Timeframe': '15-min',
            'Win Rate': 78.1,
            'Avg P&L': 35,
            'Total P&L': 19053,
            'Profit Factor': 1.17,
            'Total Trades': 544  # Estimated from total P&L / avg P&L
        },
        {
            'Timeframe': '30-min',
            'Win Rate': 82.6,
            'Avg P&L': 31,
            'Total P&L': 19555,
            'Profit Factor': 1.19,
            'Total Trades': 631
        },
        {
            'Timeframe': '60-min',
            'Win Rate': 88.8,
            'Avg P&L': 51,
            'Total P&L': 30708,
            'Profit Factor': 1.59,
            'Total Trades': 602
        }
    ])
    
    return oa_results


def format_currency(value: float) -> str:
    """Format value as currency"""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"-${abs(value):,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format value as percentage"""
    return f"{value:.{decimals}f}%"


def spy_vs_spx_explanation() -> str:
    """
    Return explanation of SPY vs SPX differences
    
    Returns:
        String with formatted explanation
    """
    return """
SPY vs SPX - KEY DIFFERENCES:

SPY (SPDR S&P 500 ETF) - What We Used:
• ETF that tracks S&P 500 index
• Price: ~1/10th of SPX (e.g., $560)
• Contract size: 100 shares (~$56K notional)
• Options: American-style (can exercise early)
• Settlement: Physical shares
• Bid/Ask: Tighter spreads, more liquid
• Tax: Regular income treatment
• Best for: Retail traders, smaller accounts

SPX (S&P 500 Index):
• The actual index (not directly tradeable)
• Price: Full index value (e.g., 5600)
• Contract size: $100 × index (~$560K notional)
• Options: European-style (exercise at expiration only)
• Settlement: Cash-settled
• Bid/Ask: Wider spreads
• Tax: 60/40 long-term/short-term treatment
• Best for: Institutions, large accounts

Why We Used SPY:
1. Data availability (SPY 0DTE options)
2. Better for retail account sizes
3. Tighter bid/ask spreads
4. Easier position management
5. More liquid options market

Note: The ORB strategy works identically on both, 
but SPX requires ~10x larger account size.
"""


def calculate_rolling_metrics(trades_df: pd.DataFrame, windows: List[int] = [10, 20, 50]) -> Dict:
    """
    Calculate rolling window performance metrics
    
    Args:
        trades_df: DataFrame with trade results
        windows: List of rolling window sizes
        
    Returns:
        Dict with rolling metrics for each window
    """
    if len(trades_df) == 0:
        return {}
    
    rolling_metrics = {}
    
    for window in windows:
        if len(trades_df) >= window:
            # Get last N trades
            recent_trades = trades_df.tail(window).copy()
            
            # Calculate metrics
            win_rate = (recent_trades['net_pnl'] > 0).mean() * 100
            total_pnl = recent_trades['net_pnl'].sum()
            avg_pnl = recent_trades['net_pnl'].mean()
            
            # Count consecutive losses
            losses = (recent_trades['net_pnl'] < 0).astype(int)
            max_consecutive = losses.groupby((losses != losses.shift()).cumsum()).sum().max()
            
            rolling_metrics[f'last_{window}'] = {
                'trades': window,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'max_consecutive_losses': max_consecutive
            }
    
    return rolling_metrics


def detect_strategy_degradation(trades_df: pd.DataFrame, baseline_win_rate: float = 89.0) -> Dict:
    """
    Detect signs of strategy degradation
    
    Args:
        trades_df: DataFrame with trade results
        baseline_win_rate: Historical baseline win rate
        
    Returns:
        Dict with degradation signals and alerts
    """
    alerts = []
    status = 'GREEN'
    
    if len(trades_df) == 0:
        return {'status': 'NO_DATA', 'alerts': ['No trades to analyze']}
    
    # Get rolling metrics
    rolling = calculate_rolling_metrics(trades_df, [10, 20, 50])
    
    # Check 10-trade rule
    if 'last_10' in rolling:
        win_rate_10 = rolling['last_10']['win_rate']
        if win_rate_10 < 70:
            alerts.append(f'🔴 CRITICAL: Last 10 trades win rate {win_rate_10:.1f}% < 70%')
            status = 'RED'
        elif win_rate_10 < 80:
            alerts.append(f'🟡 WARNING: Last 10 trades win rate {win_rate_10:.1f}% < 80%')
            if status == 'GREEN':
                status = 'YELLOW'
    
    # Check 20-trade performance
    if 'last_20' in rolling:
        win_rate_20 = rolling['last_20']['win_rate']
        if win_rate_20 < 75:
            alerts.append(f'🔴 Last 20 trades win rate {win_rate_20:.1f}% < 75%')
            status = 'RED'
        elif win_rate_20 < 85:
            alerts.append(f'🟡 Last 20 trades win rate {win_rate_20:.1f}% < 85%')
            if status == 'GREEN':
                status = 'YELLOW'
    
    # Check consecutive losses
    if len(trades_df) >= 10:
        recent_losses = (trades_df.tail(10)['net_pnl'] < 0).astype(int)
        consecutive = recent_losses.groupby((recent_losses != recent_losses.shift()).cumsum()).sum().max()
        
        if consecutive >= 3:
            alerts.append(f'🔴 CRITICAL: {consecutive} consecutive losses (max historical: 2)')
            status = 'RED'
    
    # Check average loss size
    losses = trades_df[trades_df['net_pnl'] < 0]
    if len(losses) >= 5:
        recent_avg_loss = losses.tail(5)['net_pnl'].mean()
        historical_avg_loss = losses['net_pnl'].mean()
        
        if abs(recent_avg_loss) > abs(historical_avg_loss) * 1.5:
            alerts.append(f'🟡 Average loss increased: ${recent_avg_loss:.2f} vs ${historical_avg_loss:.2f}')
            if status == 'GREEN':
                status = 'YELLOW'
    
    # Check weekly performance (last 5 trading days)
    if len(trades_df) >= 5:
        last_week = trades_df.tail(5)
        week_pnl = last_week['net_pnl'].sum()
        if week_pnl < -100:
            alerts.append(f'🟡 Negative week: ${week_pnl:.2f}')
            if status == 'GREEN':
                status = 'YELLOW'
    
    # Standard deviation check
    if len(trades_df) >= 50:
        historical_wr = (trades_df['net_pnl'] > 0).mean() * 100
        std_wr = np.sqrt(historical_wr * (100 - historical_wr) / 50)
        
        if 'last_20' in rolling:
            current_wr = rolling['last_20']['win_rate']
            z_score = (current_wr - baseline_win_rate) / std_wr
            
            if z_score < -3:
                alerts.append(f'📊 Win rate >3 std devs below baseline')
                status = 'RED'
            elif z_score < -2:
                alerts.append(f'📊 Win rate 2-3 std devs below baseline')
                if status == 'GREEN':
                    status = 'YELLOW'
    
    if not alerts:
        alerts.append('✅ All metrics within normal range')
    
    return {
        'status': status,
        'alerts': alerts,
        'rolling_metrics': rolling
    }


def generate_health_alerts(degradation_results: Dict) -> List[str]:
    """
    Generate actionable health alerts and recommendations
    
    Args:
        degradation_results: Results from detect_strategy_degradation
        
    Returns:
        List of actionable recommendations
    """
    recommendations = []
    status = degradation_results['status']
    
    if status == 'GREEN':
        recommendations.append('✅ Continue trading normally')
        recommendations.append('📊 Monitor daily for changes')
        
    elif status == 'YELLOW':
        recommendations.append('⚠️ INVESTIGATE immediately')
        recommendations.append('📝 Review recent losing trades for patterns')
        recommendations.append('🔍 Check for market structure changes')
        recommendations.append('📉 Consider reducing position size by 50%')
        recommendations.append('🧪 Run paper trades in parallel')
        
    elif status == 'RED':
        recommendations.append('🛑 STOP TRADING IMMEDIATELY')
        recommendations.append('📊 Conduct full strategy review')
        recommendations.append('🔍 Analyze market microstructure changes')
        recommendations.append('📝 Document all recent anomalies')
        recommendations.append('🧪 Paper trade for 20 trades before resuming')
    
    # Add specific checks
    recommendations.append('\nDaily Monitoring Checklist:')
    recommendations.append('□ Check opening range size (normal: $2-6)')
    recommendations.append('□ Monitor breakout timing (normal: before noon)')
    recommendations.append('□ Verify credit received (normal: $30-50)')
    recommendations.append('□ Check bid/ask spreads (normal: <$0.05)')
    recommendations.append('□ Review false breakout frequency')
    
    return recommendations


def calculate_monthly_performance(trades_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate monthly performance statistics
    
    Args:
        trades_df: DataFrame with trade results
        
    Returns:
        DataFrame with monthly statistics
    """
    trades_df = trades_df.copy()
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    trades_df['month'] = trades_df['date'].dt.to_period('M')
    
    monthly_stats = trades_df.groupby('month').agg({
        'net_pnl': ['count', 'sum', 'mean'],
        'entry_credit': 'mean'
    }).round(2)
    
    # Calculate win rate per month
    win_rates = trades_df.groupby('month').apply(
        lambda x: (x['net_pnl'] > 0).mean() * 100
    )
    
    monthly_stats.columns = ['Trades', 'Total_PnL', 'Avg_PnL', 'Avg_Credit']
    monthly_stats['Win_Rate'] = win_rates
    
    return monthly_stats


def identify_best_worst_days(trades_df: pd.DataFrame, n: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identify best and worst trading days
    
    Args:
        trades_df: DataFrame with trade results
        n: Number of days to return
        
    Returns:
        Tuple of (best_days, worst_days) DataFrames
    """
    trades_df = trades_df.copy()
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    
    # Group by date
    daily_pnl = trades_df.groupby(trades_df['date'].dt.date).agg({
        'net_pnl': 'sum',
        'direction': 'first',
        'entry_credit': 'mean'
    }).round(2)
    
    # Get best and worst
    best_days = daily_pnl.nlargest(n, 'net_pnl')
    worst_days = daily_pnl.nsmallest(n, 'net_pnl')
    
    return best_days, worst_days