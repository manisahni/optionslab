"""
Verify downloaded options data
"""

import pandas as pd
import os

# Check a sample file
sample_file = "/Users/nish_macbook/0dte/market_data/spy_options_v3/20250505/SPY_0dte_20250505.parquet"

if os.path.exists(sample_file):
    df = pd.read_parquet(sample_file)
    
    print("Sample Data Analysis")
    print("="*50)
    print(f"Total records: {len(df)}")
    print(f"Columns: {', '.join(df.columns)}")
    print(f"\nUnique contracts: {df.groupby(['strike', 'right']).size().shape[0]}")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    print("\nSample records:")
    print(df.head())
    
    print("\nData statistics:")
    print(f"Average bid/ask spread: ${df['spread'].mean():.3f}")
    print(f"Average mid price: ${df['mid_price'].mean():.2f}")
    print(f"Contracts with bid > 0: {(df['bid'] > 0).sum()}")
    print(f"Contracts with ask > 0: {(df['ask'] > 0).sum()}")
    
    print("\nStrike distribution:")
    strikes = df.groupby('strike').size().sort_index()
    print(strikes)
else:
    print("Sample file not found!")