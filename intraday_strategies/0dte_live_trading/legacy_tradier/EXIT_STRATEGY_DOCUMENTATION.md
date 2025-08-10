# 0DTE Exit Strategy Documentation

## The 15:55 Rule - Why Real Traders Exit Early

### Summary
While our Greeks calculations run until market close (4:00 PM), **real 0DTE traders typically close positions by 3:55 PM** to avoid the mathematical chaos and unpredictable price movements of the final minutes.

## Data Architecture

### Database Layer (Complete Data)
- **Calculation Period**: 2:00 PM - 4:00 PM (120 minutes)
- **Greeks Storage**: Full calculations including explosive final minutes
- **Data Integrity**: Consistent between backtests and live trading
- **Purpose**: Complete picture for analysis and research

### Display Layer (Practical View)
- **Display Period**: 2:00 PM - 3:55 PM (115 minutes)
- **Cutoff Reason**: Avoid showing misleading explosive Greeks
- **User Experience**: Clean, interpretable visualizations
- **Purpose**: Practical trading decisions

## Why This Approach?

### 1. Mathematical Reality
In the final 2-3 minutes of 0DTE options:
- **Delta** can explode from -0.02 to -0.31
- **Theta** can spike from $78 to $162/day
- **Gamma** becomes extremely volatile
- These values are **mathematically correct** but **practically unusable**

### 2. Real Trading Behavior
Professional 0DTE traders:
- Close positions 5-10 minutes before expiry
- Avoid "gamma risk" in final minutes
- Prevent assignment risk
- Maintain disciplined risk management

### 3. Data Consistency
By keeping full calculations but controlling display:
- Backtests use identical calculations
- Live trading uses same data
- Strategy layer handles exit timing
- No data regeneration needed for different exit times

## Implementation

### Greeks Generation (Full Data)
```python
# Calculate full market hours
time_range = "14:00:00 to 16:00:00"  # 2 PM to 4 PM
records = 120  # Full 2-hour data
```

### Dashboard Display (Practical View)
```sql
-- Show only until 3:55 PM
SELECT * FROM greeks_history
WHERE time(timestamp) >= '14:00:00'
  AND time(timestamp) <= '15:55:00'  -- Stop before chaos
```

### Strategy Exit Logic
```python
if current_time >= "15:55":
    close_position()  # Exit before final minutes
```

## Greeks Behavior Comparison

| Time | Delta | Theta ($/day) | Gamma | Behavior |
|------|-------|---------------|-------|----------|
| 15:50 | -0.035 | $83.72 | -0.240 | Normal |
| 15:55 | -0.024 | $78.52 | -0.225 | Last safe exit |
| 15:57 | -0.131 | $81.70 | -0.234 | Starting chaos |
| 15:59 | -0.311 | $90.56 | -0.258 | Full explosion |

## Best Practices

### For Live Trading
1. **Set alerts** for 3:50 PM to prepare for exit
2. **Close by 3:55 PM** latest
3. **Never hold** into final 2 minutes
4. **Use limit orders** to ensure fills

### For Backtesting
1. **Apply same 15:55 exit** for fair comparison
2. **Calculate P&L** at 15:55 prices
3. **Mark as "closed early"** in logs
4. **Track both** practical and theoretical results

### For Analysis
1. **Full data available** if needed for research
2. **Can adjust cutoff** without regenerating data
3. **Compare different** exit times easily
4. **Study final minutes** separately if desired

## Configuration

### To Change Exit Time
Simply modify the dashboard query:
```sql
-- For 3:50 PM exit
AND time(timestamp) <= '15:50:00'

-- For 3:45 PM exit  
AND time(timestamp) <= '15:45:00'
```

No data regeneration needed!

## Conclusion

This approach gives us the best of both worlds:
- **Complete data** for thorough analysis
- **Practical display** for real trading
- **Flexibility** to adjust without recalculation
- **Consistency** across all systems

The 15:55 cutoff is not a limitation - it's a **risk management feature** that reflects how professional traders actually manage 0DTE positions.

---
*Last Updated: August 7, 2025*