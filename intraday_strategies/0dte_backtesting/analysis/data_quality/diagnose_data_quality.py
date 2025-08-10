#!/usr/bin/env python3
"""Diagnose data quality issues in 0DTE options data"""

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
import pandas as pd
import numpy as np

db = ZeroDTESPYOptionsDatabase()

# Analyze multiple days
dates = ["20250728", "20250729", "20250730", "20250731", "20250801"]

print("DATA QUALITY ANALYSIS FOR 0DTE OPTIONS")
print("="*60)

for date in dates:
    print(f"\nAnalyzing {date}...")
    df = db.load_zero_dte_data(date)
    
    if df.empty:
        print(f"  No data for {date}")
        continue
    
    # Get a sample timestamp (10:00 AM)
    ts = f"{date[:4]}-{date[4:6]}-{date[6:]}T10:00:00"
    time_df = df[df['timestamp'] == ts]
    
    if time_df.empty:
        print(f"  No data at 10:00 AM")
        continue
    
    # Check SPY price
    spy_price = time_df.iloc[0]['underlying_price_dollar']
    print(f"  SPY Price: ${spy_price:.2f}")
    
    # Analyze delta distribution
    calls = time_df[time_df['right'] == 'CALL']
    puts = time_df[time_df['right'] == 'PUT']
    
    print(f"\n  CALL OPTIONS:")
    print(f"    Total: {len(calls)}")
    print(f"    Delta = 1.0000: {len(calls[calls['delta'] == 1.0])} ({len(calls[calls['delta'] == 1.0])/len(calls)*100:.1f}%)")
    print(f"    Delta between 0.2-0.4: {len(calls[(calls['delta'] >= 0.2) & (calls['delta'] <= 0.4)])}")
    
    # Show some calls with reasonable deltas
    reasonable_calls = calls[(calls['delta'] > 0) & (calls['delta'] < 1.0)].sort_values('delta')
    if not reasonable_calls.empty:
        print(f"    Calls with non-1.0 delta:")
        print(reasonable_calls[['strike', 'bid', 'ask', 'delta', 'implied_vol']].head(10).to_string(index=False))
    
    print(f"\n  PUT OPTIONS:")
    print(f"    Total: {len(puts)}")
    print(f"    Delta between -0.4 to -0.2: {len(puts[(puts['delta'] >= -0.4) & (puts['delta'] <= -0.2)])}")
    
    # Check bid-ask spreads
    time_df['ba_spread_pct'] = (time_df['ask'] - time_df['bid']) / ((time_df['ask'] + time_df['bid']) / 2) * 100
    
    print(f"\n  BID-ASK SPREADS:")
    print(f"    Average: {time_df['ba_spread_pct'].mean():.1f}%")
    print(f"    Median: {time_df['ba_spread_pct'].median():.1f}%")
    print(f"    Max: {time_df['ba_spread_pct'].max():.1f}%")
    print(f"    Spreads > 10%: {len(time_df[time_df['ba_spread_pct'] > 10])} options")
    
    # Check for zero or missing values
    print(f"\n  DATA COMPLETENESS:")
    print(f"    Zero bids: {len(time_df[time_df['bid'] == 0])}")
    print(f"    Zero asks: {len(time_df[time_df['ask'] == 0])}")
    print(f"    Missing IV: {len(time_df[time_df['implied_vol'] == 0])}")
    
    # Check exit time data quality
    exit_ts = f"{date[:4]}-{date[4:6]}-{date[6:]}T15:50:00"
    exit_df = df[df['timestamp'] == exit_ts]
    
    if not exit_df.empty:
        exit_df['ba_spread_pct'] = (exit_df['ask'] - exit_df['bid']) / ((exit_df['ask'] + exit_df['bid']) / 2) * 100
        print(f"\n  EXIT TIME (15:50) QUALITY:")
        print(f"    Average spread: {exit_df['ba_spread_pct'].mean():.1f}%")
        print(f"    Spreads > 50%: {len(exit_df[exit_df['ba_spread_pct'] > 50])} options")
        
        # Show worst spreads
        worst_spreads = exit_df.nlargest(5, 'ba_spread_pct')[['strike', 'right', 'bid', 'ask', 'ba_spread_pct']]
        print(f"    Worst spreads:")
        print(worst_spreads.to_string(index=False))

print("\n" + "="*60)
print("SUMMARY OF ISSUES:")
print("1. Many call options show delta = 1.0000 (deep ITM)")
print("2. Limited options with delta around 0.30 target")
print("3. Wide bid-ask spreads, especially at close (15:50)")
print("4. Some options have zero or missing implied volatility")
print("="*60)