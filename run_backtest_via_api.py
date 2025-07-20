#!/usr/bin/env python3
"""Run a backtest through the Gradio interface to test the system"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'optionslab'))

from auditable_backtest import run_auditable_backtest
from auditable_gradio_app import save_trade_log, format_trades_dataframe
import pandas as pd

print("Running backtest to generate logs...")

# Run backtest
results = run_auditable_backtest(
    "spy_options_downloader/spy_options_parquet",
    "config/strategies/simple_long_call.yaml",
    "2022-01-01",
    "2022-03-31"
)

if results:
    print(f"✅ Backtest completed!")
    print(f"Final Value: ${results['final_value']:,.2f}")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Total Trades: {len(results['trades'])}")
    
    # Format and save
    trades_df = pd.DataFrame(results['trades'])
    results['initial_capital'] = 10000
    
    csv_path, json_path = save_trade_log(
        trades_df, 
        results, 
        "simple-long-call",
        "2022-01-01",
        "2022-03-31"
    )
    
    print(f"\n📁 Logs saved:")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    
    # Check what's in the CSV
    saved_df = pd.read_csv(csv_path)
    print(f"\nCSV Details:")
    print(f"Shape: {saved_df.shape}")
    print(f"Columns: {len(saved_df.columns)}")
    print(f"Sample columns: {list(saved_df.columns)[:10]}")
else:
    print("❌ Backtest failed!")