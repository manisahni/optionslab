"""
Helper functions for all trading strategies
Makes it easy to test strategies with proper data handling
"""

import pandas as pd
import pytz
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

from ..strategies.vwap_reversion import VWAPBounceStrategy
from ..strategies.gap_momentum import GapAndGoStrategy

logger = logging.getLogger(__name__)


def test_vwap_bounce_strategy(df: pd.DataFrame, 
                             min_distance_pct: float = 0.1,
                             stop_loss_atr: float = 1.5,
                             target_atr: float = 2.0,
                             instrument_type: str = "options") -> Dict:
    """
    Test VWAP Bounce strategy with automatic timezone handling
    
    Args:
        df: DataFrame with minute bar data
        min_distance_pct: Min % distance from VWAP to trigger
        stop_loss_atr: Stop loss in ATR multiples
        target_atr: Target in ATR multiples
        instrument_type: "stock", "options", or "futures"
        
    Returns:
        Dict with results_df and statistics
    """
    # Ensure timezone awareness
    eastern = pytz.timezone('US/Eastern')
    
    # Check if index is DatetimeIndex and handle timezone
    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is None:
            df.index = df.index.tz_localize(eastern)
        elif df.index.tz != eastern:
            df.index = df.index.tz_convert(eastern)
    else:
        # If index is not DatetimeIndex, try to convert it
        try:
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize(eastern)
        except Exception as e:
            logger.warning(f"Could not convert index to datetime: {e}")
            # If conversion fails, assume data is already in correct timezone
            pass
    
    start_date = df.index[0]
    end_date = df.index[-1]
    
    # Create strategy instance
    strategy = VWAPBounceStrategy(
        min_distance_pct=min_distance_pct,
        stop_loss_atr=stop_loss_atr,
        target_atr=target_atr,
        instrument_type=instrument_type
    )
    
    logger.info(f"VWAP Bounce: Testing with df shape={df.shape}, start_date={start_date}, end_date={end_date}")
    
    # Run backtest
    results_df = strategy.backtest(df, start_date=start_date, end_date=end_date)
    
    logger.info(f"VWAP Bounce: Results shape={results_df.shape if not results_df.empty else 'empty'}")
    
    # Calculate statistics
    stats = strategy.calculate_statistics(results_df)
    
    return {
        'results_df': results_df,
        'stats': stats,
        'strategy_name': f'VWAP Bounce ({min_distance_pct}% distance)',
        'instrument_type': instrument_type
    }


def test_gap_and_go_strategy(df: pd.DataFrame,
                            min_gap_pct: float = 0.3,
                            confirmation_bars: int = 3,
                            stop_loss_pct: float = 0.5,
                            target_pct: float = 1.0,
                            time_stop_minutes: int = 120,
                            instrument_type: str = "options") -> Dict:
    """
    Test Gap and Go strategy with automatic timezone handling
    
    Args:
        df: DataFrame with minute bar data
        min_gap_pct: Minimum gap size to trade (%)
        confirmation_bars: Bars needed to confirm direction
        stop_loss_pct: Stop loss as % from entry
        target_pct: Target as % from entry
        time_stop_minutes: Max holding time
        instrument_type: "stock", "options", or "futures"
        
    Returns:
        Dict with results_df and statistics
    """
    # Ensure timezone awareness
    eastern = pytz.timezone('US/Eastern')
    
    # Check if index is DatetimeIndex and handle timezone
    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is None:
            df.index = df.index.tz_localize(eastern)
        elif df.index.tz != eastern:
            df.index = df.index.tz_convert(eastern)
    else:
        # If index is not DatetimeIndex, try to convert it
        try:
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize(eastern)
        except Exception as e:
            logger.warning(f"Could not convert index to datetime: {e}")
            # If conversion fails, assume data is already in correct timezone
            pass
    
    start_date = df.index[0]
    end_date = df.index[-1]
    
    # Create strategy instance
    strategy = GapAndGoStrategy(
        min_gap_pct=min_gap_pct,
        confirmation_bars=confirmation_bars,
        stop_loss_pct=stop_loss_pct,
        target_pct=target_pct,
        time_stop_minutes=time_stop_minutes,
        instrument_type=instrument_type
    )
    
    logger.info(f"VWAP Bounce: Testing with df shape={df.shape}, start_date={start_date}, end_date={end_date}")
    
    # Run backtest
    results_df = strategy.backtest(df, start_date=start_date, end_date=end_date)
    
    logger.info(f"VWAP Bounce: Results shape={results_df.shape if not results_df.empty else 'empty'}")
    
    # Calculate statistics
    stats = strategy.calculate_statistics(results_df)
    
    return {
        'results_df': results_df,
        'stats': stats,
        'strategy_name': f'Gap & Go ({min_gap_pct}% min gap)',
        'instrument_type': instrument_type
    }


def format_strategy_results(result: Dict) -> str:
    """
    Format strategy results in a readable text format
    """
    if not result or 'stats' not in result:
        return "❌ No results available"
    
    stats = result['stats']
    trades_df = result.get('results_df', pd.DataFrame())
    
    summary = f"""# {result.get('strategy_name', 'Strategy')} Results

## Performance Summary
- **Total Trades**: {stats.get('total_trades', 0)}
- **Win Rate**: {stats.get('win_rate', 0):.1%}
- **Total P&L**: ${stats.get('total_pnl', 0):,.2f}
- **Profit Factor**: {stats.get('profit_factor', 0):.2f}
- **Average Win**: ${stats.get('avg_win', 0):.2f}
- **Average Loss**: ${stats.get('avg_loss', 0):.2f}
- **Max Drawdown**: ${stats.get('max_drawdown', 0):,.2f}
- **Sharpe Ratio**: {stats.get('sharpe_ratio', 0):.2f}

## Recent Trades
"""
    
    if not trades_df.empty:
        recent_trades = trades_df.tail(5)
        for _, trade in recent_trades.iterrows():
            summary += f"- {trade.get('date', 'N/A')}: {trade.get('outcome', 'N/A')} (${trade.get('pnl', 0):.2f})\n"
    
    return summary


def compare_all_strategies(df: pd.DataFrame, 
                          days: int = 30,
                          instrument_type: str = "options") -> pd.DataFrame:
    """
    Compare all available strategies on the same dataset
    
    Args:
        df: DataFrame with minute bar data
        days: Number of days to test
        instrument_type: "stock", "options", or "futures"
        
    Returns:
        DataFrame with cumulative P&L for each strategy
    """
    # Ensure timezone awareness
    eastern = pytz.timezone('US/Eastern')
    
    # Check if index is DatetimeIndex and handle timezone
    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is None:
            df.index = df.index.tz_localize(eastern)
        elif df.index.tz != eastern:
            df.index = df.index.tz_convert(eastern)
    else:
        # If index is not DatetimeIndex, try to convert it
        try:
            df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize(eastern)
        except Exception as e:
            logger.warning(f"Could not convert index to datetime: {e}")
            # If conversion fails, assume data is already in correct timezone
            pass
    
    # Calculate date range if days is specified
    if days > 0:
        end_date = df.index[-1]
        start_date = end_date - timedelta(days=days)
        
        # Filter data for the period
        mask = (df.index >= start_date) & (df.index <= end_date)
        period_df = df[mask].copy()
    else:
        # Use all data
        period_df = df.copy()
    
    logger.info(f"Compare all strategies: days={days}, df shape={df.shape}, period_df shape={period_df.shape}")
    
    if period_df.empty:
        logger.warning(f"No data found for the selected period")
        return pd.DataFrame()
    
    # Test different ORB timeframes
    orb_results = {}
    for timeframe in [5, 15, 30, 60]:
        try:
            orb = ORBStrategy(
                timeframe_minutes=timeframe,
                instrument_type=instrument_type
            )
            results_df = orb.backtest(period_df)
            if not results_df.empty:
                # Overall cumulative P&L
                orb_results[f'ORB_{timeframe}min'] = results_df['pnl'].cumsum()
                
                # Split by direction if breakout_type column exists
                if 'breakout_type' in results_df.columns:
                    # Long trades
                    long_trades = results_df[results_df['breakout_type'] == 'long'].copy()
                    if not long_trades.empty:
                        long_trades['cumulative_pnl'] = long_trades['pnl'].cumsum()
                        orb_results[f'ORB_{timeframe}min_Long'] = long_trades.set_index(long_trades.index)['cumulative_pnl']
                    
                    # Short trades
                    short_trades = results_df[results_df['breakout_type'] == 'short'].copy()
                    if not short_trades.empty:
                        short_trades['cumulative_pnl'] = short_trades['pnl'].cumsum()
                        orb_results[f'ORB_{timeframe}min_Short'] = short_trades.set_index(short_trades.index)['cumulative_pnl']
        except Exception as e:
            logger.warning(f"Failed to test ORB {timeframe}min: {e}")
    
    # Test VWAP Bounce
    try:
        # Pass the filtered period_df (days parameter removed from function)
        vwap_result = test_vwap_bounce_strategy(period_df, instrument_type=instrument_type)
        if vwap_result and 'results_df' in vwap_result and not vwap_result['results_df'].empty:
            orb_results['VWAP_Bounce'] = vwap_result['results_df']['pnl'].cumsum()
        else:
            logger.warning(f"VWAP Bounce returned empty results. Result keys: {list(vwap_result.keys()) if vwap_result else 'None'}")
    except Exception as e:
        logger.error(f"Failed to test VWAP Bounce: {str(e)}", exc_info=True)
    
    # Test Gap and Go
    try:
        # Pass the filtered period_df (days parameter removed from function)
        gap_result = test_gap_and_go_strategy(period_df, instrument_type=instrument_type)
        if gap_result and 'results_df' in gap_result and not gap_result['results_df'].empty:
            orb_results['Gap_and_Go'] = gap_result['results_df']['pnl'].cumsum()
        else:
            logger.warning(f"Gap and Go returned empty results. Result keys: {list(gap_result.keys()) if gap_result else 'None'}")
    except Exception as e:
        logger.error(f"Failed to test Gap and Go: {str(e)}", exc_info=True)
    
    # Create comparison DataFrame
    if orb_results:
        comparison_df = pd.DataFrame(orb_results)
        comparison_df = comparison_df.ffill().fillna(0)
        return comparison_df
    else:
        logger.warning("No strategy results available for comparison")
        return pd.DataFrame()


# Import ORBStrategy here to avoid circular imports
try:
    from ..strategies.opening_range_breakout import ORBStrategy
except ImportError:
    try:
        from trading_engine.strategies.opening_range_breakout import ORBStrategy
    except ImportError:
        logger.warning("ORBStrategy not available for comparison")
        ORBStrategy = None