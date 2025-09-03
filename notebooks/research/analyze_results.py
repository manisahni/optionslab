#!/usr/bin/env python3

import pandas as pd
import numpy as np

# Load the data
data_path = '/Users/nish_macbook/trading/daily-optionslab/data/spy_options/'
df_2023 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2023_COMPLETE.parquet')
df_2024 = pd.read_parquet(f'{data_path}SPY_OPTIONS_2024_COMPLETE.parquet')

df_all = pd.concat([df_2023, df_2024], ignore_index=True)
df_all['date'] = pd.to_datetime(df_all['date'])
df_all['strike'] = df_all['strike'] / 1000
df_all['mid_price'] = (df_all['bid'] + df_all['ask']) / 2

# Get SPY prices
spy_prices = df_all.groupby('date')['underlying_price'].first().reset_index()
spy_prices.columns = ['date', 'spy_price']
spy_prices = spy_prices.sort_values('date').reset_index(drop=True)

print("="*50)
print("MARKET ANALYSIS 2023-2024")
print("="*50)

print(f"SPY Start (2023-01-03): ${spy_prices.iloc[0]['spy_price']:.2f}")
print(f"SPY End (2024-12-31): ${spy_prices.iloc[-1]['spy_price']:.2f}")
spy_return = (spy_prices.iloc[-1]['spy_price'] - spy_prices.iloc[0]['spy_price']) / spy_prices.iloc[0]['spy_price'] * 100
print(f"SPY Total Return: {spy_return:.1f}%")

# Analyze LEAP performance potential
print("\n" + "="*50)
print("LEAP PERFORMANCE ANALYSIS")
print("="*50)

# Check what happens to a simple LEAP buy-and-hold
start_date = spy_prices.iloc[0]['date']
end_date = spy_prices.iloc[-1]['date']

# Calculate DTE first
df_all['expiration'] = pd.to_datetime(df_all['expiration'])
df_all['dte'] = (df_all['expiration'] - df_all['date']).dt.days

# Find LEAPs available at start
start_data = df_all[(df_all['date'] == start_date) & (df_all['right'] == 'C') & 
                   (df_all['dte'] >= 300) & (df_all['dte'] <= 500) &
                   (df_all['delta'] >= 0.7) & (df_all['delta'] <= 0.8)]

print(f"LEAPs available on {start_date.date()}: {len(start_data)}")

if len(start_data) > 0:
    # Pick the best LEAP (closest to 0.75 delta)
    start_data['delta_diff'] = abs(start_data['delta'] - 0.75)
    best_leap = start_data.loc[start_data['delta_diff'].idxmin()]
    
    print(f"\nSelected LEAP:")
    print(f"  Strike: ${best_leap['strike']:.0f}")
    print(f"  Entry Price: ${best_leap['mid_price']:.2f}")
    print(f"  Delta: {best_leap['delta']:.2f}")
    print(f"  DTE: {best_leap['dte']}")
    print(f"  Expiration: {best_leap['expiration'].date()}")
    
    # Find the same option at the end (or close to end)
    end_data = df_all[(df_all['date'] <= end_date) & 
                     (df_all['strike'] == best_leap['strike']) &
                     (df_all['expiration'] == best_leap['expiration']) &
                     (df_all['right'] == 'C')]
    
    if len(end_data) > 0:
        # Get the latest available price for this option
        latest_data = end_data.loc[end_data['date'].idxmax()]
        exit_price = latest_data['mid_price']
        
        print(f"\nLEAP Performance:")
        print(f"  Entry: ${best_leap['mid_price']:.2f}")
        print(f"  Exit ({latest_data['date'].date()}): ${exit_price:.2f}")
        leap_return = (exit_price - best_leap['mid_price']) / best_leap['mid_price'] * 100
        print(f"  LEAP Return: {leap_return:.1f}%")
        
        # Compare to SPY
        print(f"\nComparison:")
        print(f"  SPY Return: {spy_return:.1f}%")
        print(f"  LEAP Return: {leap_return:.1f}%")
        print(f"  LEAP Leverage: {leap_return/spy_return:.1f}x" if spy_return != 0 else "  LEAP Leverage: N/A")
    else:
        print("  Could not find exit data for this LEAP")

# Check why our strategy underperformed
print("\n" + "="*50)
print("STRATEGY ISSUES ANALYSIS")
print("="*50)

print("Potential reasons for poor performance:")
print("1. Market Period: 2023-2024 was a strong bull market")
print("2. LEAP Selection: May be selecting wrong strikes/expiration")
print("3. Rolling Logic: May be rolling LEAPs at bad times")
print("4. Protection Cost: Protection may be too expensive")
print("5. Data Issues: Strike price conversion or other data problems")

print(f"\nNote: If SPY gained {spy_return:.1f}% but our LEAP strategy lost money,")
print("there's likely a fundamental issue with:")
print("- LEAP selection criteria")
print("- Position management logic") 
print("- Or data processing")