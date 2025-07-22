#!/usr/bin/env python3
"""Debug the array comparison error"""

import sys
import traceback
import pandas as pd
import numpy as np

# Add current directory to path
sys.path.insert(0, '.')

# Run the backtest with full traceback
try:
    from optionslab.app import run_auditable_backtest_gradio
    
    # Test with sample inputs
    data_file = "../spy_options_downloader/spy_options_parquet/SPY_OPTIONS_2022_COMPLETE.parquet"
    strategy_file = "../simple_test_strategy.yaml"
    start_date = "2022-01-01"
    end_date = "2022-01-31"
    initial_capital = 10000
    
    print("Running backtest with debug...")
    result = run_auditable_backtest_gradio(
        data_file, strategy_file, start_date, end_date, initial_capital
    )
    
    print("Result:", result[0][:200])  # First 200 chars of summary
    
except Exception as e:
    print(f"\nError occurred: {type(e).__name__}: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    
    # Additional debugging for array errors
    if "ambiguous" in str(e):
        print("\n⚠️  This is an array comparison error.")
        print("Common causes:")
        print("1. Using 'if array:' instead of 'if len(array) > 0:'")
        print("2. Using '==' on arrays instead of '.equals()' or '.all()'")
        print("3. Using pd.isna() on arrays without .any() or .all()")