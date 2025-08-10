"""
ORB Strategy Backtester
Comprehensive backtesting engine for Opening Range Breakout strategies
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import sys
from pathlib import Path
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.orb_calculator import ORBCalculator
from core.breakout_detector import BreakoutDetector
from core.position_builder import CreditSpreadBuilder
from strategies.orb_60min import ORB60MinStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ORBBacktester:
    """
    Comprehensive backtesting engine for ORB strategies
    Replicates the article's methodology for accurate comparison
    """
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 commission_per_contract: float = 0.65,
                 slippage_per_contract: float = 0.02):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital
            commission_per_contract: Commission per option contract
            slippage_per_contract: Slippage estimate per contract
        """
        self.initial_capital = initial_capital
        self.commission = commission_per_contract
        self.slippage = slippage_per_contract
        
        # Track performance
        self.trades = []
        self.daily_returns = []
        self.equity_curve = [initial_capital]
        self.current_capital = initial_capital
        
        logger.info(f"ORB Backtester initialized with ${initial_capital:,.0f}")
    
    def run_backtest(self, data: pd.DataFrame, 
                    strategy_type: str = '60min',
                    start_date: str = None,
                    end_date: str = None) -> Dict:
        """
        Run complete backtest
        
        Args:
            data: DataFrame with OHLCV data
            strategy_type: '15min', '30min', or '60min'
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            Dict with backtest results
        """
        # Filter date range (handle timezone-aware data)
        if start_date:
            start_dt = pd.to_datetime(start_date)
            if data.index.tz is not None:
                start_dt = start_dt.tz_localize(data.index.tz)
            data = data[data.index >= start_dt]
        if end_date:
            end_dt = pd.to_datetime(end_date)
            if data.index.tz is not None:
                end_dt = end_dt.tz_localize(data.index.tz)
            data = data[data.index <= end_dt]
        
        # Initialize strategy based on type
        if strategy_type == '60min':
            strategy = ORB60MinStrategy()
        elif strategy_type == '30min':
            # Would implement ORB30MinStrategy
            strategy = ORB60MinStrategy()
            strategy.orb_calculator.timeframe = 30
        elif strategy_type == '15min':
            # Would implement ORB15MinStrategy
            strategy = ORB60MinStrategy()
            strategy.orb_calculator.timeframe = 15
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        # Get unique trading days
        trading_days = data.index.normalize().unique()
        
        logger.info(f"Running {strategy_type} backtest on {len(trading_days)} days")
        
        # Progress bar
        with tqdm(total=len(trading_days), desc="Backtesting") as pbar:
            for date in trading_days:
                # Get day's data
                day_data = data[data.index.date == date.date()]
                
                if len(day_data) < 390:  # Skip incomplete days
                    pbar.update(1)
                    continue
                
                # Reset strategy for new day
                strategy.reset_daily_state()
                
                # Track daily P&L
                day_start_capital = self.current_capital
                
                # Process each bar
                for idx, bar in day_data.iterrows():
                    action = strategy.process_bar(bar, day_data, self.current_capital)
                    
                    if action['action'] == 'enter':
                        self.record_entry(action, idx)
                    elif action['action'] == 'close':
                        self.record_exit(action, idx)
                
                # Calculate daily return
                daily_return = (self.current_capital - day_start_capital) / day_start_capital
                self.daily_returns.append({
                    'date': date,
                    'return': daily_return,
                    'capital': self.current_capital
                })
                self.equity_curve.append(self.current_capital)
                
                pbar.update(1)
        
        # Calculate metrics
        results = self.calculate_metrics(strategy_type)
        
        return results
    
    def record_entry(self, action: Dict, timestamp):
        """Record trade entry"""
        position = action['position']
        
        # Calculate commission
        commission_cost = position['num_contracts'] * 2 * self.commission  # 2 legs
        
        # Record pending trade
        self.trades.append({
            'entry_time': timestamp,
            'exit_time': None,
            'type': position['type'],
            'direction': position['direction'],
            'strikes': f"{position['short_strike']}/{position['long_strike']}",
            'contracts': position['num_contracts'],
            'credit': position['estimated_credit'],
            'commission_entry': commission_cost,
            'status': 'open',
            'entry_price': position['underlying_price']
        })
    
    def record_exit(self, action: Dict, timestamp):
        """Record trade exit"""
        if not self.trades or self.trades[-1]['status'] != 'open':
            return
        
        trade = self.trades[-1]
        
        # Calculate commission for exit
        commission_cost = trade['contracts'] * 2 * self.commission
        
        # Calculate slippage
        slippage_cost = trade['contracts'] * 2 * self.slippage * 100
        
        # Net P&L
        gross_pnl = action.get('pnl', 0)
        net_pnl = gross_pnl - trade['commission_entry'] - commission_cost - slippage_cost
        
        # Update trade record
        trade['exit_time'] = timestamp
        trade['exit_reason'] = action.get('reason', 'unknown')
        trade['gross_pnl'] = gross_pnl
        trade['net_pnl'] = net_pnl
        trade['commission_exit'] = commission_cost
        trade['slippage'] = slippage_cost
        trade['status'] = 'closed'
        
        # Update capital
        self.current_capital += net_pnl
    
    def calculate_metrics(self, strategy_type: str) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        closed_trades = [t for t in self.trades if t['status'] == 'closed']
        
        if not closed_trades:
            return {
                'strategy': strategy_type,
                'status': 'No trades executed',
                'total_trades': 0
            }
        
        # Convert to DataFrame for easier analysis
        trades_df = pd.DataFrame(closed_trades)
        
        # Calculate metrics
        winning_trades = trades_df[trades_df['net_pnl'] > 0]
        losing_trades = trades_df[trades_df['net_pnl'] <= 0]
        
        total_pnl = trades_df['net_pnl'].sum()
        gross_pnl = trades_df['gross_pnl'].sum()
        total_commission = trades_df['commission_entry'].sum() + trades_df['commission_exit'].sum()
        total_slippage = trades_df['slippage'].sum()
        
        # Win rate
        win_rate = len(winning_trades) / len(trades_df)
        
        # Average P&L
        avg_pnl = trades_df['net_pnl'].mean()
        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Profit factor
        total_wins = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Max drawdown
        equity_curve = pd.Series(self.equity_curve)
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        max_drawdown_dollars = (equity_curve - rolling_max).min()
        
        # Sharpe ratio (annualized)
        if self.daily_returns:
            returns_df = pd.DataFrame(self.daily_returns)
            daily_returns = returns_df['return']
            
            if len(daily_returns) > 1:
                sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        # Exit reason analysis
        exit_reasons = trades_df['exit_reason'].value_counts().to_dict()
        
        # Time analysis
        if 'entry_time' in trades_df.columns:
            trades_df['entry_hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour
            entry_hours = trades_df['entry_hour'].value_counts().to_dict()
        else:
            entry_hours = {}
        
        results = {
            'strategy': strategy_type,
            'start_date': trades_df['entry_time'].min(),
            'end_date': trades_df['exit_time'].max(),
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_return': (self.current_capital - self.initial_capital) / self.initial_capital,
            
            # Trade statistics
            'total_trades': len(trades_df),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            
            # P&L metrics
            'gross_pnl': gross_pnl,
            'total_commission': total_commission,
            'total_slippage': total_slippage,
            'net_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            
            # Risk metrics
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'max_drawdown_dollars': max_drawdown_dollars,
            
            # Additional analysis
            'exit_reasons': exit_reasons,
            'entry_hours': entry_hours,
            
            # Detailed trades
            'trades': trades_df
        }
        
        return results
    
    def print_report(self, results: Dict):
        """Print formatted backtest report"""
        
        print("\n" + "="*70)
        print(f"ORB BACKTEST REPORT - {results['strategy'].upper()}")
        print("="*70)
        
        if 'status' in results:
            print(f"\n{results['status']}")
            return
        
        # Overview
        print(f"\nPeriod: {results['start_date']} to {results['end_date']}")
        print(f"Initial Capital: ${results['initial_capital']:,.0f}")
        print(f"Final Capital:   ${results['final_capital']:,.0f}")
        print(f"Total Return:    {results['total_return']:.1%}")
        
        # Trade Statistics
        print(f"\n--- Trade Statistics ---")
        print(f"Total Trades:    {results['total_trades']}")
        print(f"Winning Trades:  {results['winning_trades']}")
        print(f"Losing Trades:   {results['losing_trades']}")
        print(f"Win Rate:        {results['win_rate']:.1%}")
        
        # P&L Analysis
        print(f"\n--- P&L Analysis ---")
        print(f"Gross P&L:       ${results['gross_pnl']:,.0f}")
        print(f"Commission:      ${results['total_commission']:,.0f}")
        print(f"Slippage:        ${results['total_slippage']:,.0f}")
        print(f"Net P&L:         ${results['net_pnl']:,.0f}")
        print(f"Avg P&L:         ${results['avg_pnl']:.0f}")
        print(f"Avg Win:         ${results['avg_win']:.0f}")
        print(f"Avg Loss:        ${results['avg_loss']:.0f}")
        
        # Risk Metrics
        print(f"\n--- Risk Metrics ---")
        print(f"Profit Factor:   {results['profit_factor']:.2f}")
        print(f"Sharpe Ratio:    {results['sharpe_ratio']:.2f}")
        print(f"Max Drawdown:    {results['max_drawdown_pct']:.1%} (${results['max_drawdown_dollars']:,.0f})")
        
        # Exit Analysis
        print(f"\n--- Exit Reasons ---")
        for reason, count in results['exit_reasons'].items():
            print(f"{reason:15} {count:3} trades")
        
        # Comparison to Article
        print("\n" + "="*70)
        print("COMPARISON TO ARTICLE RESULTS")
        print("="*70)
        
        if results['strategy'] == '60min':
            print(f"{'Metric':<20} {'Article':>15} {'Backtest':>15} {'Difference':>15}")
            print("-"*65)
            
            article_win_rate = 0.888
            article_avg_pnl = 51
            article_pf = 1.59
            
            print(f"{'Win Rate':<20} {article_win_rate:>14.1%} {results['win_rate']:>14.1%} "
                  f"{(results['win_rate'] - article_win_rate):>14.1%}")
            print(f"{'Avg P&L':<20} ${article_avg_pnl:>13.0f} ${results['avg_pnl']:>13.0f} "
                  f"${(results['avg_pnl'] - article_avg_pnl):>13.0f}")
            print(f"{'Profit Factor':<20} {article_pf:>14.2f} {results['profit_factor']:>14.2f} "
                  f"{(results['profit_factor'] - article_pf):>14.2f}")


def main():
    """Run backtest with sample data"""
    
    print("\nLoading data...")
    
    # Try to load real SPY data
    data_path = Path('/Users/nish_macbook/0dte/data/SPY.parquet')
    if data_path.exists():
        data = pd.read_parquet(data_path)
        if 'date' in data.columns:
            data.set_index('date', inplace=True)
        print(f"Loaded {len(data)} bars of SPY data")
    else:
        print("SPY data not found, generating sample data")
        # Generate sample data
        dates = pd.date_range(start='2024-01-01 09:30', end='2024-12-31 16:00', freq='1min')
        dates = dates[(dates.time >= time(9, 30)) & (dates.time <= time(16, 0))]
        
        np.random.seed(42)
        prices = 450 + np.cumsum(np.random.randn(len(dates)) * 0.1)
        
        data = pd.DataFrame({
            'open': prices,
            'high': prices + abs(np.random.randn(len(dates)) * 0.3),
            'low': prices - abs(np.random.randn(len(dates)) * 0.3),
            'close': prices + np.random.randn(len(dates)) * 0.2,
            'volume': np.random.randint(500000, 2000000, len(dates))
        }, index=dates)
    
    # Initialize backtester
    backtester = ORBBacktester(initial_capital=100000)
    
    # Run 60-minute backtest
    print("\nRunning 60-minute ORB backtest...")
    results_60 = backtester.run_backtest(
        data,
        strategy_type='60min',
        start_date='2024-01-01',
        end_date='2024-12-31'
    )
    
    # Print report
    backtester.print_report(results_60)
    
    # Save results
    if 'trades' in results_60:
        results_60['trades'].to_csv('/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/orb_60min_trades.csv', index=False)
        print(f"\nTrades saved to: orb_strategy/data/backtest_results/orb_60min_trades.csv")


if __name__ == "__main__":
    main()