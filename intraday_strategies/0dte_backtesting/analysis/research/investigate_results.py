#!/usr/bin/env python3
"""
Investigate the counterintuitive results
"""

import pandas as pd
from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
from zero_dte_analysis_tools import ZeroDTEAnalyzer

# Initialize
db = ZeroDTESPYOptionsDatabase()
analyzer = ZeroDTEAnalyzer(db)

# Let's look at the actual trades for 0.15 delta
print("INVESTIGATING 0.15 DELTA TRADES (10:00 AM entry)")
print("="*80)

df = analyzer.backtest_strangle_strategy("20250728", "20250801", entry_time="10:00", delta_target=0.15)

if len(df) > 0:
    print("\nDetailed Trade Breakdown:")
    for idx, row in df.iterrows():
        print(f"\n{row['date']}:")
        print(f"  SPY: ${row['entry_underlying']:.2f} → ${row['exit_underlying']:.2f} ({row['underlying_move_pct']:.2%} move)")
        print(f"  Strikes: {row['call_strike']} call / {row['put_strike']} put")
        print(f"  Entry Credit: ${row['entry_credit']:.2f}")
        print(f"  Exit Debit: ${row['exit_debit']:.2f}")
        print(f"  P&L: ${row['pnl']:.2f} ({row['pnl_pct']:.1%})")
        print(f"  Result: {'WIN' if row['won'] else 'LOSS'}")

# Let's check the actual deltas
print("\n\nACTUAL DELTAS AT ENTRY:")
print("-"*40)
for idx, row in df.iterrows():
    print(f"{row['date']}: Call delta={row['call_entry_delta']:.3f}, Put delta={row['put_entry_delta']:.3f}")

# Now let's compare with 0.30 delta
print("\n\nCOMPARING WITH 0.30 DELTA TRADES:")
print("="*80)

df30 = analyzer.backtest_strangle_strategy("20250728", "20250801", entry_time="10:00", delta_target=0.30)

if len(df30) > 0:
    print("\n0.15 Delta Summary:")
    print(f"  Average Entry Credit: ${df['entry_credit'].mean():.2f}")
    print(f"  Average Exit Debit: ${df['exit_debit'].mean():.2f}")
    print(f"  Win Rate: {df['won'].mean()*100:.0f}%")
    
    print("\n0.30 Delta Summary:")
    print(f"  Average Entry Credit: ${df30['entry_credit'].mean():.2f}")
    print(f"  Average Exit Debit: ${df30['exit_debit'].mean():.2f}")
    print(f"  Win Rate: {df30['won'].mean()*100:.0f}%")

# Check if there's a data issue
print("\n\nDATA QUALITY CHECK:")
print("-"*40)

# Load raw data for one day
date = "20250801"
raw_df = db.load_zero_dte_data(date)
print(f"\nTotal records for {date}: {len(raw_df)}")

# Check bid/ask spreads
strangles = db.get_zero_dte_strangles(date, delta_target=0.15)
if not strangles.empty:
    strangles['call_spread'] = strangles['call_ask'] - strangles['call_bid']
    strangles['put_spread'] = strangles['put_ask'] - strangles['put_bid']
    
    # Sample at 10:00
    entry_time = "2025-08-01T10:00:00"
    entry_data = strangles[strangles['timestamp'] == entry_time]
    
    if not entry_data.empty:
        print(f"\nAt 10:00 AM on {date}:")
        print(f"  Call: bid=${entry_data.iloc[0]['call_bid']:.2f}, ask=${entry_data.iloc[0]['call_ask']:.2f}, spread=${entry_data.iloc[0]['call_spread']:.2f}")
        print(f"  Put: bid=${entry_data.iloc[0]['put_bid']:.2f}, ask=${entry_data.iloc[0]['put_ask']:.2f}, spread=${entry_data.iloc[0]['put_spread']:.2f}")
        print(f"  Total spread: ${(entry_data.iloc[0]['call_spread'] + entry_data.iloc[0]['put_spread']):.2f}")

# Check for zero prices
print("\n\nCHECKING FOR ZERO/INVALID PRICES:")
zero_bids = len(strangles[(strangles['call_bid'] == 0) | (strangles['put_bid'] == 0)])
print(f"Strangles with zero bids: {zero_bids} out of {len(strangles)}")