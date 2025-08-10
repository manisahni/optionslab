"""
Analyze underlying price data in the options download
"""

import pandas as pd
import os

# Load a sample file
sample_file = "/Users/nish_macbook/0dte/market_data/spy_options_complete/20250505/SPY_0dte_complete_20250505.parquet"

if os.path.exists(sample_file):
    df = pd.read_parquet(sample_file)
    
    print("Underlying Price Data Analysis")
    print("="*60)
    
    # Check underlying data columns
    underlying_cols = [col for col in df.columns if 'underlying' in col.lower() or 'spot' in col.lower()]
    print(f"Underlying-related columns: {underlying_cols}")
    
    # Analyze underlying_price
    if 'underlying_price' in df.columns:
        print(f"\nUnderlying Price Statistics:")
        print(f"  Min: ${df['underlying_price'].min():,.2f}")
        print(f"  Max: ${df['underlying_price'].max():,.2f}")
        print(f"  Mean: ${df['underlying_price'].mean():,.2f}")
        print(f"  Unique values: {df['underlying_price'].nunique()}")
        
        # Check if underlying price changes over time
        unique_times = df['timestamp'].nunique()
        unique_underlying = df.groupby('timestamp')['underlying_price'].first().nunique()
        print(f"\n  Time periods: {unique_times}")
        print(f"  Unique underlying prices by time: {unique_underlying}")
        
        # Show underlying price movement
        underlying_by_time = df.groupby('timestamp')['underlying_price'].first()
        print(f"\nUnderlying price movement:")
        print(f"  First 5 values:")
        for time, price in underlying_by_time.head().items():
            print(f"    {time}: ${price/100:.2f}")  # Dividing by 100 as it seems to be in cents
        
    # Check spot_price
    if 'spot_price' in df.columns:
        print(f"\nSpot Price (from stock data):")
        print(f"  Value: ${df['spot_price'].iloc[0]:.2f}")
        print(f"  Is constant: {df['spot_price'].nunique() == 1}")
    
    # Check underlying_timestamp
    if 'underlying_timestamp' in df.columns:
        print(f"\nUnderlying Timestamp:")
        print(f"  Sample: {df['underlying_timestamp'].iloc[0]}")
        print(f"  Unique timestamps: {df['underlying_timestamp'].nunique()}")
    
    # Compare with separate stock data
    stock_date = "2025-05-05"
    stock_file = f"/Users/nish_macbook/0dte/market_data/spy_stock_data/SPY/{stock_date}/SPY_1min.parquet"
    
    if os.path.exists(stock_file):
        stock_df = pd.read_parquet(stock_file)
        print(f"\nComparison with separate stock data:")
        print(f"  Stock data records: {len(stock_df)}")
        print(f"  Stock open: ${stock_df.iloc[0]['open']:.2f}")
        print(f"  Stock close: ${stock_df.iloc[-1]['close']:.2f}")
        print(f"  Stock high: ${stock_df['high'].max():.2f}")
        print(f"  Stock low: ${stock_df['low'].min():.2f}")
    
    # Show sample of data with underlying
    print("\nSample data with underlying prices:")
    sample_cols = ['timestamp', 'strike', 'right', 'bid', 'ask', 'delta', 'underlying_price']
    available_cols = [col for col in sample_cols if col in df.columns]
    print(df[available_cols].head(10))
    
else:
    print("Sample file not found!")