#!/usr/bin/env python3
"""Investigate strangle data to understand the losses"""

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
import pandas as pd

db = ZeroDTESPYOptionsDatabase()

# Check a specific day
date = "20250728"
df = db.load_zero_dte_data(date)

# Look at 10:00 AM data
entry_ts = "2025-07-28T10:00:00"
entry_data = df[df['timestamp'] == entry_ts]

print(f"Data for {date} at 10:00 AM")
print(f"Total options: {len(entry_data)}")

# Check SPY price
spy_price = entry_data.iloc[0]['underlying_price_dollar']
print(f"\nSPY Price: ${spy_price}")

# Look at ATM options
atm_strikes = entry_data[
    (entry_data['strike'] >= spy_price - 5) & 
    (entry_data['strike'] <= spy_price + 5)
].sort_values('strike')

print("\nNear ATM Options:")
print(atm_strikes[['strike', 'right', 'bid', 'ask', 'delta', 'implied_vol']].to_string())

# Check for 0.30 delta options
calls_30d = entry_data[
    (entry_data['right'] == 'CALL') & 
    (entry_data['delta'] > 0.25) & 
    (entry_data['delta'] < 0.35)
].sort_values('delta')

puts_30d = entry_data[
    (entry_data['right'] == 'PUT') & 
    (entry_data['delta'] < -0.25) & 
    (entry_data['delta'] > -0.35)
].sort_values('delta', ascending=False)

print("\n~0.30 Delta Calls:")
print(calls_30d[['strike', 'bid', 'ask', 'delta']].head())

print("\n~0.30 Delta Puts:")
print(puts_30d[['strike', 'bid', 'ask', 'delta']].head())

# Check exit time
exit_ts = "2025-07-28T15:50:00"
exit_data = df[df['timestamp'] == exit_ts]

print(f"\nExit SPY Price: ${exit_data.iloc[0]['underlying_price_dollar']}")

# Look at our specific strikes at exit
call_strike = 642.0
put_strike = 638.0

exit_options = exit_data[
    (exit_data['strike'].isin([call_strike, put_strike]))
]

print("\nExit prices for our strikes:")
print(exit_options[['strike', 'right', 'bid', 'ask', 'delta']].to_string())