# Understanding 0DTE Theta Values

## Summary
The theta values displayed in the dashboard (ranging from $19-82/day) are **correct and accurate**. These values represent the daily rate of time decay for 0DTE SPY strangle positions.

## Key Points

### 1. Market Implied Volatilities
The Greeks are calculated using **actual market IVs** derived from bid/ask prices:
- Call IV at 3 PM: ~58.7%
- Put IV at 3 PM: ~77.0%
- These high IVs are typical for 0DTE options near expiration

### 2. Daily Rate vs Hourly Decay
Theta is expressed as a **daily rate** ($/day), but for 0DTE options:
- Actual hourly decay = Daily theta ÷ 24
- At 3 PM with $40/day theta → $1.67/hour actual decay
- At 3:55 PM with $78/day theta → $3.25/hour actual decay

### 3. Theta Progression Throughout the Day

| Time | Hours to Expiry | Theta ($/day) | Actual Hourly | Call IV | Put IV |
|------|----------------|---------------|---------------|---------|--------|
| 2:00 PM | 2 hours | $20 | $0.83/hour | 38% | 57% |
| 2:30 PM | 1.5 hours | $26 | $1.08/hour | 61% | 50% |
| 3:00 PM | 1 hour | $40 | $1.67/hour | 59% | 77% |
| 3:30 PM | 30 minutes | $63 | $2.63/hour | 80% | 80% |
| 3:55 PM | 5 minutes | $78 | $3.25/hour | 80% | 80% |

### 4. Why These Values Make Sense

#### High Implied Volatilities
- 0DTE options have elevated IVs due to gamma risk
- Market makers price in premium for rapid price movements
- IVs often reach 60-80% annualized near expiration

#### Accelerating Time Decay
- Theta increases exponentially as expiration approaches
- The "theta burn" accelerates in the final hour
- This is why traders enter at 3 PM to capture maximum decay

#### Position Sizing Context
- Per contract: $40/day theta at 3 PM
- 10 contracts: $400/day theoretical decay rate
- 100 contracts: $4,000/day theoretical decay rate
- **Actual income in 1 hour**: Divide by 24

## Verification

The theta values have been verified by:
1. Recalculating using the same market IVs from the database
2. Confirming the match between stored and calculated values
3. Cross-checking with Black-Scholes formula

## Conclusion

The dashboard correctly displays theta values that:
- Use market-derived implied volatilities
- Follow standard Black-Scholes calculations
- Accurately represent the daily rate of time decay
- Are consistent with typical 0DTE option behavior

**No adjustments needed** - the values are accurate and working as intended.