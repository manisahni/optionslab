"""
Comprehensive ORB Backtest with Real Options Data
Runs complete backtest across all available dates
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging
import sys
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))

from backtesting.options_data_loader import OptionsDataLoader
from core.spread_pricer import SpreadPricer
from core.orb_calculator import ORBCalculator
from backtesting.market_analysis import MarketAnalyzer
from backtesting.backtest_utils import (
    calculate_drawdown_metrics,
    calculate_performance_metrics,
    compare_with_option_alpha,
    spy_vs_spx_explanation
)
from backtesting.enhanced_backtest_report import generate_enhanced_report

# Reduce logging verbosity
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class ComprehensiveORBBacktest:
    """
    Complete ORB backtest using real options data
    """
    
    def __init__(self):
        self.options_loader = OptionsDataLoader()
        self.results = {'15min': [], '30min': [], '60min': []}
        self.market_analyzer = None  # Will be initialized when SPY data is loaded
        
    def run_all_backtests(self):
        """Run backtests for all timeframes"""
        
        print("\n" + "="*80)
        print("COMPREHENSIVE ORB BACKTEST WITH REAL OPTIONS DATA")
        print("="*80)
        
        # Get all available dates
        all_dates = self.options_loader.get_available_dates()
        print(f"\nFound {len(all_dates)} days of options data")
        print(f"Date range: {all_dates[0]} to {all_dates[-1]}")
        
        # Load SPY data
        spy_data = self.load_spy_data()
        if spy_data is None:
            return
        
        # Initialize market analyzer
        self.market_analyzer = MarketAnalyzer(spy_data)
        print(f"Initialized market analyzer with {len(self.market_analyzer.daily_data)} days of data")
        
        # Run for each timeframe
        for timeframe in [15, 30, 60]:
            print(f"\n{'='*80}")
            print(f"Running {timeframe}-minute ORB Backtest")
            print("="*80)
            
            results = self.run_timeframe_backtest(
                spy_data, 
                all_dates, 
                timeframe
            )
            
            self.print_results(results, timeframe)
            
            # Save results
            if results['trades']:
                self.save_results(results, timeframe)
        
        # Compare all timeframes
        self.compare_timeframes()
        
        # Generate enhanced report
        self.generate_enhanced_report(spy_data)
    
    def load_spy_data(self):
        """Load SPY price data"""
        spy_path = Path('/Users/nish_macbook/0dte/data/SPY.parquet')
        
        if not spy_path.exists():
            print("SPY data not found!")
            return None
        
        spy_data = pd.read_parquet(spy_path)
        if 'date' in spy_data.columns:
            spy_data.set_index('date', inplace=True)
        
        print(f"Loaded SPY data: {len(spy_data)} bars")
        return spy_data
    
    def run_timeframe_backtest(self, spy_data, dates, timeframe_minutes):
        """Run backtest for specific timeframe"""
        
        orb_calculator = ORBCalculator(timeframe_minutes=timeframe_minutes)
        spread_pricer = SpreadPricer(spread_width=15)
        
        trades = []
        skipped_days = {'no_data': 0, 'invalid_or': 0, 'no_breakout': 0, 'no_options': 0}
        
        with tqdm(total=len(dates), desc=f"{timeframe_minutes}-min ORB") as pbar:
            for date in dates:
                # Load options data
                options_df = self.options_loader.load_day_data(date, use_cache=True)
                if options_df is None:
                    skipped_days['no_data'] += 1
                    pbar.update(1)
                    continue
                
                # Get SPY data for the day
                date_obj = pd.to_datetime(date)
                
                # Handle timezone
                if spy_data.index.tz is not None:
                    date_start = date_obj.tz_localize(spy_data.index.tz)
                    date_end = (date_obj + timedelta(days=1)).tz_localize(spy_data.index.tz)
                else:
                    date_start = date_obj
                    date_end = date_obj + timedelta(days=1)
                
                day_spy = spy_data[(spy_data.index >= date_start) & (spy_data.index < date_end)]
                
                if len(day_spy) < 100:  # Need enough bars
                    skipped_days['no_data'] += 1
                    pbar.update(1)
                    continue
                
                # Calculate opening range
                or_info = orb_calculator.calculate_range(day_spy)
                
                if not or_info or not or_info['valid']:
                    skipped_days['invalid_or'] += 1
                    pbar.update(1)
                    continue
                
                # Look for breakout
                trade = self.find_and_execute_trade(
                    day_spy, 
                    or_info, 
                    options_df, 
                    spread_pricer
                )
                
                if trade:
                    trades.append(trade)
                elif trade is False:
                    skipped_days['no_options'] += 1
                else:
                    skipped_days['no_breakout'] += 1
                
                pbar.update(1)
        
        return {
            'trades': trades,
            'skipped': skipped_days,
            'total_days': len(dates)
        }
    
    def find_and_execute_trade(self, spy_data, or_info, options_df, spread_pricer):
        """Find breakout and execute trade if viable"""
        
        # Get data after OR
        post_or = spy_data[spy_data.index > or_info['end_time']]
        
        if post_or.empty:
            return None
        
        or_high = or_info['high']
        or_low = or_info['low']
        
        # Check each bar for breakout (until 3:30 PM)
        for idx, bar in post_or.iterrows():
            if idx.time() > time(15, 30):
                break
            
            current_price = bar['close']
            
            # Round timestamp to minute for options data and remove timezone
            timestamp = pd.Timestamp(idx).tz_localize(None).floor('min')
            
            # Bullish breakout
            if current_price > or_high + 0.01:
                return self.execute_put_spread(
                    timestamp, or_low, current_price, 
                    options_df, spread_pricer, or_info
                )
            
            # Bearish breakout
            elif current_price < or_low - 0.01:
                return self.execute_call_spread(
                    timestamp, or_high, current_price,
                    options_df, spread_pricer, or_info
                )
        
        return None
    
    def execute_put_spread(self, entry_time, or_low, spy_price, options_df, spread_pricer, or_info):
        """Execute put credit spread for bullish breakout"""
        
        # Find strikes
        short_strike, long_strike = spread_pricer.find_put_spread_strikes(
            options_df, or_low, entry_time
        )
        
        if not short_strike or not long_strike:
            return False
        
        # Calculate entry credit
        entry_spread = spread_pricer.calculate_spread_credit(
            options_df, entry_time, short_strike, long_strike, 'PUT'
        )
        
        if not entry_spread or entry_spread['credit'] < 5:  # Lower minimum to $5
            return False
        
        # Calculate exit value at 3:59 PM (no timezone)
        exit_time = pd.Timestamp(entry_time.date()) + pd.Timedelta(hours=15, minutes=59)
        exit_cost = spread_pricer.calculate_spread_value(
            options_df, exit_time, short_strike, long_strike, 'PUT'
        )
        
        # Calculate P&L
        gross_pnl = entry_spread['credit'] - max(0, exit_cost)
        commission = 0.65 * 4  # 2 legs × 2 trades
        net_pnl = gross_pnl - commission
        
        return {
            'date': entry_time.date(),
            'entry_time': entry_time.time(),
            'exit_time': exit_time.time(),
            'type': 'PUT_SPREAD',
            'direction': 'BULLISH',
            'short_strike': short_strike,
            'long_strike': long_strike,
            'entry_spy': spy_price,
            'entry_credit': entry_spread['credit'],
            'exit_cost': exit_cost,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'or_range': or_info['range'],
            'or_range_pct': or_info['range_pct'],
            'net_delta': entry_spread.get('net_delta', 0),
            'net_vega': entry_spread.get('net_vega', 0)
        }
    
    def execute_call_spread(self, entry_time, or_high, spy_price, options_df, spread_pricer, or_info):
        """Execute call credit spread for bearish breakout"""
        
        # Find strikes
        short_strike, long_strike = spread_pricer.find_call_spread_strikes(
            options_df, or_high, entry_time
        )
        
        if not short_strike or not long_strike:
            return False
        
        # Calculate entry credit
        entry_spread = spread_pricer.calculate_spread_credit(
            options_df, entry_time, short_strike, long_strike, 'CALL'
        )
        
        if not entry_spread or entry_spread['credit'] < 5:  # Lower minimum to $5
            return False
        
        # Calculate exit value at 3:59 PM (no timezone)
        exit_time = pd.Timestamp(entry_time.date()) + pd.Timedelta(hours=15, minutes=59)
        exit_cost = spread_pricer.calculate_spread_value(
            options_df, exit_time, short_strike, long_strike, 'CALL'
        )
        
        # Calculate P&L
        gross_pnl = entry_spread['credit'] - max(0, exit_cost)
        commission = 0.65 * 4
        net_pnl = gross_pnl - commission
        
        return {
            'date': entry_time.date(),
            'entry_time': entry_time.time(),
            'exit_time': exit_time.time(),
            'type': 'CALL_SPREAD',
            'direction': 'BEARISH',
            'short_strike': short_strike,
            'long_strike': long_strike,
            'entry_spy': spy_price,
            'entry_credit': entry_spread['credit'],
            'exit_cost': exit_cost,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'or_range': or_info['range'],
            'or_range_pct': or_info['range_pct'],
            'net_delta': entry_spread.get('net_delta', 0),
            'net_vega': entry_spread.get('net_vega', 0)
        }
    
    def print_results(self, results, timeframe):
        """Print backtest results"""
        
        trades = results['trades']
        skipped = results['skipped']
        
        if not trades:
            print(f"\nNo trades executed for {timeframe}-min ORB")
            print(f"Skipped days: {skipped}")
            return
        
        df = pd.DataFrame(trades)
        
        # Calculate metrics
        winning_trades = df[df['net_pnl'] > 0]
        losing_trades = df[df['net_pnl'] <= 0]
        
        total_trades = len(df)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_pnl = df['net_pnl'].sum()
        avg_pnl = df['net_pnl'].mean()
        
        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['net_pnl'].mean()) if len(losing_trades) > 0 else 0
        
        # Profit factor
        total_wins = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Max drawdown
        df['cumulative'] = df['net_pnl'].cumsum()
        running_max = df['cumulative'].expanding().max()
        drawdown = df['cumulative'] - running_max
        max_drawdown = drawdown.min()
        
        print(f"\n{timeframe}-MINUTE ORB RESULTS")
        print("-" * 40)
        print(f"Total Trades:    {total_trades}")
        print(f"Winning Trades:  {len(winning_trades)}")
        print(f"Losing Trades:   {len(losing_trades)}")
        print(f"Win Rate:        {win_rate:.1%}")
        print(f"\nTotal P&L:       ${total_pnl:,.0f}")
        print(f"Average P&L:     ${avg_pnl:.2f}")
        print(f"Average Win:     ${avg_win:.2f}")
        print(f"Average Loss:    ${avg_loss:.2f}")
        print(f"\nProfit Factor:   {profit_factor:.2f}")
        print(f"Max Drawdown:    ${max_drawdown:,.0f}")
        print(f"\nAvg Entry Credit: ${df['entry_credit'].mean():.2f}")
        print(f"Avg OR Range:    {df['or_range_pct'].mean():.3%}")
        
        print(f"\nDays Analyzed:   {results['total_days']}")
        print(f"Days Traded:     {total_trades}")
        print(f"Days Skipped:    {sum(skipped.values())}")
        print(f"  - No data:     {skipped['no_data']}")
        print(f"  - Invalid OR:  {skipped['invalid_or']}")
        print(f"  - No breakout: {skipped['no_breakout']}")
        print(f"  - No options:  {skipped['no_options']}")
        
        # Store for comparison
        self.results[f'{timeframe}min'] = {
            'df': df,
            'metrics': {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown
            }
        }
    
    def save_results(self, results, timeframe):
        """Save results to CSV"""
        df = pd.DataFrame(results['trades'])
        output_path = f'/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/real_orb_{timeframe}min.csv'
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")
    
    def compare_timeframes(self):
        """Compare all timeframe results"""
        
        print("\n" + "="*80)
        print("COMPARISON OF ALL TIMEFRAMES")
        print("="*80)
        
        comparison = []
        
        for timeframe in ['15min', '30min', '60min']:
            if timeframe in self.results and self.results[timeframe]:
                metrics = self.results[timeframe]['metrics']
                comparison.append({
                    'Timeframe': timeframe,
                    'Trades': metrics['total_trades'],
                    'Win Rate': f"{metrics['win_rate']:.1%}",
                    'Total P&L': f"${metrics['total_pnl']:,.0f}",
                    'Avg P&L': f"${metrics['avg_pnl']:.2f}",
                    'PF': f"{metrics['profit_factor']:.2f}",
                    'Max DD': f"${metrics['max_drawdown']:,.0f}"
                })
        
        if comparison:
            df_comp = pd.DataFrame(comparison)
            print("\nBacktest Results:")
            print(df_comp.to_string(index=False))
            
            print("\n" + "="*80)
            print("COMPARISON TO OPTION ALPHA ARTICLE")
            print("="*80)
            
            article_results = pd.DataFrame([
                {'Timeframe': '15min', 'Win Rate': '78.1%', 'Total P&L': '$19,053', 'Avg P&L': '$35', 'PF': '1.17'},
                {'Timeframe': '30min', 'Win Rate': '82.6%', 'Total P&L': '$19,555', 'Avg P&L': '$31', 'PF': '1.19'},
                {'Timeframe': '60min', 'Win Rate': '88.8%', 'Total P&L': '$30,708', 'Avg P&L': '$51', 'PF': '1.59'}
            ])
            
            print("\nOption Alpha Results:")
            print(article_results.to_string(index=False))
            
            print("\n" + "="*80)
            print("KEY INSIGHTS")
            print("="*80)
            print("""
1. Our results now use REAL option prices (bid/ask)
2. Credits are calculated from actual market data
3. P&L includes commission costs
4. Results should be closer to Option Alpha's findings

Note: Differences may still exist due to:
- Different date ranges
- Data quality/completeness
- Execution assumptions
- Slippage modeling
            """)
    
    def generate_enhanced_report(self, spy_data):
        """Generate enhanced report with all analytics"""
        
        print("\n" + "=" * 80)
        print("GENERATING ENHANCED REPORT...")
        print("=" * 80)
        
        # Prepare results dictionary with DataFrames
        results_dict = {}
        
        for timeframe in ['15min', '30min', '60min']:
            if timeframe in self.results and self.results[timeframe].get('df') is not None:
                results_dict[timeframe] = self.results[timeframe]['df']
        
        # Generate the enhanced report
        if results_dict:
            generate_enhanced_report(results_dict, spy_data)
        else:
            print("No results available for enhanced report")


def main():
    """Run comprehensive backtest"""
    backtester = ComprehensiveORBBacktest()
    backtester.run_all_backtests()


if __name__ == "__main__":
    main()