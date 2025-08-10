"""
Gap and Go Strategy Implementation for 0DTE Trading

This strategy trades opening gaps that continue in the direction of the gap.
It's based on the principle that significant overnight gaps often lead to
continued momentum in the gap direction during the first part of the trading day.

Strategy Logic:
1. Identify opening gap (>0.3% from previous close)
2. Wait for confirmation (price continues in gap direction)
3. Enter trade in direction of gap
4. Exit on momentum exhaustion or time stop
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class GapAndGoStrategy:
    """
    Gap and Go Strategy for intraday momentum trading
    
    Key Concepts:
    - Large gaps indicate overnight sentiment shift
    - Gaps often continue in the morning session
    - Volume confirms the gap strength
    - Best performance in first 2 hours of trading
    """
    
    def __init__(self,
                 min_gap_pct: float = 0.3,      # Minimum gap size to trade (0.3%)
                 confirmation_bars: int = 3,      # Bars to confirm direction
                 stop_loss_pct: float = 0.5,     # Stop loss as % of entry
                 target_pct: float = 1.0,        # Target as % of entry
                 time_stop_minutes: int = 120,    # Exit after N minutes
                 instrument_type: str = "options"):
        """
        Initialize Gap and Go strategy
        
        Args:
            min_gap_pct: Minimum gap size as percentage to consider
            confirmation_bars: Number of bars to confirm gap continuation
            stop_loss_pct: Stop loss as percentage from entry
            target_pct: Target as percentage from entry
            time_stop_minutes: Maximum time to hold position
            instrument_type: Type of instrument (stock/options/futures)
        """
        self.min_gap_pct = min_gap_pct / 100  # Convert to decimal
        self.confirmation_bars = confirmation_bars
        self.stop_loss_pct = stop_loss_pct / 100
        self.target_pct = target_pct / 100
        self.time_stop_minutes = time_stop_minutes
        self.instrument_type = instrument_type
        
        # Trading hours
        self.market_open = time(9, 30)
        self.market_close = time(16, 0)
        self.entry_cutoff = time(10, 30)  # Only enter in first hour
        
        # P&L multipliers
        self.pnl_multipliers = {
            "stock": 1.0,
            "options": 0.1,
            "futures": 2.0
        }
    
    def calculate_gap(self, prev_close: float, open_price: float) -> Tuple[float, str]:
        """
        Calculate gap size and direction
        
        Returns:
            (gap_pct, direction)
        """
        gap_pct = (open_price - prev_close) / prev_close
        direction = 'up' if gap_pct > 0 else 'down'
        
        return gap_pct, direction
    
    def check_gap_continuation(self, df_open: pd.DataFrame, gap_direction: str) -> bool:
        """
        Check if price continues in gap direction for confirmation
        
        Args:
            df_open: DataFrame starting from market open
            gap_direction: 'up' or 'down'
        
        Returns:
            True if gap continues, False otherwise
        """
        if len(df_open) < self.confirmation_bars:
            return False
        
        # Get confirmation period
        confirm_df = df_open.iloc[:self.confirmation_bars]
        
        if gap_direction == 'up':
            # For gap up, want to see higher highs
            first_high = confirm_df.iloc[0]['high']
            last_high = confirm_df.iloc[-1]['high']
            
            # Also check that we haven't filled the gap
            min_low = confirm_df['low'].min()
            gap_filled = min_low <= df_open.iloc[0]['open'] * 0.998  # Small buffer
            
            return last_high > first_high and not gap_filled
        
        else:  # gap down
            # For gap down, want to see lower lows
            first_low = confirm_df.iloc[0]['low']
            last_low = confirm_df.iloc[-1]['low']
            
            # Check gap hasn't filled
            max_high = confirm_df['high'].max()
            gap_filled = max_high >= df_open.iloc[0]['open'] * 1.002  # Small buffer
            
            return last_low < first_low and not gap_filled
    
    def calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """
        Calculate momentum score based on price action and volume
        
        Higher score = stronger momentum
        """
        # Price momentum: how much price moved vs range
        price_change = abs(df.iloc[-1]['close'] - df.iloc[0]['open'])
        avg_range = (df['high'] - df['low']).mean()
        price_momentum = price_change / avg_range if avg_range > 0 else 0
        
        # Volume momentum: current vs average
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].mean()
        volume_momentum = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Combine scores
        momentum_score = price_momentum * volume_momentum
        
        return momentum_score
    
    def execute_trade(self, entry_price: float, gap_direction: str,
                     df_remaining: pd.DataFrame, entry_time: pd.Timestamp) -> Dict[str, any]:
        """
        Execute gap and go trade
        """
        # Calculate stops and targets
        if gap_direction == 'up':
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            target = entry_price * (1 + self.target_pct)
            
            # Check exit conditions
            stop_hit = df_remaining[df_remaining['low'] <= stop_loss]
            target_hit = df_remaining[df_remaining['high'] >= target]
        else:  # gap down = short
            stop_loss = entry_price * (1 + self.stop_loss_pct)
            target = entry_price * (1 - self.target_pct)
            
            stop_hit = df_remaining[df_remaining['high'] >= stop_loss]
            target_hit = df_remaining[df_remaining['low'] <= target]
        
        # Time stop
        time_stop = entry_time + pd.Timedelta(minutes=self.time_stop_minutes)
        time_stopped = df_remaining[df_remaining.index >= time_stop]
        
        # Determine exit
        exit_time = df_remaining.index[-1]
        exit_price = df_remaining.iloc[-1]['close']
        exit_reason = 'eod'
        
        # Check stops in order of priority
        exits = []
        
        if not stop_hit.empty:
            exits.append(('stop_loss', stop_hit.index[0], stop_loss))
        if not target_hit.empty:
            exits.append(('target', target_hit.index[0], target))
        if not time_stopped.empty:
            exits.append(('time_stop', time_stopped.index[0], time_stopped.iloc[0]['close']))
        
        # Take earliest exit
        if exits:
            exits.sort(key=lambda x: x[1])  # Sort by time
            exit_reason, exit_time, exit_price = exits[0]
        
        # Calculate P&L
        multiplier = self.pnl_multipliers.get(self.instrument_type, 0.1)
        
        if gap_direction == 'up':
            raw_pnl = exit_price - entry_price
        else:
            raw_pnl = entry_price - exit_price
        
        pnl = raw_pnl * multiplier
        pnl_pct = (raw_pnl / entry_price) * 100
        
        return {
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'target': target,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'exit_time': exit_time,
            'duration_minutes': (exit_time - entry_time).total_seconds() / 60
        }
    
    def analyze_day(self, df_day: pd.DataFrame, prev_close: float) -> Dict[str, any]:
        """
        Analyze gap and go opportunity for a single day
        """
        # Get opening bar
        open_time = df_day.index[0]
        open_price = df_day.iloc[0]['open']
        
        # Calculate gap
        gap_pct, gap_direction = self.calculate_gap(prev_close, open_price)
        
        # Check if gap is large enough
        if abs(gap_pct) < self.min_gap_pct:
            return {
                'date': df_day.index[0].date() if isinstance(df_day.index, pd.DatetimeIndex) else pd.to_datetime(df_day.iloc[0]['date']).date(),
                'gap_pct': gap_pct * 100,
                'gap_direction': gap_direction,
                'traded': False,
                'reason': 'gap_too_small'
            }
        
        # Only trade in first hour
        entry_cutoff_time = open_time.replace(hour=10, minute=30)
        df_entry_window = df_day[df_day.index <= entry_cutoff_time]
        
        # Check for gap continuation
        if len(df_entry_window) < self.confirmation_bars + 1:
            return {
                'date': df_day.index[0].date() if isinstance(df_day.index, pd.DatetimeIndex) else pd.to_datetime(df_day.iloc[0]['date']).date(),
                'gap_pct': gap_pct * 100,
                'gap_direction': gap_direction,
                'traded': False,
                'reason': 'insufficient_data'
            }
        
        # Wait for confirmation
        gap_continues = self.check_gap_continuation(
            df_entry_window.iloc[1:],  # Skip first bar
            gap_direction
        )
        
        if not gap_continues:
            return {
                'date': df_day.index[0].date() if isinstance(df_day.index, pd.DatetimeIndex) else pd.to_datetime(df_day.iloc[0]['date']).date(),
                'gap_pct': gap_pct * 100,
                'gap_direction': gap_direction,
                'traded': False,
                'reason': 'no_continuation'
            }
        
        # Enter trade after confirmation
        entry_idx = self.confirmation_bars + 1
        entry_time = df_entry_window.index[entry_idx]
        entry_price = df_entry_window.iloc[entry_idx]['close']
        
        
        # Calculate momentum at entry
        momentum_score = self.calculate_momentum_score(df_entry_window.iloc[:entry_idx])
        
        # Execute trade
        df_remaining = df_day[df_day.index > entry_time]
        
        if df_remaining.empty:
            return {
                'date': df_day.index[0].date() if isinstance(df_day.index, pd.DatetimeIndex) else pd.to_datetime(df_day.iloc[0]['date']).date(),
                'gap_pct': gap_pct * 100,
                'gap_direction': gap_direction,
                'traded': False,
                'reason': 'no_data_after_entry'
            }
        
        trade_result = self.execute_trade(
            entry_price,
            gap_direction,
            df_remaining,
            entry_time
        )
        
        return {
            'date': df_day.index[0].date() if isinstance(df_day.index, pd.DatetimeIndex) else pd.to_datetime(df_day.iloc[0]['date']).date(),
            'gap_pct': gap_pct * 100,
            'gap_direction': gap_direction,
            'traded': True,
            'momentum_score': momentum_score,
            'trade_result': trade_result,
            'entry_time': entry_time
        }
    
    def backtest(self, df: pd.DataFrame, start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Backtest Gap and Go strategy
        """
        # Ensure we have a datetime index
        if 'date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df = df.set_index('date')
        
        # Ensure data is sorted
        df = df.sort_index()
        
        # Filter date range
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        
        # Group by day
        results = []
        prev_close = None
        
        for date, df_day in df.groupby(df.index.date):
            # Filter to regular trading hours
            mask = (df_day.index.time >= self.market_open) & \
                   (df_day.index.time <= self.market_close)
            df_day = df_day[mask]
            
            if len(df_day) < 30 or prev_close is None:
                # Store previous close for next day
                if len(df_day) > 0:
                    prev_close = df_day.iloc[-1]['close']
                continue
            
            # Analyze the day
            day_result = self.analyze_day(df_day, prev_close)
            
            if day_result['traded']:
                results.append(day_result)
            
            # Update previous close
            prev_close = df_day.iloc[-1]['close']
        
        # Create results DataFrame
        if not results:
            return pd.DataFrame()
        
        rows = []
        for r in results:
            trade = r['trade_result']
            rows.append({
                'date': r['date'],
                'gap_pct': r['gap_pct'],
                'gap_direction': r['gap_direction'],
                'momentum_score': r['momentum_score'],
                'entry_time': r['entry_time'],
                'entry_price': trade['entry_price'],
                'exit_price': trade['exit_price'],
                'exit_reason': trade['exit_reason'],
                'pnl': trade['pnl'],
                'pnl_pct': trade['pnl_pct'],
                'duration_minutes': trade['duration_minutes']
            })
        
        return pd.DataFrame(rows)
    
    def calculate_statistics(self, results_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate strategy performance statistics
        """
        if results_df.empty:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        
        wins = results_df[results_df['pnl'] > 0]
        losses = results_df[results_df['pnl'] <= 0]
        
        # Basic metrics
        total_trades = len(results_df)
        win_rate = len(wins) / total_trades
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        
        total_wins = wins['pnl'].sum() if len(wins) > 0 else 0
        total_losses = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        total_pnl = results_df['pnl'].sum()
        
        # Sharpe ratio
        daily_returns = results_df.groupby('date')['pnl'].sum()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0
        
        # Max drawdown
        cumulative_pnl = results_df['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min()
        
        # Gap-specific statistics
        gap_up_trades = results_df[results_df['gap_direction'] == 'up']
        gap_down_trades = results_df[results_df['gap_direction'] == 'down']
        
        # Exit reason analysis
        exit_reasons = results_df['exit_reason'].value_counts()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_duration': results_df['duration_minutes'].mean(),
            'avg_gap_size': results_df['gap_pct'].abs().mean(),
            'gap_up_trades': len(gap_up_trades),
            'gap_down_trades': len(gap_down_trades),
            'gap_up_win_rate': len(gap_up_trades[gap_up_trades['pnl'] > 0]) / len(gap_up_trades) if len(gap_up_trades) > 0 else 0,
            'gap_down_win_rate': len(gap_down_trades[gap_down_trades['pnl'] > 0]) / len(gap_down_trades) if len(gap_down_trades) > 0 else 0,
            'exit_by_target': exit_reasons.get('target', 0) / total_trades if total_trades > 0 else 0,
            'exit_by_stop': exit_reasons.get('stop_loss', 0) / total_trades if total_trades > 0 else 0,
            'exit_by_time': exit_reasons.get('time_stop', 0) / total_trades if total_trades > 0 else 0
        }