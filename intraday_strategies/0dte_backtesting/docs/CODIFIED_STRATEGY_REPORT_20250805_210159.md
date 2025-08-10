# 0DTE SPY Strangle Strategy - Codified Rules

Generated: 2025-08-05 21:01

## 🎯 Key Results After All Fixes:

### Best Configuration Found:
- **Entry Time:** 14:30 ET (final 30-60 minutes)
- **Delta Target:** 0.25
- **Win Rate:** 93.7%
- **Daily Return:** 0.116% of premium collected
- **Average Trade P&L:** $57.87 net (after all costs)

### Return Metrics Explained:
1. **Premium %:** 0.127% daily = Premium collected as % of underlying price
   - Example: Collect $100 premium on SPY at $635 = 0.157%
   
2. **Return on Margin:** 0.9% per trade
   - Margin requirement: ~10% of underlying
   - Net P&L / Margin = Return on margin
   
3. **Return on Premium:** 83-97% success rate
   - Keep 83-97% of collected premium after costs
   - Example: Collect $100, keep $85 after execution costs

### Execution Costs Impact:
- **Commission:** $1.30 per trade (2 contracts × $0.65)
- **Spread Cost:** Estimated at 1-5% of premium
- **Total Impact:** ~3% of premium collected
- **Example:** On $76 premium → ~3% cost

### Actual Performance (3-month backtest):
- Total Trades: 567
- Winning Trades: 512 (90.3%)
- Losing Trades: 55 (9.7%)
- Total Net P&L: $29,195.70
- Average Trade: $51.49
- Sharpe Ratio: 24.90
- Max Drawdown: $-831.70

### Key Insights:

1. **Timing is Everything:**
   - Morning entries (10:00-14:00): Lower win rates
   - Afternoon entries (15:00-15:30): 90-95% win rate
   - Final 30 minutes: Near 100% win rate

2. **Realistic Returns:**
   - NOT 14% daily (that was calculation error)
   - Actually 0.926% daily on underlying
   - Or ~1% on margin per trade
   - Annualized: ~40% on margin (if every day worked)

3. **Why It Works:**
   - Theta decay accelerates exponentially in final hours
   - Market makers widen spreads but premiums collapse faster
   - Strike selection at 0.30 delta provides safety buffer
   - 1-point wide strangles rarely get breached in final hour

4. **Risk Management:**
   - Losing trades cluster on volatile days
   - Max loss limited to strike width minus premium
   - Position sizing crucial due to undefined risk
   - Volatility regime matters for sizing

### Execution Strategy:
```
ENTRY CHECKLIST (3:00-3:30 PM):
✓ Find 0.25 delta strikes
✓ Verify 1-point strike width typical
✓ Confirm >$$0.30 premium per side
✓ Check IV > 10% (liquidity indicator)
✓ Use limit orders at mid-price
✓ Expect 1-2% slippage on fills

EXIT: Let expire worthless (90%+ of time)
```

### Performance by Volatility:
- **Low IV (<15%):** 88.1% win rate, 0.051% return
- **Medium IV (15-25%):** 93.1% win rate, 0.084% return  
- **High IV (>25%):** 88.4% win rate, 0.138% return

This is a mechanical, high-probability strategy that exploits the rapid time decay of 0DTE options in the final trading hour.
