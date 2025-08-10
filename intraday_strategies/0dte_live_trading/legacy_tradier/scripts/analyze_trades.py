#!/usr/bin/env python3
"""
Analyze all three days of trading with real data and Greeks
"""

import sqlite3
from datetime import datetime

print("=" * 70)
print("VEGAAWARE STRATEGY ANALYSIS WITH REAL DATA")
print("=" * 70)

conn = sqlite3.connect('database/market_data.db')
cur = conn.cursor()

dates = ['2025-08-06', '2025-08-07', '2025-08-08']

for date in dates:
    print(f"\n{'=' * 70}")
    print(f"{date} TRADE ANALYSIS")
    print("=" * 70)
    
    # Get SPY price at entry (3:00 PM)
    cur.execute("""
        SELECT close FROM spy_prices
        WHERE timestamp = ? || ' 15:00:00'
    """, (date,))
    spy_entry = cur.fetchone()[0]
    
    # Get SPY price at exit (4:00 PM)
    cur.execute("""
        SELECT close FROM spy_prices
        WHERE timestamp = ? || ' 16:00:00'
    """, (date,))
    spy_exit = cur.fetchone()[0]
    
    print(f"\nUNDERLYING MOVEMENT:")
    print(f"  Entry (3:00 PM): ${spy_entry:.2f}")
    print(f"  Exit (4:00 PM):  ${spy_exit:.2f}")
    print(f"  Move: ${spy_exit - spy_entry:.2f} ({((spy_exit/spy_entry - 1) * 100):.2f}%)")
    
    # Get options data
    cur.execute("""
        SELECT 
            option_type,
            strike,
            last as entry_price,
            iv as entry_iv,
            delta as entry_delta,
            theta as entry_theta
        FROM options_data
        WHERE timestamp = ? || ' 15:00:00'
        ORDER BY option_type DESC
    """, (date,))
    
    entry_options = cur.fetchall()
    
    cur.execute("""
        SELECT 
            option_type,
            strike,
            last as exit_price,
            iv as exit_iv,
            delta as exit_delta,
            theta as exit_theta
        FROM options_data
        WHERE timestamp = ? || ' 16:00:00'
        ORDER BY option_type DESC
    """, (date,))
    
    exit_options = cur.fetchall()
    
    if len(entry_options) == 2 and len(exit_options) == 2:
        print(f"\nSTRANGLE POSITION:")
        
        total_collected = 0
        total_exit = 0
        
        for i in range(2):
            entry = entry_options[i]
            exit = exit_options[i]
            
            option_type = entry[0].upper()
            strike = entry[1]
            entry_price = entry[2]
            exit_price = exit[2]
            
            total_collected += entry_price
            total_exit += exit_price
            
            print(f"\n  {option_type} ${strike:.0f}:")
            print(f"    Entry: ${entry_price:.2f} (IV: {entry[3]:.1%}, Delta: {entry[4]:.3f})")
            print(f"    Exit:  ${exit_price:.2f} (IV: {exit[3]:.1%}, Delta: {exit[4]:.3f})")
            print(f"    P&L: ${exit_price - entry_price:.2f}")
            
            # Check if option is ITM at exit
            if option_type == 'PUT':
                itm = spy_exit < strike
            else:
                itm = spy_exit > strike
            
            if itm:
                print(f"    ⚠️ IN THE MONEY at exit!")
        
        # Calculate overall P&L
        pnl = total_exit - total_collected
        pnl_pct = (pnl / total_collected) * 100 if total_collected > 0 else 0
        
        print(f"\n  TOTAL PREMIUM COLLECTED: ${total_collected:.2f}")
        print(f"  TOTAL EXIT VALUE: ${total_exit:.2f}")
        print(f"  P&L: ${pnl:.2f} ({pnl_pct:.1f}%)")
        
        if pnl < 0:
            print(f"  ✅ PROFITABLE TRADE (sold high, bought back lower)")
        else:
            print(f"  ❌ LOSING TRADE (bought back higher than sold)")
        
        # Check if price stayed within strikes
        call_strike = max(entry_options[0][1], entry_options[1][1])
        put_strike = min(entry_options[0][1], entry_options[1][1])
        
        if put_strike < spy_exit < call_strike:
            print(f"  ✅ Price stayed within strikes ({put_strike} < {spy_exit:.2f} < {call_strike})")
        else:
            print(f"  ❌ Price breached strikes")
        
        # Analyze why the trade won or lost
        print(f"\n  ANALYSIS:")
        
        # Calculate IV change
        avg_entry_iv = sum(opt[3] for opt in entry_options) / 2
        avg_exit_iv = sum(opt[3] for opt in exit_options) / 2
        iv_change = avg_exit_iv - avg_entry_iv
        
        print(f"    IV Change: {iv_change:.1%}")
        if iv_change > 0.5:
            print(f"    ⚠️ Significant IV expansion hurt the position")
        elif iv_change < -0.5:
            print(f"    ✅ IV contraction helped the position")
        
        # Time decay effect
        total_theta = sum(opt[5] for opt in entry_options)
        expected_decay = total_theta / (365 * 24)  # 1 hour decay
        print(f"    Expected 1hr decay: ${expected_decay:.2f}")
        
        actual_change = total_exit - total_collected
        decay_vs_actual = expected_decay - actual_change
        print(f"    Actual change: ${actual_change:.2f}")
        
        if abs(decay_vs_actual) > 0.10:
            print(f"    ⚠️ Large deviation from expected decay (${decay_vs_actual:.2f})")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

# Calculate overall statistics
cur.execute("""
    SELECT 
        date(o1.timestamp) as trade_date,
        SUM(CASE WHEN o1.timestamp LIKE '% 15:00:00' THEN o1.last ELSE 0 END) as entry_total,
        SUM(CASE WHEN o1.timestamp LIKE '% 16:00:00' THEN o1.last ELSE 0 END) as exit_total
    FROM options_data o1
    WHERE time(o1.timestamp) IN ('15:00:00', '16:00:00')
    AND date(o1.timestamp) IN ('2025-08-06', '2025-08-07', '2025-08-08')
    GROUP BY date(o1.timestamp)
""")

results = cur.fetchall()
total_pnl = 0
winning_trades = 0

for date, entry, exit in results:
    # For short strangles, profit when exit < entry
    trade_pnl = entry - exit
    total_pnl += trade_pnl
    if trade_pnl > 0:
        winning_trades += 1

print(f"\nTotal trades: {len(results)}")
print(f"Winning trades: {winning_trades}")
print(f"Win rate: {(winning_trades/len(results)*100):.1f}%")
print(f"Total P&L: ${total_pnl:.2f}")

conn.close()