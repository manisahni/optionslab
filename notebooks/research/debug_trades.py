#!/usr/bin/env python3

# Quick script to debug our strategy trades
import sys
import os
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

# Import and run our strategy to get trade details
exec(open('/Users/nish_macbook/trading/daily-optionslab/notebooks/research/volatility_protected_leaps.py').read())

print("\n" + "="*60)
print("STRATEGY TRADE DEBUG ANALYSIS")
print("="*60)

if len(strategy.trades) > 0:
    import pandas as pd
    trades_df = pd.DataFrame(strategy.trades)
    
    print("All Strategy Trades:")
    print(trades_df[['date', 'action', 'strike', 'price', 'quantity']].to_string())
    
    print("\n" + "="*40)
    print("LEAP TRADE ANALYSIS")
    print("="*40)
    
    leap_buys = trades_df[trades_df['action'] == 'buy_leap']
    leap_sells = trades_df[trades_df['action'] == 'close_leap']
    
    print(f"LEAP Buys: {len(leap_buys)}")
    print(f"LEAP Sells: {len(leap_sells)}")
    
    for i, buy in leap_buys.iterrows():
        print(f"\nLEAP Trade {i}:")
        print(f"  Buy: {buy['date'].date()} - Strike ${buy['strike']:.0f} @ ${buy['price']:.2f}")
        
        # Find corresponding sell
        matching_sells = leap_sells[
            (leap_sells['strike'] == buy['strike']) & 
            (leap_sells['date'] > buy['date'])
        ]
        
        if len(matching_sells) > 0:
            sell = matching_sells.iloc[0]
            pnl = (sell['price'] - buy['price']) * buy['quantity']
            pnl_pct = (sell['price'] - buy['price']) / buy['price'] * 100
            
            print(f"  Sell: {sell['date'].date()} - Strike ${sell['strike']:.0f} @ ${sell['price']:.2f}")
            print(f"  P&L: ${pnl:.2f} ({pnl_pct:.1f}%)")
            
            # Check SPY performance during this trade
            spy_buy = spy_prices[spy_prices['date'] == buy['date']]['spy_price'].iloc[0]
            spy_sell = spy_prices[spy_prices['date'] == sell['date']]['spy_price'].iloc[0]
            spy_pnl_pct = (spy_sell - spy_buy) / spy_buy * 100
            
            print(f"  SPY during same period: {spy_pnl_pct:.1f}%")
            print(f"  LEAP leverage: {pnl_pct/spy_pnl_pct:.1f}x" if spy_pnl_pct != 0 else "  LEAP leverage: N/A")
        else:
            print(f"  Still open or no matching sell found")
    
    print("\n" + "="*40)
    print("PROTECTION TRADE ANALYSIS")
    print("="*40)
    
    protection_trades = trades_df[trades_df['action'].str.contains('protection')]
    protection_cost = protection_trades[protection_trades['action'] == 'buy_protection']['price'].sum()
    print(f"Total protection cost: ${protection_cost:.2f}")
    
    if len(protection_trades) > 0:
        print("Protection trades:")
        print(protection_trades[['date', 'action', 'strike', 'price']].to_string())

print("\n" + "="*40)
print("PORTFOLIO VALUE ANALYSIS")
print("="*40)

print(f"Initial Capital: $10,000")
print(f"Final Value: ${results['total_value'].iloc[-1]:,.2f}")
print(f"Final Cash: ${results['capital'].iloc[-1]:,.2f}")
print(f"Final Position Value: ${results['position_value'].iloc[-1]:,.2f}")

# Check if we still have open positions
if len(strategy.positions) > 0:
    print(f"\nOpen Positions: {len(strategy.positions)}")
    for pos in strategy.positions:
        print(f"  {pos['type']}: Strike ${pos['strike']:.0f}, Entry ${pos['entry_price']:.2f}")
else:
    print("\nNo open positions")

print("\nThis helps identify:")
print("1. Are we buying good LEAPs?")
print("2. Are we selling too early/late?") 
print("3. Is protection too expensive?")
print("4. Are there implementation bugs?")