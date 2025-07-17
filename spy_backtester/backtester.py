#!/usr/bin/env python3
"""
SPY Options Backtester - CLI Interface
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from typing import Dict, Any

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from data_loader import SPYDataLoader
from portfolio_manager import PortfolioManager
from strategy_base import OrderType
from strategies.simple_strategies import (
    LongCallStrategy, LongPutStrategy, 
    StraddleStrategy, CoveredCallStrategy
)
from config import DEFAULT_PARAMS


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, strategy, start_date: str, end_date: str, 
                 initial_capital: float = 100000):
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.data_loader = SPYDataLoader()
        self.portfolio = PortfolioManager(initial_capital)
        self.results = []
        
    def run_backtest(self) -> Dict[str, Any]:
        """Execute the backtest"""
        print(f"Running backtest: {self.strategy.name}")
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Initial capital: ${self.portfolio.initial_capital:,.2f}")
        print("-" * 50)
        
        # Get available dates in range
        available_dates = self.data_loader.get_available_dates()
        backtest_dates = [d for d in available_dates 
                         if self.start_date <= d <= self.end_date]
        
        if not backtest_dates:
            raise ValueError(f"No data available for period {self.start_date} to {self.end_date}")
        
        print(f"Found {len(backtest_dates)} trading days")
        
        # Process each date
        for i, date in enumerate(backtest_dates):
            try:
                self._process_date(date)
                
                # Print progress
                if (i + 1) % 50 == 0 or i == len(backtest_dates) - 1:
                    progress = (i + 1) / len(backtest_dates) * 100
                    portfolio_value = self.portfolio.snapshots[-1].total_value if self.portfolio.snapshots else self.portfolio.initial_capital
                    print(f"Progress: {progress:.1f}% - {date} - Portfolio: ${portfolio_value:,.2f}")
                    
            except Exception as e:
                print(f"Error processing {date}: {e}")
                continue
        
        # Generate final results
        results = self._generate_results()
        return results
    
    def _process_date(self, date: str):
        """Process a single trading date"""
        # Load data for this date
        current_data = self.data_loader.load_date(date)
        current_date = datetime.strptime(date, '%Y%m%d')
        
        self.strategy.current_date = current_date
        
        # Check exit conditions for existing positions
        positions_to_close = []
        for position in self.portfolio.get_open_positions():
            if self.strategy.should_exit_position(position, current_data):
                positions_to_close.append(position)
        
        # Close positions
        for position in positions_to_close:
            self._close_position(position, current_data, current_date)
        
        # Generate new entry signals
        market_data = {
            'underlying_price': current_data['underlying_price'].iloc[0],
            'date': current_date
        }
        
        signals = self.strategy.generate_signals(current_data, market_data)
        
        # Execute signals
        for signal in signals:
            self._execute_signal(signal, current_data, current_date)
        
        # Update strategy with current trades
        self.strategy.trades = self.portfolio.trades.copy()
        self.strategy.positions = self.portfolio.positions.copy()
        self.strategy.portfolio_value = self.portfolio.calculate_portfolio_value(current_data)
        
        # Take portfolio snapshot
        self.portfolio.take_snapshot(current_date, current_data)
    
    def _execute_signal(self, signal, current_data: pd.DataFrame, current_date: datetime):
        """Execute a trading signal"""
        # Find the option based on criteria
        option_data = self._find_option(current_data, signal.option_criteria)
        
        if option_data is None:
            print(f"Warning: Could not find option for signal: {signal.reason}")
            return
        
        # Determine order type
        if signal.action == 'buy':
            order_type = OrderType.BUY_TO_OPEN
        else:
            order_type = OrderType.SELL_TO_OPEN
        
        # Execute trade
        trade = self.portfolio.execute_trade(
            option_data, signal.quantity, order_type, current_date
        )
        
        if trade:
            print(f"{current_date.strftime('%Y-%m-%d')}: {signal.reason} - "
                  f"{signal.action.upper()} {signal.quantity} {trade.option_type} "
                  f"${trade.strike:.0f} @ ${trade.price:.2f}")
        else:
            print(f"Warning: Could not execute trade for signal: {signal.reason}")
    
    def _close_position(self, position, current_data: pd.DataFrame, current_date: datetime):
        """Close an open position"""
        last_trade = position.trades[-1]
        
        # Find current option data
        option_data = self._find_option(current_data, {
            'strike': last_trade.strike,
            'expiration': last_trade.expiration,
            'option_type': last_trade.option_type
        })
        
        if option_data is None:
            # Option expired or not found - assume worthless
            print(f"{current_date.strftime('%Y-%m-%d')}: Position expired - "
                  f"{last_trade.option_type} ${last_trade.strike:.0f}")
            return
        
        # Determine closing order type
        if position.net_quantity > 0:
            order_type = OrderType.SELL_TO_CLOSE
        else:
            order_type = OrderType.BUY_TO_CLOSE
        
        # Execute closing trade
        trade = self.portfolio.execute_trade(
            option_data, abs(position.net_quantity), order_type, current_date
        )
        
        if trade:
            # Calculate P&L for this position
            total_cost = sum(t.total_cost for t in position.trades)
            pnl = total_cost + trade.total_cost
            print(f"{current_date.strftime('%Y-%m-%d')}: CLOSE {trade.option_type} "
                  f"${trade.strike:.0f} @ ${trade.price:.2f} - P&L: ${pnl:.2f}")
    
    def _find_option(self, current_data: pd.DataFrame, criteria: Dict[str, Any]) -> pd.Series:
        """Find option matching criteria"""
        matches = current_data[
            (current_data['strike'] == criteria['strike']) &
            (current_data['right'] == criteria['option_type']) &
            (current_data['expiration'] == pd.to_datetime(criteria['expiration']))
        ]
        
        return matches.iloc[0] if not matches.empty else None
    
    def _generate_results(self) -> Dict[str, Any]:
        """Generate final backtest results"""
        performance = self.portfolio.get_performance_summary()
        
        results = {
            'strategy': self.strategy.name,
            'period': f"{self.start_date} to {self.end_date}",
            'performance': performance,
            'trades_df': self.portfolio.get_trades_df(),
            'snapshots_df': self.portfolio.get_snapshots_df()
        }
        
        return results


def create_strategy(strategy_name: str, params: Dict[str, Any]):
    """Factory function to create strategy instances"""
    strategies = {
        'long_call': LongCallStrategy,
        'long_put': LongPutStrategy,
        'straddle': StraddleStrategy,
        'covered_call': CoveredCallStrategy
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. "
                        f"Available: {list(strategies.keys())}")
    
    return strategies[strategy_name](params)


def print_results(results: Dict[str, Any]):
    """Print backtest results"""
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    
    perf = results['performance']
    
    print(f"Strategy: {results['strategy']}")
    print(f"Period: {results['period']}")
    print(f"\nPerformance Summary:")
    print(f"  Initial Capital:     ${perf['initial_capital']:>12,.2f}")
    print(f"  Final Value:         ${perf['final_value']:>12,.2f}")
    print(f"  Total Return:        {perf['total_return']:>12.2%}")
    print(f"  Total P&L:           ${perf['total_pnl']:>12,.2f}")
    print(f"  Max Drawdown:        {perf['max_drawdown']:>12.2%}")
    print(f"  Sharpe Ratio:        {perf['sharpe_ratio']:>12.2f}")
    print(f"  Number of Trades:    {perf['num_trades']:>12}")
    print(f"  Current Cash:        ${perf['current_cash']:>12,.2f}")
    
    # Print recent trades
    trades_df = results['trades_df']
    if not trades_df.empty:
        print(f"\nRecent Trades (last 10):")
        recent_trades = trades_df.tail(10)[['date', 'option_type', 'strike', 'order_type', 'quantity', 'price']]
        print(recent_trades.to_string(index=False))


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='SPY Options Backtester')
    
    # Required arguments
    parser.add_argument('--strategy', required=True, 
                       choices=['long_call', 'long_put', 'straddle', 'covered_call'],
                       help='Strategy to backtest')
    parser.add_argument('--start-date', required=True, 
                       help='Start date (YYYYMMDD)')
    parser.add_argument('--end-date', required=True,
                       help='End date (YYYYMMDD)')
    
    # Optional arguments
    parser.add_argument('--initial-capital', type=float, default=100000,
                       help='Initial capital (default: 100000)')
    parser.add_argument('--delta-threshold', type=float, default=0.30,
                       help='Delta threshold for entry (default: 0.30)')
    parser.add_argument('--min-dte', type=int, default=10,
                       help='Minimum days to expiration (default: 10)')
    parser.add_argument('--max-dte', type=int, default=60,
                       help='Maximum days to expiration (default: 60)')
    parser.add_argument('--stop-loss', type=float, default=0.50,
                       help='Stop loss percentage (default: 0.50)')
    parser.add_argument('--profit-target', type=float, default=1.00,
                       help='Profit target percentage (default: 1.00)')
    parser.add_argument('--position-size', type=float, default=0.05,
                       help='Maximum position size as fraction of capital (default: 0.05)')
    parser.add_argument('--output', type=str, 
                       help='Output file path for results')
    
    args = parser.parse_args()
    
    # Build strategy parameters
    params = DEFAULT_PARAMS.copy()
    params.update({
        'initial_capital': args.initial_capital,
        'delta_threshold': args.delta_threshold,
        'target_delta': args.delta_threshold,
        'min_dte': args.min_dte,
        'max_dte': args.max_dte,
        'stop_loss_pct': args.stop_loss,
        'profit_target_pct': args.profit_target,
        'max_position_size': args.position_size
    })
    
    try:
        # Create strategy
        strategy = create_strategy(args.strategy, params)
        
        # Run backtest
        engine = BacktestEngine(strategy, args.start_date, args.end_date, 
                              args.initial_capital)
        results = engine.run_backtest()
        
        # Print results
        print_results(results)
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save trades to CSV
            trades_df = results['trades_df']
            if not trades_df.empty:
                trades_file = output_path.with_suffix('.csv')
                trades_df.to_csv(trades_file, index=False)
                print(f"\nTrades saved to: {trades_file}")
            
            # Save portfolio snapshots
            snapshots_df = results['snapshots_df']
            if not snapshots_df.empty:
                snapshots_file = output_path.with_name(f"{output_path.stem}_portfolio.csv")
                snapshots_df.to_csv(snapshots_file, index=False)
                print(f"Portfolio history saved to: {snapshots_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()