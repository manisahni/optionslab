# Unified Greeks Methodology - Dashboard & Backtests

## Summary of Changes

We've unified the Greeks calculation methodology between the dashboard and backtests to ensure consistency. Both now use market-derived implied volatility calculated from bid/ask prices.

## Previous Issues

### Dashboard (Before)
- Used fixed 36.4% IV for all options
- Didn't match backtest results
- Ignored actual market conditions

### Backtests
- Calculated IV from bid/ask prices
- Recalculated Greeks with market IV
- Achieved 93.7% win rate

## Current Implementation

### Unified Approach
Both dashboard and backtests now:
1. **Calculate IV from market prices** using Newton-Raphson method
2. **Use market-derived IV** for Greeks calculations
3. **Apply same Black-Scholes formulas**

### Key Files Created/Updated

1. **`calculate_market_iv.py`**
   - Calculates implied volatility from bid/ask prices
   - Updates `options_data` table with market IV
   - Handles edge cases and validation

2. **`regenerate_accurate_greeks_v2.py`**
   - Uses market IV from `options_data` table
   - Falls back to reasonable estimates when needed
   - Generates consistent Greeks for dashboard

## Results

### Market IV Calculation
- Successfully calculated IV for 87.8% of options
- Average IV: **45.8%** (realistic for 0DTE)
- Range: 5.4% - 96.3% (shows volatility smile)

### Greeks Values
- Entry Delta: ~0.08 (realistic for $2 OTM)
- IV: 36-42% (market-calibrated)
- Greeks decay smoothly to expiry

## Database Structure

### `options_data` Table
```sql
- timestamp: When data was captured
- strike: Option strike price
- option_type: 'call' or 'put'
- bid/ask: Market prices
- iv: Market-derived IV (calculated)
```

### `greeks_history` Table
```sql
- timestamp: Time point
- total_delta/gamma/theta/vega: Greeks
- call_iv/put_iv: Market-derived IV used
- underlying_price: SPY price
```

## Verification

### To verify Greeks are consistent:
```python
# Check IV in options_data
SELECT AVG(iv), MIN(iv), MAX(iv) 
FROM options_data 
WHERE iv IS NOT NULL;
-- Result: AVG 45.8%, realistic for 0DTE

# Check Greeks in dashboard
SELECT AVG(call_iv) 
FROM greeks_history;
-- Result: 39%, using market-calibrated values
```

## Next Steps

### Completed ✅
1. Created market IV calculator
2. Updated Greeks generator to use market IV
3. Regenerated historical Greeks
4. Verified realistic values

### Remaining Tasks
1. Ensure live updates use same methodology
2. Add real-time IV calculation for new data
3. Monitor Greeks accuracy vs actual P&L

## Key Insight

The critical difference was IV source:
- **Wrong**: Fixed IV or broker-provided IV
- **Right**: IV calculated from actual bid/ask prices

This matches exactly what successful backtests did, ensuring dashboard Greeks now reflect true market risk.

---
*Updated: August 7, 2025*