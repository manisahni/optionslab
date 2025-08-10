#!/usr/bin/env python3
"""
Comprehensive 0DTE Strangle Backtesting Tool
Step-by-step calculation with full verification
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import csv

# Add the market_data directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase


class StrangleBacktester:
    """Accurate backtesting for 0DTE strangle strategies"""
    
    def __init__(self):
        self.db = ZeroDTESPYOptionsDatabase()
        self.trades = []
        
    def find_strangle_for_delta(self, df, timestamp, delta_target=0.30):
        """Find the best strangle for given delta target"""
        
        # Filter to specific timestamp
        time_df = df[df['timestamp'] == timestamp].copy()
        if time_df.empty:
            return None
            
        # Get current SPY price (convert from cents if needed)
        spy_price = time_df.iloc[0]['underlying_price']
        if spy_price > 1000:  # Price is in cents
            spy_price = spy_price / 100
        
        # Separate calls and puts
        calls = time_df[time_df['right'] == 'CALL'].copy()
        puts = time_df[time_df['right'] == 'PUT'].copy()
        
        if calls.empty or puts.empty:
            return None
        
        # Find calls closest to delta target
        calls['delta_diff'] = abs(calls['delta'] - delta_target)
        best_call = calls.nsmallest(1, 'delta_diff').iloc[0]
        
        # Find puts closest to delta target (remember put deltas are negative)
        puts['delta_diff'] = abs(abs(puts['delta']) - delta_target)
        best_put = puts.nsmallest(1, 'delta_diff').iloc[0]
        
        # Verify bid/ask validity
        if (best_call['bid'] <= 0 or best_call['ask'] <= 0 or 
            best_put['bid'] <= 0 or best_put['ask'] <= 0):
            return None
        
        # Verify bid < ask
        if best_call['bid'] >= best_call['ask'] or best_put['bid'] >= best_put['ask']:
            return None
        
        return {
            'timestamp': timestamp,
            'spy_price': spy_price,
            'call_strike': best_call['strike'],
            'call_bid': best_call['bid'],
            'call_ask': best_call['ask'],
            'call_delta': best_call['delta'],
            'put_strike': best_put['strike'],
            'put_bid': best_put['bid'],
            'put_ask': best_put['ask'],
            'put_delta': best_put['delta']
        }
    
    def execute_trade(self, date, entry_time="10:00", exit_time="15:50", delta_target=0.30):
        """Execute a single day's strangle trade"""
        
        # Load data for the date
        df = self.db.load_zero_dte_data(date)
        if df.empty:
            return None
        
        # Format timestamps
        entry_ts = f"{date[:4]}-{date[4:6]}-{date[6:]}T{entry_time}:00"
        exit_ts = f"{date[:4]}-{date[4:6]}-{date[6:]}T{exit_time}:00"
        
        # Find entry strangle
        entry = self.find_strangle_for_delta(df, entry_ts, delta_target)
        if not entry:
            return None
        
        # Find exit prices (same strikes as entry)
        exit_df = df[(df['timestamp'] == exit_ts) & 
                     ((df['strike'] == entry['call_strike']) | 
                      (df['strike'] == entry['put_strike']))]
        
        if len(exit_df) < 2:
            return None
        
        # Get exit prices
        exit_call = exit_df[(exit_df['strike'] == entry['call_strike']) & 
                           (exit_df['right'] == 'CALL')].iloc[0]
        exit_put = exit_df[(exit_df['strike'] == entry['put_strike']) & 
                          (exit_df['right'] == 'PUT')].iloc[0]
        
        # Calculate P&L
        entry_credit = entry['call_bid'] + entry['put_bid']
        exit_debit = exit_call['ask'] + exit_put['ask']
        pnl = entry_credit - exit_debit
        pnl_pct = (pnl / entry_credit) * 100 if entry_credit > 0 else 0
        
        # SPY movement
        exit_spy = exit_call['underlying_price']
        if exit_spy > 1000:  # Convert from cents
            exit_spy = exit_spy / 100
        spy_move = exit_spy - entry['spy_price']
        spy_move_pct = (spy_move / entry['spy_price']) * 100
        
        trade = {
            'date': date,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_spy': round(entry['spy_price'], 2),
            'exit_spy': round(exit_spy, 2),
            'spy_move': round(spy_move, 2),
            'spy_move_pct': round(spy_move_pct, 2),
            'call_strike': entry['call_strike'],
            'put_strike': entry['put_strike'],
            'call_delta': round(entry['call_delta'], 3),
            'put_delta': round(entry['put_delta'], 3),
            'entry_credit': round(entry_credit, 2),
            'exit_debit': round(exit_debit, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'won': pnl > 0,
            # Breakdown for verification
            'call_bid': round(entry['call_bid'], 2),
            'call_ask_entry': round(entry['call_ask'], 2),
            'put_bid': round(entry['put_bid'], 2),
            'put_ask_entry': round(entry['put_ask'], 2),
            'call_ask_exit': round(exit_call['ask'], 2),
            'put_ask_exit': round(exit_put['ask'], 2)
        }
        
        return trade
    
    def backtest_strategy(self, start_date, end_date, entry_time="10:00", 
                         exit_time="15:50", delta_target=0.30, verbose=True):
        """Run backtest over date range"""
        
        # Get all dates in range
        all_dates = sorted(self.db.metadata.get('downloaded_dates', []))
        test_dates = [d for d in all_dates if start_date <= d <= end_date]
        
        print(f"\nBacktesting {len(test_dates)} days from {start_date} to {end_date}")
        print(f"Parameters: Entry={entry_time}, Exit={exit_time}, Delta={delta_target}")
        print("-" * 80)
        
        self.trades = []
        
        for i, date in enumerate(test_dates):
            if verbose and i % 10 == 0:
                print(f"Processing day {i+1}/{len(test_dates)}...")
            
            trade = self.execute_trade(date, entry_time, exit_time, delta_target)
            if trade:
                self.trades.append(trade)
        
        return self.analyze_results()
    
    def analyze_results(self):
        """Analyze backtest results"""
        
        if not self.trades:
            return None
        
        df = pd.DataFrame(self.trades)
        
        # Calculate metrics
        total_trades = len(df)
        winning_trades = len(df[df['won']])
        win_rate = (winning_trades / total_trades) * 100
        
        avg_win = df[df['won']]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[~df['won']]['pnl'].mean() if (total_trades - winning_trades) > 0 else 0
        
        total_pnl = df['pnl'].sum()
        avg_pnl = df['pnl'].mean()
        avg_pnl_pct = df['pnl_pct'].mean()
        
        # Sharpe ratio (annualized)
        if df['pnl_pct'].std() > 0:
            daily_sharpe = df['pnl_pct'].mean() / df['pnl_pct'].std()
            annual_sharpe = daily_sharpe * np.sqrt(252)
        else:
            annual_sharpe = 0
        
        # Max drawdown
        df['cumulative_pnl'] = df['pnl'].cumsum()
        df['running_max'] = df['cumulative_pnl'].cummax()
        df['drawdown'] = df['cumulative_pnl'] - df['running_max']
        max_drawdown = df['drawdown'].min()
        
        # Consecutive losses
        df['loss'] = ~df['won']
        df['loss_streak'] = df['loss'].groupby((df['loss'] != df['loss'].shift()).cumsum()).cumsum()
        max_consecutive_losses = df['loss_streak'].max()
        
        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else np.inf,
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(avg_pnl, 2),
            'avg_pnl_pct': round(avg_pnl_pct, 2),
            'sharpe_ratio': round(annual_sharpe, 2),
            'max_drawdown': round(max_drawdown, 2),
            'max_consecutive_losses': int(max_consecutive_losses),
            'best_trade': round(df['pnl'].max(), 2),
            'worst_trade': round(df['pnl'].min(), 2),
            'avg_spy_move': round(df['spy_move_pct'].abs().mean(), 2)
        }
        
        return results
    
    def print_sample_trades(self, n=5):
        """Print sample trades for verification"""
        
        if not self.trades:
            return
        
        print(f"\nSAMPLE TRADES (First {n}):")
        print("=" * 120)
        
        for i, trade in enumerate(self.trades[:n]):
            print(f"\nTrade {i+1} - {trade['date']}:")
            print(f"  SPY: ${trade['entry_spy']} → ${trade['exit_spy']} ({trade['spy_move_pct']:+.2f}%)")
            print(f"  Strikes: {trade['call_strike']} Call (Δ={trade['call_delta']}) / {trade['put_strike']} Put (Δ={trade['put_delta']})")
            print(f"  Entry: Call bid=${trade['call_bid']}, Put bid=${trade['put_bid']} = ${trade['entry_credit']} credit")
            print(f"  Exit: Call ask=${trade['call_ask_exit']}, Put ask=${trade['put_ask_exit']} = ${trade['exit_debit']} debit")
            print(f"  P&L: ${trade['pnl']} ({trade['pnl_pct']:+.1f}%) - {'WIN' if trade['won'] else 'LOSS'}")
    
    def export_trades(self, filename='strangle_trades.csv'):
        """Export all trades to CSV"""
        
        if not self.trades:
            return
        
        df = pd.DataFrame(self.trades)
        df.to_csv(filename, index=False)
        print(f"\nExported {len(df)} trades to {filename}")


def main():
    """Run comprehensive backtest"""
    
    backtester = StrangleBacktester()
    
    # Test with small sample first
    print("\n" + "="*80)
    print("TESTING WITH 5-DAY SAMPLE")
    print("="*80)
    
    results = backtester.backtest_strategy("20250728", "20250801", 
                                          entry_time="10:00", 
                                          delta_target=0.30,
                                          verbose=False)
    
    if results:
        print(f"\nRESULTS SUMMARY:")
        for key, value in results.items():
            print(f"  {key}: {value}")
        
        backtester.print_sample_trades(3)
    
    # Ask user if they want to run full backtest
    print(f"\n{'='*80}")
    response = input("Run full backtest on 62 days? (y/n): ")
    
    if response.lower() == 'y':
        print(f"\n{'='*80}")
        print("RUNNING FULL BACKTEST")
        print("="*80)
        
        # Test multiple parameter combinations
        param_combinations = [
            (0.15, "09:35"), (0.15, "10:00"), (0.15, "10:30"),
            (0.20, "09:35"), (0.20, "10:00"), (0.20, "10:30"),
            (0.25, "09:35"), (0.25, "10:00"), (0.25, "10:30"),
            (0.30, "09:35"), (0.30, "10:00"), (0.30, "10:30"),
        ]
        
        all_results = []
        
        for delta, entry_time in param_combinations:
            print(f"\nTesting Delta={delta}, Entry={entry_time}")
            
            results = backtester.backtest_strategy("20250505", "20250801",
                                                  entry_time=entry_time,
                                                  delta_target=delta,
                                                  verbose=False)
            
            if results:
                results['delta'] = delta
                results['entry_time'] = entry_time
                all_results.append(results)
                print(f"  Win Rate: {results['win_rate']}%, Sharpe: {results['sharpe_ratio']}, Total P&L: ${results['total_pnl']}")
        
        # Export detailed results
        backtester.export_trades('full_backtest_trades.csv')
        
        # Print best parameters
        if all_results:
            print(f"\n{'='*80}")
            print("OPTIMAL PARAMETERS:")
            print("="*80)
            
            # Sort by Sharpe ratio
            all_results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
            
            print("\nTop 3 by Sharpe Ratio:")
            for i, r in enumerate(all_results[:3]):
                print(f"{i+1}. Delta={r['delta']}, Entry={r['entry_time']}: Sharpe={r['sharpe_ratio']}, Win={r['win_rate']}%, Total=${r['total_pnl']}")


if __name__ == "__main__":
    main()