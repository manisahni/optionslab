"""
Verify the complete download with Greeks
"""

import pandas as pd
import os

# Check a sample file
sample_file = "/Users/nish_macbook/0dte/market_data/spy_options_complete/20250505/SPY_0dte_complete_20250505.parquet"

if os.path.exists(sample_file):
    df = pd.read_parquet(sample_file)
    
    print("Complete Data Analysis (Quotes + Greeks)")
    print("="*60)
    print(f"Total records: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"\nColumn names:")
    for col in sorted(df.columns):
        print(f"  - {col}")
    
    print(f"\nUnique contracts: {df.groupby(['strike', 'right']).size().shape[0]}")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    print("\nGreeks Statistics:")
    if 'delta' in df.columns:
        print(f"Delta range: {df['delta'].min():.3f} to {df['delta'].max():.3f}")
        print(f"Average delta (calls): {df[df['right']=='CALL']['delta'].mean():.3f}")
        print(f"Average delta (puts): {df[df['right']=='PUT']['delta'].mean():.3f}")
    
    if 'implied_vol' in df.columns:
        print(f"\nImplied Vol range: {df['implied_vol'].min():.3f} to {df['implied_vol'].max():.3f}")
        print(f"Average IV: {df['implied_vol'].mean():.3f}")
    
    if 'theta' in df.columns:
        print(f"\nTheta range: {df['theta'].min():.3f} to {df['theta'].max():.3f}")
    
    if 'vega' in df.columns:
        print(f"Vega range: {df['vega'].min():.3f} to {df['vega'].max():.3f}")
    
    print("\nQuote Statistics:")
    print(f"Average bid/ask spread: ${df['spread'].mean():.3f}")
    print(f"Average mid price: ${df['mid_price'].mean():.2f}")
    
    # Show a sample record
    print("\nSample record:")
    sample = df.iloc[100]
    print(f"Strike: {sample['strike']}")
    print(f"Type: {sample['right']}")
    print(f"Bid: ${sample['bid']:.2f}")
    print(f"Ask: ${sample['ask']:.2f}")
    print(f"Delta: {sample['delta']:.3f}")
    print(f"IV: {sample['implied_vol']:.3f}")
    print(f"Underlying: ${sample['underlying_price']:.2f}")
    
    # Calculate total data size
    total_size = 0
    data_dir = "/Users/nish_macbook/0dte/market_data/spy_options_complete"
    for folder in os.listdir(data_dir):
        if folder.startswith('2025'):
            file_path = os.path.join(data_dir, folder, f"SPY_0dte_complete_{folder}.parquet")
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
    
    print(f"\nTotal download size: {total_size/(1024*1024):.1f} MB")
    print(f"Days downloaded: {len([f for f in os.listdir(data_dir) if f.startswith('2025')])}")
    
else:
    print("Sample file not found!")