import pandas as pd

# Load results
results_15min = pd.read_csv('/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/real_orb_15min.csv')
results_30min = pd.read_csv('/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/real_orb_30min.csv')
results_60min = pd.read_csv('/Users/nish_macbook/0dte/orb_strategy/data/backtest_results/real_orb_60min.csv')

print("=" * 70)
print("DRAWDOWN ANALYSIS IN PERCENTAGE TERMS")
print("=" * 70)

for df, name in zip([results_15min, results_30min, results_60min], ['15-min', '30-min', '60-min']):
    # Calculate cumulative P&L
    df['cumulative_pnl'] = df['net_pnl'].cumsum()
    
    # Initial capital assumption
    # With $15 wide spreads, max risk is $1,500 per contract
    # Assume we need capital to cover 10 trades = $15,000
    initial_capital = 15000
    
    # Calculate running capital (initial + cumulative P&L)
    df['running_capital'] = initial_capital + df['cumulative_pnl']
    
    # Calculate drawdown
    running_max = df['cumulative_pnl'].expanding().max()
    drawdown_dollars = df['cumulative_pnl'] - running_max
    
    # Calculate percentage drawdown based on peak capital
    peak_capital = initial_capital + running_max
    drawdown_pct = (drawdown_dollars / peak_capital) * 100
    
    max_dd_dollars = drawdown_dollars.min()
    max_dd_pct = drawdown_pct.min()
    
    # Also calculate as % of initial capital
    max_dd_pct_of_initial = (max_dd_dollars / initial_capital) * 100
    
    total_return = df['cumulative_pnl'].iloc[-1]
    total_return_pct = (total_return / initial_capital) * 100
    
    print(f"\n{name} ORB:")
    print("-" * 40)
    print(f"Initial Capital:        ${initial_capital:,}")
    print(f"Final Capital:          ${initial_capital + total_return:,.0f}")
    print(f"Total Return:           ${total_return:,.0f} ({total_return_pct:.2f}%)")
    print(f"Max Drawdown ($):       ${max_dd_dollars:,.0f}")
    print(f"Max DD (% of peak):     {max_dd_pct:.2f}%")
    print(f"Max DD (% of initial):  {max_dd_pct_of_initial:.2f}%")
    print(f"Total Trades:           {len(df)}")
    print(f"Avg Trade Risk:         ${df['entry_credit'].mean() * 10:.0f}")  # Max risk estimate

print("\n" + "=" * 70)
print("SPY vs SPX EXPLANATION")
print("=" * 70)

print("""
We used SPY data for this backtest. Here's the key difference:

1. SPY (SPDR S&P 500 ETF):
   - An ETF that tracks the S&P 500 index
   - Trades at ~1/10th the price of SPX (e.g., SPY $560 vs SPX 5600)
   - Has actual shares you can buy/sell
   - Options are American-style (can exercise early)
   - More liquid with tighter bid/ask spreads
   - Options contracts represent 100 shares
   - Better for retail traders due to smaller size

2. SPX (S&P 500 Index):
   - The actual index value (not tradeable directly)
   - 10x larger than SPY (e.g., SPX 5600)
   - Cash-settled index options only
   - Options are European-style (exercise at expiration only)
   - Larger contract size ($100 x index value)
   - Tax advantages (60/40 long-term/short-term treatment)
   - Preferred by institutions due to size and tax benefits

For 0DTE Trading:
- SPY: Better for smaller accounts, tighter spreads
- SPX: Better tax treatment, but requires larger capital
- Both offer 0DTE options expiring Mon/Wed/Fri

Our backtest used SPY because:
1. The data was for SPY 0DTE options
2. More accessible for retail traders
3. Tighter bid/ask spreads
4. Easier to manage position sizes
""")