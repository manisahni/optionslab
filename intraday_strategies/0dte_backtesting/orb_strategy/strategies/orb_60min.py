"""
60-Minute Opening Range Breakout Strategy
Best performer based on backtested results: 88.8% win rate
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.orb_calculator import ORBCalculator
from core.breakout_detector import BreakoutDetector  
from core.position_builder import CreditSpreadBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ORB60MinStrategy:
    """
    60-Minute ORB Strategy with Credit Spreads
    
    Performance (from article):
    - Win Rate: 88.8%
    - Total P/L: $30,708
    - Max Drawdown: -$3,231
    - Profit Factor: 1.59
    - Average P/L: $51/trade
    """
    
    def __init__(self, 
                 spread_width: float = 15,
                 position_size_pct: float = 0.02,
                 profit_target_pct: float = 0.8,
                 stop_loss_multiplier: float = 2.0):
        """
        Initialize 60-minute ORB strategy
        
        Args:
            spread_width: Width of credit spreads ($15 optimal)
            position_size_pct: Position size as % of account
            profit_target_pct: Take profit at X% of max profit
            stop_loss_multiplier: Stop at X times credit received
        """
        # Core components
        self.orb_calculator = ORBCalculator(timeframe_minutes=60)
        self.breakout_detector = BreakoutDetector()
        self.position_builder = CreditSpreadBuilder(
            spread_width=spread_width,
            position_size_pct=position_size_pct
        )
        
        # Strategy parameters
        self.profit_target_pct = profit_target_pct
        self.stop_loss_multiplier = stop_loss_multiplier
        
        # State tracking
        self.current_position = None
        self.daily_trade_taken = False
        self.current_date = None
        self.or_levels = None
        
        # Performance tracking
        self.trades = []
        self.daily_pnl = 0
        
        logger.info("60-Minute ORB Strategy initialized")
    
    def process_bar(self, bar: pd.Series, data: pd.DataFrame, 
                   account_value: float = 100000) -> Dict:
        """
        Process each bar for trading signals
        
        Args:
            bar: Current price bar
            data: Historical data for context
            account_value: Account value for position sizing
            
        Returns:
            Dict with action to take
        """
        current_time = bar.name.time() if hasattr(bar.name, 'time') else None
        current_date = bar.name.date() if hasattr(bar.name, 'date') else bar.name
        
        # Reset for new day
        if current_date != self.current_date:
            self.reset_daily_state()
            self.current_date = current_date
        
        # Calculate opening range after 10:30 AM
        if current_time == time(10, 30) and not self.or_levels:
            self.or_levels = self.calculate_opening_range(data)
            if self.or_levels:
                logger.info(f"OR calculated: ${self.or_levels['low']:.2f} - ${self.or_levels['high']:.2f}")
        
        # Check for position management
        if self.current_position:
            action = self.manage_position(bar)
            if action and action['action'] == 'close':
                return action
        
        # Check for new entry (only if no position and OR is set)
        if not self.current_position and not self.daily_trade_taken and self.or_levels:
            if current_time and time(10, 30) < current_time < time(15, 30):
                signal = self.check_entry_signal(bar, data)
                if signal:
                    return signal
        
        return {'action': 'hold'}
    
    def calculate_opening_range(self, data: pd.DataFrame) -> Dict:
        """Calculate 60-minute opening range"""
        or_levels = self.orb_calculator.calculate_range(data)
        
        if or_levels and or_levels['valid']:
            logger.info(f"Valid OR found: Range = ${or_levels['range']:.2f} ({or_levels['range_pct']:.3%})")
            return or_levels
        else:
            logger.info("Invalid OR - skipping day")
            return None
    
    def check_entry_signal(self, bar: pd.Series, data: pd.DataFrame) -> Optional[Dict]:
        """Check for breakout and generate entry signal"""
        
        # Get recent bars for confirmation
        bar_idx = data.index.get_loc(bar.name)
        if bar_idx >= 2:
            historical = data.iloc[bar_idx-2:bar_idx]
        else:
            historical = None
        
        # Detect breakout
        breakout = self.breakout_detector.detect_breakout(
            bar, 
            self.or_levels,
            historical
        )
        
        if not breakout:
            return None
        
        # Build position
        position = self.position_builder.build_position(
            breakout,
            self.or_levels,
            account_value=100000  # Would pass actual account value
        )
        
        if position:
            self.current_position = position
            self.daily_trade_taken = True
            
            logger.info(f"ENTRY: {position['type']} - {position['num_contracts']} contracts")
            logger.info(f"Strikes: ${position['short_strike']}/{position['long_strike']}")
            
            return {
                'action': 'enter',
                'position': position,
                'timestamp': bar.name
            }
        
        return None
    
    def manage_position(self, bar: pd.Series) -> Optional[Dict]:
        """Manage existing position"""
        
        if not self.current_position:
            return None
        
        current_time = bar.name.time() if hasattr(bar.name, 'time') else None
        current_price = bar['close']
        
        # Time-based exit at 3:59 PM
        if current_time and current_time >= time(15, 59):
            return self.close_position(bar, reason='time_exit')
        
        # Calculate P&L (simplified - need real option prices)
        pnl = self.calculate_position_pnl(self.current_position, current_price)
        
        # Profit target (80% of max profit)
        max_profit = self.current_position['max_profit']
        if pnl >= max_profit * self.profit_target_pct:
            return self.close_position(bar, reason='profit_target', pnl=pnl)
        
        # Stop loss (2x credit received)
        credit = self.current_position['estimated_credit']
        if pnl <= -credit * self.stop_loss_multiplier:
            return self.close_position(bar, reason='stop_loss', pnl=pnl)
        
        return None
    
    def calculate_position_pnl(self, position: Dict, current_price: float) -> float:
        """
        Calculate position P&L (simplified)
        In production, would use real option prices
        """
        # Simplified P&L based on how far price moved
        if position['type'] == 'put_credit_spread':
            # Put spread profits if price stays above short strike
            if current_price > position['short_strike']:
                # Keeping most of credit
                pnl = position['estimated_credit'] * 0.8
            elif current_price < position['long_strike']:
                # Max loss
                pnl = -position['max_loss']
            else:
                # Partial loss
                loss_pct = (position['short_strike'] - current_price) / position['spread_width']
                pnl = position['estimated_credit'] - (position['max_loss'] * loss_pct)
        else:
            # Call spread profits if price stays below short strike
            if current_price < position['short_strike']:
                # Keeping most of credit
                pnl = position['estimated_credit'] * 0.8
            elif current_price > position['long_strike']:
                # Max loss
                pnl = -position['max_loss']
            else:
                # Partial loss
                loss_pct = (current_price - position['short_strike']) / position['spread_width']
                pnl = position['estimated_credit'] - (position['max_loss'] * loss_pct)
        
        return pnl
    
    def close_position(self, bar: pd.Series, reason: str, pnl: float = None) -> Dict:
        """Close current position"""
        
        if not self.current_position:
            return None
        
        if pnl is None:
            pnl = self.calculate_position_pnl(self.current_position, bar['close'])
        
        # Record trade
        trade_record = {
            'date': bar.name.date() if hasattr(bar.name, 'date') else bar.name,
            'entry_time': self.current_position['entry_time'],
            'exit_time': bar.name,
            'type': self.current_position['type'],
            'strikes': f"{self.current_position['short_strike']}/{self.current_position['long_strike']}",
            'contracts': self.current_position['num_contracts'],
            'pnl': pnl,
            'exit_reason': reason,
            'or_range': self.or_levels['range'] if self.or_levels else 0
        }
        
        self.trades.append(trade_record)
        self.daily_pnl += pnl
        
        logger.info(f"EXIT: {reason} - P&L: ${pnl:.0f}")
        
        # Clear position
        self.current_position = None
        
        return {
            'action': 'close',
            'reason': reason,
            'pnl': pnl,
            'timestamp': bar.name
        }
    
    def reset_daily_state(self):
        """Reset state for new trading day"""
        self.current_position = None
        self.daily_trade_taken = False
        self.or_levels = None
        self.daily_pnl = 0
        self.breakout_detector.reset_daily_flag()
        
        logger.info("Daily state reset for new trading day")
    
    def get_performance_summary(self) -> Dict:
        """Get strategy performance summary"""
        
        if not self.trades:
            return {'status': 'No trades executed'}
        
        trades_df = pd.DataFrame(self.trades)
        
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        total_pnl = trades_df['pnl'].sum()
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['pnl'].mean()) if len(losing_trades) > 0 else 0
        
        summary = {
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0,
            'total_pnl': total_pnl,
            'avg_pnl': trades_df['pnl'].mean(),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades)) 
                           if len(losing_trades) > 0 and avg_loss > 0 else 0,
            'max_drawdown': trades_df['pnl'].cumsum().min(),
            'trades': trades_df
        }
        
        return summary


def main():
    """Test the 60-minute ORB strategy"""
    
    print("Testing 60-Minute ORB Strategy\n" + "="*50)
    
    # Create sample data for one day
    dates = pd.date_range(start='2024-01-02 09:30', end='2024-01-02 16:00', freq='1min')
    
    # Simulate SPY with breakout
    prices = []
    for dt in dates:
        hour, minute = dt.hour, dt.minute
        
        # OR period: 9:30-10:30, range 448-452
        if hour == 9 or (hour == 10 and minute <= 30):
            price = 450 + np.sin((minute/60) * np.pi) * 2
        # Breakout at 11:00
        elif hour == 11 and minute == 0:
            price = 452.5  # Break above OR
        elif hour >= 11:
            price = 452.5 + np.random.uniform(0, 1)
        else:
            price = 450
        
        prices.append(price)
    
    data = pd.DataFrame({
        'open': prices,
        'high': [p + 0.2 for p in prices],
        'low': [p - 0.2 for p in prices], 
        'close': prices,
        'volume': np.random.randint(500000, 2000000, len(prices))
    }, index=dates)
    
    # Initialize strategy
    strategy = ORB60MinStrategy()
    
    # Process each bar
    for idx, bar in data.iterrows():
        action = strategy.process_bar(bar, data)
        
        if action['action'] == 'enter':
            print(f"\n✅ ENTRY at {idx.strftime('%H:%M')}")
            print(f"   Position: {action['position']['type']}")
        elif action['action'] == 'close':
            print(f"\n🔴 EXIT at {idx.strftime('%H:%M')}")
            print(f"   Reason: {action['reason']}")
            print(f"   P&L: ${action['pnl']:.0f}")
    
    # Show summary
    summary = strategy.get_performance_summary()
    
    print("\n" + "="*50)
    print("Performance Summary:")
    print(f"Total Trades: {summary.get('total_trades', 0)}")
    print(f"Win Rate: {summary.get('win_rate', 0):.1%}")
    print(f"Total P&L: ${summary.get('total_pnl', 0):.0f}")


if __name__ == "__main__":
    main()