#!/usr/bin/env python3
"""Test script to run a backtest and display results"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'optionslab'))
from auditable_backtest import run_auditable_backtest
from auditable_gradio_app import format_trades_dataframe
import pandas as pd
from datetime import datetime

# Run a backtest
print("🚀 Running backtest with enhanced trade logging...")
print("=" * 60)

data_dir = "spy_options_downloader/spy_options_parquet"
strategy_file = "config/strategies/simple_long_call.yaml"
start_date = "2022-01-01"
end_date = "2022-03-31"  # Shorter period for demo

# Run the backtest
results = run_auditable_backtest(data_dir, strategy_file, start_date, end_date)

if results:
    print("\n✅ Backtest completed successfully!")
    print(f"Final Value: ${results['final_value']:,.2f}")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Total Trades: {len(results['trades'])}")
    
    # Format trades for display
    trades_df = format_trades_dataframe(results['trades'])
    
    if not trades_df.empty:
        print("\n📊 Trade Details:")
        print("=" * 60)
        
        # Display first few trades with all columns
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 20)
        
        print(trades_df.head(10))
        
        # Save to CSV for inspection
        csv_path = f"trade_log_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        full_trades_df = pd.DataFrame(results['trades'])
        full_trades_df.to_csv(csv_path, index=False)
        print(f"\n💾 Full trade log saved to: {csv_path}")
        
        # Show summary statistics
        completed_trades = [t for t in results['trades'] if 'exit_date' in t]
        if completed_trades:
            winning_trades = [t for t in completed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in completed_trades if t.get('pnl', 0) <= 0]
            
            print("\n📈 Summary Statistics:")
            print("=" * 60)
            print(f"Total Completed Trades: {len(completed_trades)}")
            print(f"Winning Trades: {len(winning_trades)}")
            print(f"Losing Trades: {len(losing_trades)}")
            print(f"Win Rate: {(len(winning_trades) / len(completed_trades) * 100):.1f}%")
            
            if winning_trades:
                avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades)
                print(f"Average Win: ${avg_win:.2f}")
            
            if losing_trades:
                avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades)
                print(f"Average Loss: ${avg_loss:.2f}")
            
            # Show sample of comprehensive data
            print("\n🔍 Sample Trade with All Fields:")
            print("=" * 60)
            sample_trade = completed_trades[0]
            for key, value in sample_trade.items():
                print(f"{key}: {value}")
else:
    print("❌ Backtest failed!")