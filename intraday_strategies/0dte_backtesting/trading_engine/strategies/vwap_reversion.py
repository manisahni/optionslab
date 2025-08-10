"""
VWAP Bounce Strategy Implementation for 0DTE Trading

This strategy trades bounces off the Volume Weighted Average Price (VWAP) line.
VWAP is a crucial intraday indicator that shows the average price weighted by volume.

Strategy Logic:
1. Calculate VWAP throughout the day
2. Buy when price touches VWAP from above (bounce up)
3. Sell when price touches VWAP from below (bounce down)
4. Use ATR-based stops and targets
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class VWAPBounceStrategy:
    """
    VWAP Bounce Strategy for intraday trading
    
    Key Concepts:
    - VWAP acts as a dynamic support/resistance level
    - Price tends to revert to VWAP after deviations
    - Strong volume at VWAP indicates institutional interest
    - Best used in ranging/choppy markets
    """
    
    def __init__(self, 
                 min_distance_pct: float = 0.02,  # Min distance from VWAP to trigger (0.02%)
                 stop_loss_atr: float = 1.2,     # Stop loss in ATR multiples (tighter)
                 target_atr: float = 1.8,         # Target in ATR multiples (realistic)
                 instrument_type: str = "options"):
        """
        Initialize VWAP Bounce strategy
        
        Args:
            min_distance_pct: Minimum % distance from VWAP to consider a bounce
            stop_loss_atr: Stop loss distance in ATR multiples
            target_atr: Target distance in ATR multiples
            instrument_type: Type of instrument (stock/options/futures)
        """
        self.min_distance_pct = min_distance_pct / 100  # Convert to decimal
        self.stop_loss_atr = stop_loss_atr
        self.target_atr = target_atr
        self.instrument_type = instrument_type
        
        # Trading hours
        self.market_open = time(9, 30)
        self.market_close = time(16, 0)
        self.last_entry = time(15, 30)  # No new positions after 3:30 PM
        
        # P&L multipliers
        self.pnl_multipliers = {
            "stock": 1.0,
            "options": 0.1,
            "futures": 2.0
        }
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate VWAP (Volume Weighted Average Price)
        
        VWAP = Σ(Price × Volume) / Σ(Volume)
        """
        # Calculate typical price (high + low + close) / 3
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # Calculate cumulative totals for the day
        cum_volume = df['volume'].cumsum()
        cum_pv = (typical_price * df['volume']).cumsum()
        
        # VWAP = cumulative(price*volume) / cumulative(volume)
        vwap = cum_pv / cum_volume
        
        return vwap
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range for volatility-based stops
        """
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def identify_bounce_signals(self, df: pd.DataFrame, vwap: pd.Series) -> pd.DataFrame:
        """
        Identify VWAP bounce opportunities
        
        Returns DataFrame with bounce signals
        """
        signals = pd.DataFrame(index=df.index)
        signals['vwap'] = vwap
        signals['price'] = df['close']
        signals['distance_pct'] = (df['close'] - vwap) / vwap
        
        # Calculate if price is approaching VWAP
        signals['above_vwap'] = df['close'] > vwap
        signals['prev_above'] = signals['above_vwap'].shift(1)
        
        # Bounce up: Price was below VWAP, now touching/crossing up
        # Must be at least min_distance away before bounce
        prev_distance = signals['distance_pct'].shift(1)
        signals['bounce_up'] = (
            (signals['prev_above'] == False) &  # Was below VWAP
            (signals['above_vwap'] == True) &   # Now above VWAP
            (prev_distance < -self.min_distance_pct)  # Was far enough below
        )
        
        # Bounce down: Price was above VWAP, now touching/crossing down
        signals['bounce_down'] = (
            (signals['prev_above'] == True) &    # Was above VWAP
            (signals['above_vwap'] == False) &   # Now below VWAP
            (prev_distance > self.min_distance_pct)   # Was far enough above
        )
        
        return signals
    
    def execute_trade(self, signal_type: str, entry_price: float, 
                     atr: float, df_remaining: pd.DataFrame) -> Dict[str, any]:
        """
        Execute trade with VWAP bounce logic
        """
        if signal_type == 'bounce_up':
            # Long trade
            stop_loss = entry_price - (atr * self.stop_loss_atr)
            target = entry_price + (atr * self.target_atr)
            
            # Check exit conditions
            stop_hit = df_remaining[df_remaining['low'] <= stop_loss]
            target_hit = df_remaining[df_remaining['high'] >= target]
            
        else:  # bounce_down
            # Short trade
            stop_loss = entry_price + (atr * self.stop_loss_atr)
            target = entry_price - (atr * self.target_atr)
            
            stop_hit = df_remaining[df_remaining['high'] >= stop_loss]
            target_hit = df_remaining[df_remaining['low'] <= target]
        
        # Determine exit
        exit_time = df_remaining.index[-1]
        exit_price = df_remaining.iloc[-1]['close']
        exit_reason = 'eod'  # End of day
        
        if not stop_hit.empty and not target_hit.empty:
            if stop_hit.index[0] < target_hit.index[0]:
                exit_time = stop_hit.index[0]
                exit_price = stop_loss
                exit_reason = 'stop_loss'
            else:
                exit_time = target_hit.index[0]
                exit_price = target
                exit_reason = 'target'
        elif not stop_hit.empty:
            exit_time = stop_hit.index[0]
            exit_price = stop_loss
            exit_reason = 'stop_loss'
        elif not target_hit.empty:
            exit_time = target_hit.index[0]
            exit_price = target
            exit_reason = 'target'
        
        # Calculate P&L
        multiplier = self.pnl_multipliers.get(self.instrument_type, 0.1)
        
        if signal_type == 'bounce_up':
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
            'duration_minutes': (exit_time - df_remaining.index[0]).total_seconds() / 60
        }
    
    def analyze_day(self, df_day: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze VWAP bounces for a single day
        """
        # Calculate VWAP for the day
        vwap = self.calculate_vwap(df_day)
        
        # Calculate ATR
        atr = self.calculate_atr(df_day)
        
        # Identify bounce signals
        signals = self.identify_bounce_signals(df_day, vwap)
        
        # Find first valid signal after 9:45 AM (give VWAP time to establish)
        valid_time = df_day.index[0].replace(hour=9, minute=45)
        last_entry_time = df_day.index[0].replace(hour=15, minute=30)
        
        valid_signals = signals[
            (signals.index >= valid_time) & 
            (signals.index <= last_entry_time)
        ]
        
        # Get first bounce signal
        bounce_ups = valid_signals[valid_signals['bounce_up']]
        bounce_downs = valid_signals[valid_signals['bounce_down']]
        
        trade_result = None
        signal_type = None
        entry_time = None
        
        # Take first signal (either bounce up or down)
        if not bounce_ups.empty and not bounce_downs.empty:
            if bounce_ups.index[0] < bounce_downs.index[0]:
                entry_time = bounce_ups.index[0]
                signal_type = 'bounce_up'
            else:
                entry_time = bounce_downs.index[0]
                signal_type = 'bounce_down'
        elif not bounce_ups.empty:
            entry_time = bounce_ups.index[0]
            signal_type = 'bounce_up'
        elif not bounce_downs.empty:
            entry_time = bounce_downs.index[0]
            signal_type = 'bounce_down'
        
        # Execute trade if signal found
        if entry_time:
            entry_idx = df_day.index.get_loc(entry_time)
            entry_price = df_day.loc[entry_time, 'close']
            entry_atr = atr.iloc[entry_idx] if not pd.isna(atr.iloc[entry_idx]) else df_day['high'].iloc[entry_idx] - df_day['low'].iloc[entry_idx]
            
            # Execute trade
            df_remaining = df_day.iloc[entry_idx + 1:]
            if not df_remaining.empty:
                trade_result = self.execute_trade(
                    signal_type, 
                    entry_price, 
                    entry_atr,
                    df_remaining
                )
                trade_result['entry_time'] = entry_time
                trade_result['signal_type'] = signal_type
                trade_result['vwap_at_entry'] = vwap.iloc[entry_idx]
        
        return {
            'date': df_day.index[0].date() if isinstance(df_day.index, pd.DatetimeIndex) else pd.to_datetime(df_day.iloc[0]['date']).date(),
            'trade_result': trade_result,
            'signals_found': len(bounce_ups) + len(bounce_downs),
            'vwap_close': vwap.iloc[-1],
            'price_close': df_day.iloc[-1]['close']
        }
    
    def backtest(self, df: pd.DataFrame, start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Backtest VWAP bounce strategy over multiple days
        """
        # Ensure we have a datetime index
        if 'date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df = df.set_index('date')
        
        # Filter date range
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        
        # Group by day and analyze
        results = []
        
        for date, df_day in df.groupby(df.index.date):
            # Only analyze regular trading hours
            mask = (df_day.index.time >= self.market_open) & \
                   (df_day.index.time <= self.market_close)
            df_day = df_day[mask]
            
            if len(df_day) < 30:  # Need enough data
                continue
            
            day_result = self.analyze_day(df_day)
            if day_result['trade_result']:
                results.append(day_result)
        
        # Create results DataFrame
        if not results:
            return pd.DataFrame()
        
        rows = []
        for r in results:
            trade = r['trade_result']
            rows.append({
                'date': r['date'],
                'signal_type': trade['signal_type'],
                'entry_time': trade['entry_time'],
                'entry_price': trade['entry_price'],
                'vwap_at_entry': trade['vwap_at_entry'],
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
        
        # Calculate metrics
        total_trades = len(results_df)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        
        total_wins = wins['pnl'].sum() if len(wins) > 0 else 0
        total_losses = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        total_pnl = results_df['pnl'].sum()
        
        # Sharpe ratio (simplified daily)
        daily_returns = results_df.groupby('date')['pnl'].sum()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0
        
        # Max drawdown
        cumulative_pnl = results_df['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        max_drawdown = drawdown.min()
        
        # Signal-specific stats
        long_trades = results_df[results_df['signal_type'] == 'bounce_up']
        short_trades = results_df[results_df['signal_type'] == 'bounce_down']
        
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
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'long_win_rate': len(long_trades[long_trades['pnl'] > 0]) / len(long_trades) if len(long_trades) > 0 else 0,
            'short_win_rate': len(short_trades[short_trades['pnl'] > 0]) / len(short_trades) if len(short_trades) > 0 else 0
        }