"""
Real Options Backtester for ORB Strategy
Uses actual 0DTE options data for accurate backtesting
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import sys
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))

from backtesting.options_data_loader import OptionsDataLoader
from core.spread_pricer import SpreadPricer
from core.orb_calculator import ORBCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealOptionsBacktester:
    """
    Backtest ORB strategy using real 0DTE options data
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 position_size: int = 1,
                 commission_per_contract: float = 0.65):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital
            position_size: Number of contracts per trade
            commission_per_contract: Commission per option contract
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.commission = commission_per_contract
        
        # Initialize components
        self.options_loader = OptionsDataLoader()
        self.spread_pricer = SpreadPricer(spread_width=15)
        
        # Track results
        self.trades = []
        self.current_capital = initial_capital
        
        logger.info(f"Real Options Backtester initialized with ${initial_capital:,.0f}")
    
    def run_backtest(self, spy_data: pd.DataFrame, 
                    timeframe_minutes: int = 60,
                    start_date: str = None,
                    end_date: str = None) -> Dict:
        """
        Run complete backtest with real options data
        
        Args:
            spy_data: SPY price data for OR calculation
            timeframe_minutes: OR timeframe (15, 30, 60)
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            Dict with backtest results
        """
        # Initialize OR calculator
        orb_calculator = ORBCalculator(timeframe_minutes=timeframe_minutes)
        
        # Get available option dates
        available_dates = self.options_loader.get_available_dates()
        
        if start_date:
            available_dates = [d for d in available_dates if d >= start_date]
        if end_date:
            available_dates = [d for d in available_dates if d <= end_date]
        
        logger.info(f"Running {timeframe_minutes}-min ORB backtest on {len(available_dates)} days")
        
        # Process each day
        with tqdm(total=len(available_dates), desc="Backtesting") as pbar:
            for date in available_dates:
                self.process_day(date, spy_data, orb_calculator)
                pbar.update(1)
        
        # Calculate metrics
        results = self.calculate_metrics(timeframe_minutes)
        
        return results
    
    def process_day(self, date: str, spy_data: pd.DataFrame, 
                   orb_calculator: ORBCalculator) -> Optional[Dict]:
        """
        Process single trading day
        
        Args:
            date: Date to process (YYYY-MM-DD)
            spy_data: SPY price data
            orb_calculator: OR calculator instance
            
        Returns:
            Trade details if executed
        """
        # Load options data for the day
        options_df = self.options_loader.load_day_data(date)
        if options_df is None:
            return None
        
        # Get SPY data for the day
        date_obj = pd.to_datetime(date)
        
        # Handle timezone aware/naive comparison
        if spy_data.index.tz is not None:
            date_start = date_obj.tz_localize(spy_data.index.tz)
            date_end = (date_obj + timedelta(days=1)).tz_localize(spy_data.index.tz)
        else:
            date_start = date_obj
            date_end = date_obj + timedelta(days=1)
        
        day_spy = spy_data[(spy_data.index >= date_start) & (spy_data.index < date_end)]
        
        if day_spy.empty:
            return None
        
        # Calculate opening range
        or_info = orb_calculator.calculate_range(day_spy)
        
        if not or_info or not or_info['valid']:
            return None
        
        # Look for breakout after OR
        breakout = self.detect_breakout(day_spy, or_info, options_df)
        
        if breakout:
            # Execute trade
            trade = self.execute_trade(breakout, or_info, options_df)
            
            if trade:
                self.trades.append(trade)
                self.current_capital += trade['net_pnl']
                return trade
        
        return None
    
    def detect_breakout(self, spy_data: pd.DataFrame, or_info: Dict, 
                       options_df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect breakout and check if options are tradeable
        
        Args:
            spy_data: SPY price data for the day
            or_info: Opening range information
            options_df: Options data for the day
            
        Returns:
            Breakout details if detected
        """
        # Get data after OR period
        post_or = spy_data[spy_data.index > or_info['end_time']]
        
        if post_or.empty:
            return None
        
        or_high = or_info['high']
        or_low = or_info['low']
        
        # Check each bar for breakout
        for idx, bar in post_or.iterrows():
            # Skip if after 3:30 PM
            if idx.time() > time(15, 30):
                break
            
            current_price = bar['close']
            
            # Convert index to timestamp for options data
            timestamp = pd.Timestamp(idx).floor('min')  # Round to minute
            
            # Bullish breakout
            if current_price > or_high + 0.01:
                # Find put spread strikes
                short_strike, long_strike = self.spread_pricer.find_put_spread_strikes(
                    options_df, or_low, timestamp
                )
                
                if short_strike and long_strike:
                    # Calculate spread credit
                    spread = self.spread_pricer.calculate_spread_credit(
                        options_df, timestamp, short_strike, long_strike, 'PUT'
                    )
                    
                    if spread and spread['credit'] > 10:  # Minimum $10 credit
                        return {
                            'type': 'bullish',
                            'entry_time': timestamp,
                            'spy_price': current_price,
                            'spread': spread
                        }
            
            # Bearish breakout
            elif current_price < or_low - 0.01:
                # Find call spread strikes
                short_strike, long_strike = self.spread_pricer.find_call_spread_strikes(
                    options_df, or_high, timestamp
                )
                
                if short_strike and long_strike:
                    # Calculate spread credit
                    spread = self.spread_pricer.calculate_spread_credit(
                        options_df, timestamp, short_strike, long_strike, 'CALL'
                    )
                    
                    if spread and spread['credit'] > 10:  # Minimum $10 credit
                        return {
                            'type': 'bearish',
                            'entry_time': timestamp,
                            'spy_price': current_price,
                            'spread': spread
                        }
        
        return None
    
    def execute_trade(self, breakout: Dict, or_info: Dict, 
                     options_df: pd.DataFrame) -> Dict:
        """
        Execute trade and track through exit
        
        Args:
            breakout: Breakout details
            or_info: Opening range information
            options_df: Options data
            
        Returns:
            Complete trade details
        """
        spread = breakout['spread']
        entry_time = breakout['entry_time']
        entry_credit = spread['credit']
        
        # Find exit (3:59 PM or earlier if hit stop/target)
        exit_time = pd.Timestamp(entry_time.date()) + pd.Timedelta(hours=15, minutes=59)
        
        # Calculate exit cost
        exit_cost = self.spread_pricer.calculate_spread_value(
            options_df, exit_time,
            spread['short_strike'], spread['long_strike'],
            spread['right']
        )
        
        # If exit cost is 0 or negative, spread expired worthless (we keep credit)
        if exit_cost <= 0:
            exit_cost = 0
            exit_reason = 'expired_worthless'
        else:
            exit_reason = 'time_exit'
        
        # Calculate P&L
        pnl = self.spread_pricer.calculate_pnl(
            entry_credit, exit_cost, self.position_size
        )
        
        trade = {
            'date': entry_time.date(),
            'entry_time': entry_time,
            'exit_time': exit_time,
            'type': spread['right'] + '_SPREAD',
            'direction': breakout['type'],
            'strikes': f"{spread['short_strike']}/{spread['long_strike']}",
            'entry_credit': entry_credit,
            'exit_cost': exit_cost,
            'contracts': self.position_size,
            'gross_pnl': pnl['gross_pnl'],
            'commission': pnl['commission'],
            'net_pnl': pnl['net_pnl'],
            'exit_reason': exit_reason,
            'or_range': or_info['range'],
            'or_range_pct': or_info['range_pct'],
            'entry_spy': breakout['spy_price'],
            'entry_delta': spread['net_delta'],
            'entry_vega': spread['net_vega']
        }
        
        return trade
    
    def calculate_metrics(self, timeframe: int) -> Dict:
        """Calculate performance metrics"""
        
        if not self.trades:
            return {
                'timeframe': f'{timeframe}min',
                'status': 'No trades executed',
                'total_trades': 0
            }
        
        df = pd.DataFrame(self.trades)
        
        # Calculate metrics
        winning_trades = df[df['net_pnl'] > 0]
        losing_trades = df[df['net_pnl'] <= 0]
        
        total_trades = len(df)
        win_rate = len(winning_trades) / total_trades
        
        total_pnl = df['net_pnl'].sum()
        avg_pnl = df['net_pnl'].mean()
        
        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades['net_pnl'].mean()) if len(losing_trades) > 0 else 0
        
        # Profit factor
        total_wins = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Max drawdown
        df['cumulative_pnl'] = df['net_pnl'].cumsum()
        running_max = df['cumulative_pnl'].expanding().max()
        drawdown = df['cumulative_pnl'] - running_max
        max_drawdown = drawdown.min()
        
        return {
            'timeframe': f'{timeframe}min',
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'final_capital': self.current_capital,
            'total_return': (self.current_capital - self.initial_capital) / self.initial_capital,
            'avg_credit': df['entry_credit'].mean(),
            'trades_df': df
        }
    
    def print_report(self, results: Dict):
        """Print formatted backtest report"""
        
        print("\n" + "="*70)
        print(f"REAL OPTIONS BACKTEST - {results['timeframe'].upper()}")
        print("="*70)
        
        if 'status' in results:
            print(f"\n{results['status']}")
            return
        
        print(f"\nTotal Trades:    {results['total_trades']}")
        print(f"Winning Trades:  {results['winning_trades']}")
        print(f"Losing Trades:   {results['losing_trades']}")
        print(f"Win Rate:        {results['win_rate']:.1%}")
        
        print(f"\nTotal P&L:       ${results['total_pnl']:,.0f}")
        print(f"Average P&L:     ${results['avg_pnl']:.0f}")
        print(f"Average Win:     ${results['avg_win']:.0f}")
        print(f"Average Loss:    ${results['avg_loss']:.0f}")
        
        print(f"\nProfit Factor:   {results['profit_factor']:.2f}")
        print(f"Max Drawdown:    ${results['max_drawdown']:,.0f}")
        print(f"Total Return:    {results['total_return']:.1%}")
        
        print(f"\nAvg Credit:      ${results['avg_credit']:.0f}")
        
        # Comparison to Option Alpha
        print("\n" + "="*70)
        print("COMPARISON TO OPTION ALPHA RESULTS")
        print("="*70)
        
        if '60min' in results['timeframe']:
            expected = {'win_rate': 0.888, 'avg_pnl': 51, 'pf': 1.59}
        elif '30min' in results['timeframe']:
            expected = {'win_rate': 0.826, 'avg_pnl': 31, 'pf': 1.19}
        else:  # 15min
            expected = {'win_rate': 0.781, 'avg_pnl': 35, 'pf': 1.17}
        
        print(f"Win Rate:   Expected {expected['win_rate']:.1%} | Actual {results['win_rate']:.1%}")
        print(f"Avg P&L:    Expected ${expected['avg_pnl']} | Actual ${results['avg_pnl']:.0f}")
        print(f"Profit Factor: Expected {expected['pf']:.2f} | Actual {results['profit_factor']:.2f}")


def main():
    """Run real options backtest"""
    
    print("Loading SPY data...")
    
    # Load SPY data
    spy_path = Path('/Users/nish_macbook/0dte/data/SPY.parquet')
    if spy_path.exists():
        spy_data = pd.read_parquet(spy_path)
        if 'date' in spy_data.columns:
            spy_data.set_index('date', inplace=True)
    else:
        print("SPY data not found")
        return
    
    # Initialize backtester
    backtester = RealOptionsBacktester(
        initial_capital=100000,
        position_size=1  # 1 contract per trade
    )
    
    # Run 60-minute backtest
    print("\nRunning 60-minute ORB backtest with REAL options data...")
    results = backtester.run_backtest(
        spy_data,
        timeframe_minutes=60,
        start_date='2024-08-01',
        end_date='2024-08-31'
    )
    
    # Print report
    backtester.print_report(results)
    
    # Save trades
    if 'trades_df' in results and not results['trades_df'].empty:
        output_path = '/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/real_options_60min.csv'
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        results['trades_df'].to_csv(output_path, index=False)
        print(f"\nTrades saved to: {output_path}")


if __name__ == "__main__":
    main()