#!/usr/bin/env python3
"""Analyze why strangle selection is problematic"""

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
import pandas as pd

db = ZeroDTESPYOptionsDatabase()

date = "20250728"
df = db.load_zero_dte_data(date)

# Look at 10:00 AM
entry_ts = "2025-07-28T10:00:00"
entry_data = df[df['timestamp'] == entry_ts]

spy_price = entry_data.iloc[0]['underlying_price_dollar']
print(f"Date: {date}")
print(f"SPY Price at 10:00 AM: ${spy_price:.2f}")
print(f"\nLooking for ~0.30 delta options...")

# Find all options with reasonable deltas
calls = entry_data[entry_data['right'] == 'CALL'].copy()
puts = entry_data[entry_data['right'] == 'PUT'].copy()

# Filter out delta = 1.0 calls
calls_filtered = calls[calls['delta'] < 0.99]
print(f"\nCALLS (excluding delta=1.0):")
print(calls_filtered[['strike', 'bid', 'ask', 'delta', 'implied_vol']].sort_values('delta'))

# Look for puts around -0.30 delta
puts_30d = puts[(puts['delta'] > -0.35) & (puts['delta'] < -0.25)]
print(f"\nPUTS with delta around -0.30:")
print(puts_30d[['strike', 'bid', 'ask', 'delta', 'implied_vol']].sort_values('delta'))

# The problem: Finding the "closest" to 0.30 delta when no calls have delta near 0.30
print("\nPROBLEM IDENTIFIED:")
print("- No call options have delta near 0.30 (they jump from 0.166 to 1.0)")
print("- The backtester picks 642 call with 0.166 delta as 'closest' to 0.30")
print("- This creates an asymmetric strangle that's bearish biased")

# Show what happens at exit
exit_ts = "2025-07-28T15:50:00"
exit_data = df[df['timestamp'] == exit_ts]
exit_spy = exit_data.iloc[0]['underlying_price_dollar']

print(f"\nAt exit (15:50):")
print(f"SPY moved from ${spy_price:.2f} to ${exit_spy:.2f} ({exit_spy - spy_price:.2f})")

# Look at our strikes at exit
call_strike = 642.0
put_strike = 638.0
exit_options = exit_data[exit_data['strike'].isin([call_strike, put_strike])]

print(f"\nExit prices for selected strikes:")
for _, row in exit_options.iterrows():
    print(f"{row['right']} {row['strike']}: bid=${row['bid']:.2f}, ask=${row['ask']:.2f}")
    if row['ask'] > row['bid']:
        spread_pct = (row['ask'] - row['bid']) / row['bid'] * 100 if row['bid'] > 0 else float('inf')
        print(f"  Spread: {spread_pct:.1f}%")

print("\nKEY ISSUES:")
print("1. Limited OTM call options with reasonable deltas")
print("2. Most calls show delta = 1.0 (data issue)")
print("3. Huge bid-ask spreads at close (e.g., 4.37/6.94)")
print("4. Strategy forced to use suboptimal strikes")