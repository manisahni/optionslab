#!/usr/bin/env python3
"""
Quick Start Script for ORB Strategy
Run this to test the ORB strategy with your data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path
import logging
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add strategy modules to path
sys.path.append(str(Path(__file__).parent))

from strategies.orb_60min import ORB60MinStrategy
from core.orb_calculator import ORBCalculator
from core.breakout_detector import BreakoutDetector
from core.position_builder import CreditSpreadBuilder


def load_config():
    """Load configuration from YAML file"""
    config_path = Path(__file__).parent / 'config' / 'orb_settings.yaml'
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        logger.warning("Config file not found, using defaults")
        return {}


def load_spy_data():
    """Load SPY data from the main data directory"""
    data_paths = [
        Path('/Users/nish_macbook/0dte/data/SPY.parquet'),
        Path('/Users/nish_macbook/0dte/data/historical/SPY.parquet'),
        Path('/Users/nish_macbook/0dte/SPY.parquet')
    ]
    
    for path in data_paths:
        if path.exists():
            logger.info(f"Loading data from {path}")
            df = pd.read_parquet(path)
            
            # Ensure datetime index
            if 'date' in df.columns:
                df.set_index('date', inplace=True)
            
            # Ensure OHLCV columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if all(col in df.columns for col in required_cols):
                return df
            else:
                logger.warning(f"Missing required columns in {path}")
    
    logger.warning("No SPY data found, generating sample data")
    return generate_sample_data()


def generate_sample_data():
    """Generate sample SPY data for testing"""
    dates = pd.date_range(start='2024-01-02 09:30', end='2024-01-31 16:00', freq='1min')
    
    # Filter to market hours only
    dates = dates[(dates.time >= pd.Timestamp('09:30').time()) & 
                  (dates.time <= pd.Timestamp('16:00').time())]
    
    # Generate realistic price movements
    np.random.seed(42)
    base_price = 450
    prices = []
    
    for date in dates:
        # Add some intraday patterns
        hour_factor = np.sin((date.hour - 9.5) / 6.5 * np.pi) * 2
        noise = np.random.randn() * 0.5
        price = base_price + hour_factor + noise
        prices.append(price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p + abs(np.random.randn() * 0.3) for p in prices],
        'low': [p - abs(np.random.randn() * 0.3) for p in prices],
        'close': [p + np.random.randn() * 0.2 for p in prices],
        'volume': np.random.randint(500000, 2000000, len(prices))
    }, index=dates)
    
    # Ensure high/low contain open/close
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def run_single_day_test(data, date, strategy):
    """Run strategy for a single day"""
    # Filter to specific date
    day_data = data[data.index.date == pd.to_datetime(date).date()]
    
    if day_data.empty:
        logger.warning(f"No data for {date}")
        return None
    
    logger.info(f"\nProcessing {date}")
    logger.info("="*50)
    
    results = []
    
    # Process each bar
    for idx, bar in day_data.iterrows():
        action = strategy.process_bar(bar, day_data)
        
        if action['action'] == 'enter':
            position = action['position']
            logger.info(f"✅ ENTRY at {idx.strftime('%H:%M')}")
            logger.info(f"   Type: {position['type']}")
            logger.info(f"   Strikes: ${position['short_strike']}/{position['long_strike']}")
            logger.info(f"   Contracts: {position['num_contracts']}")
            results.append(action)
            
        elif action['action'] == 'close':
            logger.info(f"🔴 EXIT at {idx.strftime('%H:%M')}")
            logger.info(f"   Reason: {action['reason']}")
            logger.info(f"   P&L: ${action.get('pnl', 0):.0f}")
            results.append(action)
    
    return results


def run_backtest(data, start_date, end_date, strategy):
    """Run backtest over date range"""
    logger.info(f"\nRunning backtest from {start_date} to {end_date}")
    logger.info("="*70)
    
    # Get unique trading days
    trading_days = pd.date_range(start=start_date, end=end_date, freq='B')
    
    all_trades = []
    
    for date in trading_days:
        day_data = data[data.index.date == date.date()]
        
        if day_data.empty:
            continue
        
        # Reset strategy for new day
        strategy.reset_daily_state()
        
        # Process the day
        for idx, bar in day_data.iterrows():
            action = strategy.process_bar(bar, day_data)
            
            if action['action'] in ['enter', 'close']:
                all_trades.append(action)
    
    return all_trades


def print_performance_report(strategy):
    """Print detailed performance report"""
    summary = strategy.get_performance_summary()
    
    print("\n" + "="*70)
    print("PERFORMANCE REPORT")
    print("="*70)
    
    if 'status' in summary:
        print(summary['status'])
        return
    
    print(f"Total Trades:     {summary['total_trades']}")
    print(f"Winning Trades:   {summary['winning_trades']}")
    print(f"Losing Trades:    {summary['losing_trades']}")
    print(f"Win Rate:         {summary['win_rate']:.1%}")
    print(f"")
    print(f"Total P&L:        ${summary['total_pnl']:,.0f}")
    print(f"Average P&L:      ${summary['avg_pnl']:.0f}")
    print(f"Average Win:      ${summary['avg_win']:.0f}")
    print(f"Average Loss:     ${summary['avg_loss']:.0f}")
    print(f"")
    print(f"Profit Factor:    {summary['profit_factor']:.2f}")
    print(f"Max Drawdown:     ${summary['max_drawdown']:,.0f}")
    
    # Compare to expected results
    print("\n" + "-"*70)
    print("COMPARISON TO ARTICLE RESULTS (60-min ORB):")
    print(f"Expected Win Rate: 88.8% | Actual: {summary['win_rate']:.1%}")
    print(f"Expected Avg P&L:  $51   | Actual: ${summary['avg_pnl']:.0f}")
    print(f"Expected PF:       1.59  | Actual: {summary['profit_factor']:.2f}")


def main():
    """Main entry point"""
    
    print("\n" + "="*70)
    print("ORB STRATEGY QUICK START")
    print("="*70)
    
    # Load configuration
    config = load_config()
    
    # Initialize strategy
    strategy = ORB60MinStrategy(
        spread_width=config.get('position', {}).get('spread_width', 15),
        position_size_pct=config.get('position', {}).get('position_size_pct', 0.02)
    )
    
    # Load data
    data = load_spy_data()
    print(f"\nData loaded: {len(data)} bars")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    
    # Menu
    print("\nSelect Option:")
    print("1. Test single day (most recent)")
    print("2. Run backtest (last 30 days)")
    print("3. Analyze opening ranges")
    print("4. Test components individually")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '1':
        # Test most recent day
        last_date = data.index[-1].date()
        run_single_day_test(data, last_date, strategy)
        
    elif choice == '2':
        # Run backtest
        end_date = data.index[-1].date()
        start_date = end_date - timedelta(days=30)
        trades = run_backtest(data, start_date, end_date, strategy)
        print_performance_report(strategy)
        
    elif choice == '3':
        # Analyze opening ranges
        calculator = ORBCalculator(timeframe_minutes=60)
        
        # Get last 10 days of ranges
        dates = data.index.normalize().unique()[-10:]
        
        print("\nOpening Range Analysis (Last 10 Days)")
        print("-"*50)
        
        for date in dates:
            day_data = data[data.index.date == date.date()]
            if not day_data.empty:
                or_info = calculator.calculate_range(day_data)
                if or_info:
                    print(f"{date.date()}: Range=${or_info['range']:.2f} "
                          f"({or_info['range_pct']:.3%}) - "
                          f"Valid: {or_info['valid']}")
    
    elif choice == '4':
        # Test components
        print("\nTesting Components:")
        print("-"*50)
        
        # Test ORB Calculator
        calculator = ORBCalculator(60)
        day_data = data[data.index.date == data.index[-1].date()]
        or_levels = calculator.calculate_range(day_data)
        print(f"✓ ORB Calculator: Range = ${or_levels['range']:.2f}")
        
        # Test Breakout Detector
        detector = BreakoutDetector()
        print(f"✓ Breakout Detector: Initialized")
        
        # Test Position Builder
        builder = CreditSpreadBuilder()
        position = builder.build_put_spread(450, 448)
        print(f"✓ Position Builder: Spread = ${position['short_strike']}/{position['long_strike']}")
    
    else:
        print("Invalid choice")
    
    print("\n" + "="*70)
    print("Quick start complete!")
    print("\nNext steps:")
    print("1. Connect to Alpaca for real option prices")
    print("2. Run full backtest with actual data")
    print("3. Paper trade to validate performance")
    print("4. Go live with small capital")


if __name__ == "__main__":
    main()