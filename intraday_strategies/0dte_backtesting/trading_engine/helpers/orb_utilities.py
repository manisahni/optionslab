"""
Helper functions for ORB strategy analysis with timezone handling
"""
import pandas as pd
from datetime import datetime, timedelta
from trading_engine.strategies.opening_range_breakout import ORBStrategy

def test_orb_strategy(df, timeframe_minutes=15, days=30):
    """
    Test ORB strategy for the last N days
    
    Args:
        df: SPY DataFrame with 'date' column
        timeframe_minutes: ORB timeframe (5, 15, or 30)
        days: Number of days to backtest
        
    Returns:
        Dict with results and statistics
    """
    # Get the latest date in the data
    latest_date = df['date'].max()
    
    # Calculate start date (handle timezone)
    if df['date'].dt.tz is not None:
        # If data is timezone-aware, create timezone-aware start date
        start_date = latest_date - pd.Timedelta(days=days)
    else:
        # If data is timezone-naive, use naive datetime
        start_date = latest_date - timedelta(days=days)
    
    # Filter data for the date range
    filtered_df = df[df['date'] > start_date].copy()
    
    # Initialize ORB strategy
    orb = ORBStrategy(timeframe_minutes=timeframe_minutes)
    
    # Run backtest
    results = orb.backtest(filtered_df)
    
    # Calculate statistics
    stats = orb.calculate_statistics(results)
    
    return {
        'results_df': results,
        'stats': stats,
        'date_range': {
            'start': filtered_df['date'].min(),
            'end': filtered_df['date'].max(),
            'days': len(results)
        }
    }

def format_orb_results(stats):
    """Format ORB statistics for display"""
    return f"""
ORB Strategy Results:
- Total Days: {stats['total_days']}
- Breakout Days: {stats['breakout_days']} ({stats['breakout_rate']:.1%})
- Win Rate: {stats['win_rate']:.1%}
- Average Win: ${stats['avg_win']:.2f} ({stats.get('avg_win_pct', 0):.2f}%)
- Average Loss: ${stats['avg_loss']:.2f} ({stats.get('avg_loss_pct', 0):.2f}%)
- Profit Factor: {stats['profit_factor']:.2f}
- Total P&L: ${stats['total_pnl']:.2f}
- Sharpe Ratio: {stats['sharpe_ratio']:.2f}
"""