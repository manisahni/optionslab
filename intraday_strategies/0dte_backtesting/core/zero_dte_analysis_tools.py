"""
Zero DTE Analysis Tools
Utilities for analyzing 0DTE SPY options data
"""

from .zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt


class ZeroDTEAnalyzer:
    """Analysis tools for 0DTE options strategies"""
    
    def __init__(self, db: ZeroDTESPYOptionsDatabase):
        self.db = db
    
    def analyze_strangle_pnl(self, date: str, entry_time: str = "10:00", 
                            exit_time: str = "15:50", delta_target: float = 0.30):
        """
        Analyze P&L for a delta-neutral strangle
        
        Args:
            date: Date YYYYMMDD
            entry_time: Entry time HH:MM
            exit_time: Exit time HH:MM
            delta_target: Target delta for strikes
            
        Returns:
            Dict with P&L analysis
        """
        # Get strangles for the day
        strangles = self.db.get_zero_dte_strangles(date, delta_target)
        if strangles.empty:
            return None
        
        # Add total bid/ask columns
        strangles['total_bid'] = strangles['call_bid'] + strangles['put_bid']
        strangles['total_ask'] = strangles['call_ask'] + strangles['put_ask']
        
        # Convert times
        entry_ts = f"{date[:4]}-{date[4:6]}-{date[6:]}T{entry_time}:00"
        exit_ts = f"{date[:4]}-{date[4:6]}-{date[6:]}T{exit_time}:00"
        
        # Get entry and exit
        entry = strangles[strangles['timestamp'] == entry_ts]
        exit = strangles[strangles['timestamp'] == exit_ts]
        
        if entry.empty or exit.empty:
            return None
        
        entry = entry.iloc[0]
        exit = exit.iloc[0]
        
        # Calculate P&L (selling strangle)
        entry_credit = entry['total_bid']
        exit_debit = exit['total_ask']
        
        pnl = entry_credit - exit_debit
        pnl_pct = (pnl / entry_credit) if entry_credit > 0 else 0  # Keep as decimal, not percentage
        
        return {
            'date': date,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_underlying': entry['underlying_price'],
            'exit_underlying': exit['underlying_price'],
            'underlying_move': exit['underlying_price'] - entry['underlying_price'],
            'underlying_move_pct': ((exit['underlying_price'] - entry['underlying_price']) / 
                                   entry['underlying_price']) * 100,
            'call_strike': entry['call_strike'],
            'put_strike': entry['put_strike'],
            'entry_credit': entry_credit,
            'exit_debit': exit_debit,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'call_entry_delta': entry['call_delta'],
            'put_entry_delta': entry['put_delta'],
            'max_profit': entry_credit,
            'won': pnl > 0
        }
    
    def backtest_strangle_strategy(self, start_date: str, end_date: str,
                                 entry_time: str = "10:00", exit_time: str = "15:50",
                                 delta_target: float = 0.30):
        """
        Backtest strangle strategy over date range
        
        Returns:
            DataFrame with daily results
        """
        results = []
        
        # Load data for date range
        data = self.db.load_date_range(start_date, end_date)
        if data.empty:
            return pd.DataFrame()
        
        # Get unique dates
        dates = data['trade_date'].unique()
        
        for date in dates:
            result = self.analyze_strangle_pnl(date, entry_time, exit_time, delta_target)
            if result:
                results.append(result)
        
        if not results:
            return pd.DataFrame()
        
        results_df = pd.DataFrame(results)
        
        # Add cumulative metrics
        results_df['cumulative_pnl'] = results_df['pnl'].cumsum()
        results_df['win_rate'] = results_df['won'].expanding().mean()
        
        return results_df
    
    def analyze_entry_times(self, date: str, delta_target: float = 0.30):
        """
        Analyze best entry times for 0DTE strangles
        
        Returns:
            DataFrame with P&L by entry time
        """
        results = []
        exit_time = "15:50"  # Fixed exit near close
        
        # Test entry times from 9:30 to 14:00
        for hour in range(9, 15):
            for minute in [0, 30]:
                if hour == 9 and minute == 0:
                    continue  # Skip 9:00
                
                entry_time = f"{hour:02d}:{minute:02d}"
                
                result = self.analyze_strangle_pnl(date, entry_time, exit_time, delta_target)
                if result:
                    results.append(result)
        
        return pd.DataFrame(results)
    
    def get_intraday_strangle_prices(self, date: str, delta_target: float = 0.30):
        """
        Get intraday strangle prices for monitoring
        
        Returns:
            DataFrame with strangle values throughout the day
        """
        strangles = self.db.get_zero_dte_strangles(date, delta_target)
        
        if strangles.empty:
            return pd.DataFrame()
        
        # Calculate total values
        strangles['total_value'] = strangles['total_mid']
        strangles['time'] = pd.to_datetime(strangles['timestamp']).dt.time
        
        return strangles[['time', 'underlying_price', 'call_strike', 'put_strike',
                         'call_mid', 'put_mid', 'total_value', 'call_delta', 'put_delta']]
    
    def calculate_profit_targets(self, entry_credit: float, 
                               target_pcts: list = [0.25, 0.50, 0.75]):
        """
        Calculate profit target prices
        
        Args:
            entry_credit: Credit received at entry
            target_pcts: List of profit target percentages
            
        Returns:
            Dict of target prices
        """
        targets = {}
        for pct in target_pcts:
            targets[f"{int(pct*100)}%"] = entry_credit * (1 - pct)
        
        return targets


def main():
    """Example usage"""
    # Initialize database and analyzer
    db = ZeroDTESPYOptionsDatabase()
    analyzer = ZeroDTEAnalyzer(db)
    
    # Example: Analyze single day
    # result = analyzer.analyze_strangle_pnl('20250505', entry_time='10:00', exit_time='15:50')
    # print(result)
    
    # Example: Backtest strategy
    # results = analyzer.backtest_strangle_strategy('20250505', '20250531')
    # print(f"Win Rate: {results['won'].mean():.1%}")
    # print(f"Average P&L: ${results['pnl'].mean():.2f}")
    
    # Example: Find best entry time
    # entry_analysis = analyzer.analyze_entry_times('20250505')
    # best_entry = entry_analysis.loc[entry_analysis['pnl'].idxmax()]
    # print(f"Best entry time: {best_entry['entry_time']}")


if __name__ == "__main__":
    main()