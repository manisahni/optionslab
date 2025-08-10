import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class ORBStrategy:
    """
    Opening Range Breakout (ORB) Strategy Implementation
    
    WHAT THE ORB STRATEGY ACTUALLY DOES:
    ====================================
    
    STEP 1: OPENING RANGE CALCULATION (9:30 AM - 9:45 AM for 15-min ORB)
    ---------------------------------------------------------------------
    • At market open (9:30 AM), start monitoring SPY price
    • For 15-minute ORB: Track high/low from 9:30 AM to 9:45 AM
    • For 30-minute ORB: Track high/low from 9:30 AM to 10:00 AM  
    • For 60-minute ORB: Track high/low from 9:30 AM to 10:30 AM
    • This creates the "opening range" - the price range during early trading
    
    STEP 2: BREAKOUT DETECTION (After opening range period)
    -------------------------------------------------------
    • After 9:45 AM (for 15-min ORB), monitor for breakouts
    • LONG SIGNAL: If SPY price goes ABOVE the opening range high
    • SHORT SIGNAL: If SPY price goes BELOW the opening range low
    • Only the FIRST breakout of the day is considered (whichever comes first)
    
    STEP 3: TRADE EXECUTION
    -----------------------
    • ENTRY: Enter position at the breakout level (opening range high/low)
    • STOP LOSS: Exit if price moves against us by 50% of opening range width
    • TARGET: Exit if price moves in our favor by 100% of opening range width
    • EXAMPLE: If opening range is $500-$502 (2 point range):
      - Long entry at $502 (breakout above high)
      - Stop loss at $501 (50% of 2-point range = 1 point)
      - Target at $504 (100% of 2-point range = 2 points)
    
    STEP 4: P&L CALCULATION
    ------------------------
    • Calculate profit/loss based on exit price vs entry price
    • Apply instrument multiplier (stock=1x, options=0.1x, futures=2x)
    
    KEY PARAMETERS:
    ===============
    • timeframe_minutes: How long to calculate opening range (5, 15, 30, 60)
    • stop_loss_pct: Stop loss as % of opening range width (default: 50%)
    • target_pct: Target as % of opening range width (default: 100%)
    • instrument_type: How to calculate P&L (stock/options/futures)
    
    EXAMPLE SCENARIO:
    =================
    Day: July 25, 2025
    SPY opens at $500
    9:30-9:45 AM: SPY trades between $500.50 and $501.50 (1-point range)
    9:47 AM: SPY breaks above $501.50 → LONG SIGNAL
    Entry: $501.50
    Stop Loss: $501.00 (50% of 1-point range)
    Target: $502.50 (100% of 1-point range)
    10:15 AM: SPY hits $502.50 → TARGET HIT → PROFIT
    """
    
    def __init__(self, timeframe_minutes: int = 15, instrument_type: str = "options",
                 starting_capital: float = 25000, risk_per_trade: float = 2.0):
        """
        Initialize ORB strategy with detailed parameters
        
        Args:
            timeframe_minutes: Opening range duration in minutes
                • 5: Calculate range from 9:30 AM to 9:35 AM
                • 15: Calculate range from 9:30 AM to 9:45 AM (most common)
                • 30: Calculate range from 9:30 AM to 10:00 AM
                • 60: Calculate range from 9:30 AM to 10:30 AM
            
            instrument_type: How to calculate P&L
                • "stock": Direct SPY shares (1:1 leverage)
                • "options": 0DTE options simulation (10% of underlying move)
                • "futures": SPY futures simulation (2x leverage)
            
        
        Strategy Parameters (Hardcoded):
        • Stop Loss: 50% of opening range width
        • Target: 100% of opening range width
        • Entry: At breakout level (opening range high/low)
        • Exit: First to hit stop loss or target
        • Signal: Only first breakout of the day
        """
        self.timeframe = timeframe_minutes
        self.instrument_type = instrument_type
        self.opening_time = time(9, 30)  # Market open
        self.closing_time = time(16, 0)  # Market close
        self.starting_capital = starting_capital
        self.risk_per_trade = risk_per_trade / 100  # Convert percentage to decimal
        self.current_capital = starting_capital  # Track running capital
        
        # P&L multipliers based on instrument type
        self.pnl_multipliers = {
            "stock": 1.0,      # Full price difference
            "options": 0.1,    # 10% of underlying move (typical for 0DTE)
            "futures": 2.0     # 2x leverage (typical for SPY futures)
        }
        self.timeframe = timeframe_minutes
        self.opening_time = time(9, 30)  # Market open
        self.closing_time = time(16, 0)  # Market close
        
    def calculate_opening_range(self, df_day: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate the opening range for a given day
        
        Returns:
            Dict with 'high', 'low', 'range', and 'midpoint'
        """
        # Get opening range bars - handle both date column and index cases
        if 'date' in df_day.columns:
            start_time = pd.Timestamp.combine(df_day['date'].iloc[0].date(), self.opening_time)
            end_time = start_time + pd.Timedelta(minutes=self.timeframe)
            
            # Handle timezone-aware comparison
            if df_day['date'].dt.tz is not None:
                start_time = start_time.tz_localize(df_day['date'].dt.tz)
                end_time = end_time.tz_localize(df_day['date'].dt.tz)
            
            orb_bars = df_day[(df_day['date'] >= start_time) & (df_day['date'] < end_time)]
        else:
            # Date is the index
            start_time = pd.Timestamp.combine(df_day.index[0].date(), self.opening_time)
            end_time = start_time + pd.Timedelta(minutes=self.timeframe)
            
            # Handle timezone-aware comparison
            if df_day.index.tz is not None:
                start_time = start_time.tz_localize(df_day.index.tz)
                end_time = end_time.tz_localize(df_day.index.tz)
            
            orb_bars = df_day[(df_day.index >= start_time) & (df_day.index < end_time)]
        
        if orb_bars.empty:
            return None
            
        orb_high = orb_bars['high'].max()
        orb_low = orb_bars['low'].min()
        orb_range = orb_high - orb_low
        orb_midpoint = (orb_high + orb_low) / 2
        
        return {
            'high': orb_high,
            'low': orb_low,
            'range': orb_range,
            'midpoint': orb_midpoint,
            'start_time': start_time,
            'end_time': end_time
        }
    
    def detect_breakout(self, df_day: pd.DataFrame, orb: Dict[str, float]) -> Dict[str, any]:
        """
        Detect breakout from opening range
        
        Returns:
            Dict with breakout details or None if no breakout
        """
        # Get bars after opening range - handle both date column and index cases
        if 'date' in df_day.columns:
            post_orb = df_day[df_day['date'] >= orb['end_time']]
        else:
            post_orb = df_day[df_day.index >= orb['end_time']]
        
        if post_orb.empty:
            return None
            
        breakout_info = {
            'type': None,
            'time': None,
            'price': None,
            'bars_after_orb': None
        }
        
        # Check for upside breakout
        upside_break = post_orb[post_orb['high'] > orb['high']]
        if not upside_break.empty:
            first_break = upside_break.iloc[0]
            breakout_info['type'] = 'long'
            if 'date' in df_day.columns:
                breakout_info['time'] = first_break['date']
                breakout_info['bars_after_orb'] = len(post_orb[post_orb['date'] <= first_break['date']])
            else:
                breakout_info['time'] = first_break.name  # Use index as time
                breakout_info['bars_after_orb'] = len(post_orb[post_orb.index <= first_break.name])
            breakout_info['price'] = orb['high']
            
        # Check for downside breakout
        downside_break = post_orb[post_orb['low'] < orb['low']]
        if not downside_break.empty:
            first_break = downside_break.iloc[0]
            # If no upside break or downside break came first
            if breakout_info['type'] is None or (first_break['date'] if 'date' in df_day.columns else first_break.name) < breakout_info['time']:
                breakout_info['type'] = 'short'
                if 'date' in df_day.columns:
                    breakout_info['time'] = first_break['date']
                    breakout_info['bars_after_orb'] = len(post_orb[post_orb['date'] <= first_break['date']])
                else:
                    breakout_info['time'] = first_break.name  # Use index as time
                    breakout_info['bars_after_orb'] = len(post_orb[post_orb.index <= first_break.name])
                breakout_info['price'] = orb['low']
                
        return breakout_info if breakout_info['type'] else None
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                                current_capital: float = None) -> int:
        """
        Calculate position size based on risk management rules
        
        Args:
            entry_price: Entry price of the trade
            stop_loss: Stop loss price
            current_capital: Current trading capital (uses self.current_capital if None)
            
        Returns:
            Number of shares/contracts to trade
        """
        if current_capital is None:
            current_capital = self.current_capital
            
        # Calculate risk per share/contract
        risk_per_unit = abs(entry_price - stop_loss)
        
        # Calculate maximum risk amount based on capital and risk percentage
        max_risk_amount = current_capital * self.risk_per_trade
        
        # Calculate position size
        if risk_per_unit > 0:
            position_size = int(max_risk_amount / risk_per_unit)
            
            # Apply instrument-specific constraints
            if self.instrument_type == "options":
                # Options trade in contracts (100 shares per contract)
                # For 0DTE simulation, we'll treat 1 unit as 1 contract
                position_size = max(1, position_size)
            elif self.instrument_type == "stock":
                # Ensure we don't exceed capital
                max_shares = int(current_capital / entry_price)
                position_size = min(position_size, max_shares)
            elif self.instrument_type == "futures":
                # Futures have fixed contract sizes
                position_size = max(1, position_size)
                
            return position_size
        else:
            return 0
    
    def calculate_trade_performance(self, df_day: pd.DataFrame, breakout: Dict, 
                                  stop_loss_pct: float = 0.5, target_pct: float = 1.0) -> Dict[str, float]:
        """
        Calculate trade performance after breakout
        
        Args:
            stop_loss_pct: Stop loss as % of ORB range
            target_pct: Target as % of ORB range
        """
        if not breakout:
            return None
            
        # Get bars after breakout - handle both date column and index cases
        if 'date' in df_day.columns:
            post_breakout = df_day[df_day['date'] >= breakout['time']]
        else:
            post_breakout = df_day[df_day.index >= breakout['time']]
        
        if post_breakout.empty:
            return None
            
        entry_price = breakout['price']
        orb_range = abs(entry_price - breakout.get('opposite_level', entry_price))
        
        if breakout['type'] == 'long':
            stop_loss = entry_price - (orb_range * stop_loss_pct)
            target = entry_price + (orb_range * target_pct)
            
            # Check if stop or target hit
            stop_hit = post_breakout[post_breakout['low'] <= stop_loss]
            target_hit = post_breakout[post_breakout['high'] >= target]
            
        else:  # short
            stop_loss = entry_price + (orb_range * stop_loss_pct)
            target = entry_price - (orb_range * target_pct)
            
            stop_hit = post_breakout[post_breakout['high'] >= stop_loss]
            target_hit = post_breakout[post_breakout['low'] <= target]
            
        # Determine outcome - handle both date column and index cases
        outcome = 'open'
        exit_price = post_breakout.iloc[-1]['close']
        if 'date' in df_day.columns:
            exit_time = post_breakout.iloc[-1]['date']
        else:
            exit_time = post_breakout.iloc[-1].name  # Use index as time
        
        if not stop_hit.empty and not target_hit.empty:
            if 'date' in df_day.columns:
                if stop_hit.iloc[0]['date'] < target_hit.iloc[0]['date']:
                    outcome = 'stop_loss'
                    exit_price = stop_loss
                    exit_time = stop_hit.iloc[0]['date']
                else:
                    outcome = 'target'
                    exit_price = target
                    exit_time = target_hit.iloc[0]['date']
            else:
                if stop_hit.iloc[0].name < target_hit.iloc[0].name:
                    outcome = 'stop_loss'
                    exit_price = stop_loss
                    exit_time = stop_hit.iloc[0].name
                else:
                    outcome = 'target'
                    exit_price = target
                    exit_time = target_hit.iloc[0].name
        elif not stop_hit.empty:
            outcome = 'stop_loss'
            exit_price = stop_loss
            if 'date' in df_day.columns:
                exit_time = stop_hit.iloc[0]['date']
            else:
                exit_time = stop_hit.iloc[0].name
        elif not target_hit.empty:
            outcome = 'target'
            exit_price = target
            if 'date' in df_day.columns:
                exit_time = target_hit.iloc[0]['date']
            else:
                exit_time = target_hit.iloc[0].name
            
        # Calculate position size based on risk management
        position_size = self.calculate_position_size(entry_price, stop_loss, self.current_capital)
        
        # Skip trade if position size is 0 (insufficient capital or risk too high)
        if position_size == 0:
            return None
            
        # Calculate P&L based on instrument type and position size
        multiplier = self.pnl_multipliers.get(self.instrument_type, 0.1)
        
        if breakout['type'] == 'long':
            raw_pnl_per_unit = exit_price - entry_price
            pnl = raw_pnl_per_unit * multiplier * position_size
            pnl_pct = (exit_price / entry_price - 1) * 100
        else:
            raw_pnl_per_unit = entry_price - exit_price
            pnl = raw_pnl_per_unit * multiplier * position_size
            pnl_pct = (entry_price / exit_price - 1) * 100
        
        # Calculate capital used for this trade
        if self.instrument_type == "options":
            # For options, assume premium is ~10% of stock price
            capital_used = position_size * entry_price * 0.1
        else:
            capital_used = position_size * entry_price
            
        return {
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'target': target,
            'outcome': outcome,
            'position_size': position_size,
            'capital_used': capital_used,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_time': breakout['time'],
            'exit_time': exit_time,
            'duration_minutes': (exit_time - breakout['time']).total_seconds() / 60
        }
    
    def analyze_day(self, df_day: pd.DataFrame) -> Dict[str, any]:
        """
        Complete ORB analysis for a single day
        """
        # Calculate opening range
        orb = self.calculate_opening_range(df_day)
        if not orb:
            return None
        
        # Detect breakout
        breakout = self.detect_breakout(df_day, orb)
        
        
        # Add opposite level for stop loss calculation
        if breakout:
            if breakout['type'] == 'long':
                breakout['opposite_level'] = orb['low']
            else:
                breakout['opposite_level'] = orb['high']
                
        # Calculate trade performance if breakout occurred
        trade_result = None
        if breakout:
            trade_result = self.calculate_trade_performance(df_day, breakout)
            
        return {
            'date': df_day['date'].iloc[0].date() if 'date' in df_day.columns else df_day.index[0].date(),
            'orb': orb,
            'breakout': breakout,
            'trade_result': trade_result
        }
    
    def backtest(self, df: pd.DataFrame, start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Backtest ORB strategy over multiple days
        """
        # Filter date range if specified
        if start_date:
            # Handle timezone-aware comparison
            if 'date' in df.columns:
                if df['date'].dt.tz is not None:
                    # Convert to pandas Timestamp and ensure it has the same timezone
                    start_date = pd.Timestamp(start_date)
                    if start_date.tz is None:
                        start_date = start_date.tz_localize(df['date'].dt.tz)
                    elif start_date.tz != df['date'].dt.tz:
                        start_date = start_date.tz_convert(df['date'].dt.tz)
                else:
                    # Data is timezone-naive, ensure start_date is also naive
                    start_date = pd.Timestamp(start_date).tz_localize(None)
                df = df[df['date'] >= start_date]
            else:
                # Date is the index
                if df.index.tz is not None:
                    start_date = pd.Timestamp(start_date)
                    if start_date.tz is None:
                        start_date = start_date.tz_localize(df.index.tz)
                    elif start_date.tz != df.index.tz:
                        start_date = start_date.tz_convert(df.index.tz)
                else:
                    start_date = pd.Timestamp(start_date).tz_localize(None)
                df = df[df.index >= start_date]
        if end_date:
            # Handle timezone-aware comparison
            if 'date' in df.columns:
                if df['date'].dt.tz is not None:
                    # Convert to pandas Timestamp and ensure it has the same timezone
                    end_date = pd.Timestamp(end_date)
                    if end_date.tz is None:
                        end_date = end_date.tz_localize(df['date'].dt.tz)
                    elif end_date.tz != df['date'].dt.tz:
                        end_date = end_date.tz_convert(df['date'].dt.tz)
                else:
                    # Data is timezone-naive, ensure end_date is also naive
                    end_date = pd.Timestamp(end_date).tz_localize(None)
                df = df[df['date'] <= end_date]
            else:
                # Date is the index
                if df.index.tz is not None:
                    end_date = pd.Timestamp(end_date)
                    if end_date.tz is None:
                        end_date = end_date.tz_localize(df.index.tz)
                    elif end_date.tz != df.index.tz:
                        end_date = end_date.tz_convert(df.index.tz)
                else:
                    end_date = pd.Timestamp(end_date).tz_localize(None)
                df = df[df.index <= end_date]
            
        
        # Get unique trading days - handle both index and column cases
        if 'date' in df.columns:
            trading_days = df['date'].dt.date.unique()
        else:
            # Date is the index - convert numpy array to pandas Series for unique()
            trading_days = pd.Series(df.index.date).unique()
        
        results = []
        self.current_capital = self.starting_capital  # Reset to starting capital
        
        for day in trading_days:
            if 'date' in df.columns:
                df_day = df[df['date'].dt.date == day]
            else:
                df_day = df[df.index.date == day]
            
            # Only analyze regular trading hours
            if 'date' in df_day.columns:
                mask = (df_day['date'].dt.time >= self.opening_time) & \
                       (df_day['date'].dt.time <= self.closing_time)
            else:
                mask = (df_day.index.time >= self.opening_time) & \
                       (df_day.index.time <= self.closing_time)
            df_day = df_day[mask]
            
            if len(df_day) < 30:  # Skip days with insufficient data
                continue
                
            day_result = self.analyze_day(df_day)
            if day_result and day_result.get('trade_result'):
                # Update current capital based on P&L
                self.current_capital += day_result['trade_result']['pnl']
                # Store current capital in the result
                day_result['trade_result']['current_capital'] = self.current_capital
                results.append(day_result)
                
        return self._create_results_dataframe(results)
    
    def _create_results_dataframe(self, results: List[Dict]) -> pd.DataFrame:
        """
        Create a structured DataFrame from backtest results
        """
        if not results:
            # Return empty DataFrame with expected columns
            return pd.DataFrame({
                'date': [],
                'orb_high': [],
                'orb_low': [],
                'orb_range': [],
                'breakout': [],
                'breakout_type': [],
                'breakout_time': [],
                'entry_price': [],
                'exit_price': [],
                'outcome': [],
                'position_size': [],
                'capital_used': [],
                'pnl': [],
                'pnl_pct': [],
                'current_capital': [],
                'duration_minutes': []
            })
        
        rows = []
        for r in results:
            row = {
                'date': r['date'],
                'orb_high': r['orb']['high'],
                'orb_low': r['orb']['low'],
                'orb_range': r['orb']['range'],
                'breakout': r['breakout'] is not None,
                'breakout_type': r['breakout']['type'] if r['breakout'] else None,
                'breakout_time': r['breakout']['time'] if r['breakout'] else None,
            }
            
            if r['trade_result']:
                row.update({
                    'entry_price': r['trade_result']['entry_price'],
                    'exit_price': r['trade_result']['exit_price'],
                    'outcome': r['trade_result']['outcome'],
                    'position_size': r['trade_result']['position_size'],
                    'capital_used': r['trade_result']['capital_used'],
                    'pnl': r['trade_result']['pnl'],
                    'pnl_pct': r['trade_result']['pnl_pct'],
                    'current_capital': r['trade_result']['current_capital'],
                    'duration_minutes': r['trade_result']['duration_minutes']
                })
            else:
                row.update({
                    'entry_price': None,
                    'exit_price': None,
                    'outcome': None,
                    'position_size': None,
                    'capital_used': None,
                    'pnl': None,
                    'pnl_pct': None,
                    'current_capital': None,
                    'duration_minutes': None
                })
                
            rows.append(row)
            
        return pd.DataFrame(rows)
    
    def calculate_statistics(self, results_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate strategy performance statistics
        """
        # Handle case where 'breakout' column might not exist
        if 'breakout' not in results_df.columns:
            return {
                'total_days': len(results_df),
                'breakout_days': 0,
                'breakout_rate': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'sharpe_ratio': 0
            }
        
        trades = results_df[results_df['breakout'] == True]
        
        if trades.empty:
            return {
                'total_days': len(results_df),
                'breakout_days': 0,
                'breakout_rate': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'sharpe_ratio': 0
            }
            
        wins = trades[trades['outcome'] == 'target']
        losses = trades[trades['outcome'] == 'stop_loss']
        
        stats = {
            'total_days': len(results_df),
            'breakout_days': len(trades),
            'breakout_rate': len(trades) / len(results_df),
            'win_rate': len(wins) / len(trades) if len(trades) > 0 else 0,
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'avg_win_pct': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
            'avg_loss_pct': losses['pnl_pct'].mean() if len(losses) > 0 else 0,
            'total_pnl': trades['pnl'].sum() if 'pnl' in trades else 0,
            'avg_duration': trades['duration_minutes'].mean() if 'duration_minutes' in trades else 0
        }
        
        # Calculate profit factor
        total_wins = wins['pnl'].sum() if len(wins) > 0 else 0
        total_losses = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
        stats['profit_factor'] = total_wins / total_losses if total_losses > 0 else 0
        
        # Calculate Sharpe ratio (simplified daily)
        if len(trades) > 0 and 'pnl' in trades:
            daily_returns = trades.groupby('date')['pnl'].sum()
            stats['sharpe_ratio'] = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0
        else:
            stats['sharpe_ratio'] = 0
            
        return stats