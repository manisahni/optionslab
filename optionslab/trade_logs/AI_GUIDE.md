# AI Guide for Trade Log Analysis

## Quick Start for AI Analysis

### 1. Finding Logs
```python
# Load the index to find available logs
import json
with open('trade_logs/index.json', 'r') as f:
    index = json.load(f)

# Find logs by strategy
long_call_logs = [log for log in index['logs'] if 'long_call' in log['strategy']]

# Find logs by date range
jan_2025_logs = [log for log in index['logs'] if log['year'] == 2025 and log['month'] == 1]
```

### 2. Analyzing Trade Patterns
Common analysis tasks:
- **Win Rate Analysis**: Compare entry/exit conditions of winning vs losing trades
- **Greeks Evolution**: Track how Delta, Theta, etc. change from entry to exit
- **Market Timing**: Analyze underlying price movements vs option performance
- **Strategy Optimization**: Identify optimal entry/exit parameters

### 3. Data Structure
Each log file contains:
```json
{
  "metadata": {
    "strategy": "simple_long_call",
    "backtest_date": "2025-01-19",
    "start_date": "2022-01-01",
    "end_date": "2022-12-31",
    "initial_capital": 10000,
    "final_value": 9156.00,
    "total_return": -0.0844,
    "total_trades": 25,
    "win_rate": 0.44
  },
  "trades": [
    {
      "trade_id": 1,
      "entry_date": "2022-01-03",
      "option_type": "C",
      "strike": 487.5,
      "entry_delta": 0.112,
      "exit_delta": 0.025,
      "pnl": -374.00,
      "pnl_pct": -79.07,
      // ... all other fields
    }
  ]
}
```

### 4. Key Metrics for AI Analysis

**Entry Quality Indicators:**
- entry_delta (directional exposure)
- entry_iv (implied volatility)
- entry_spread_pct (liquidity indicator)
- dte_at_entry (time value)

**Exit Quality Indicators:**
- exit_reason (strategy logic validation)
- days_held vs max_hold_days
- underlying_move_pct (market direction accuracy)

**Performance Correlations:**
- annualized_return (efficiency metric)
- pnl_pct vs underlying_move_pct (leverage effectiveness)
- IV change (entry_iv → exit_iv)

### 5. Example Analysis Queries

1. **"What's the optimal Delta range for entry?"**
   - Group trades by entry_delta ranges
   - Calculate win rate and average return per range

2. **"How does IV affect returns?"**
   - Correlate entry_iv with pnl_pct
   - Identify IV environments that favor the strategy

3. **"What are common characteristics of big winners?"**
   - Filter trades with pnl_pct > 100%
   - Analyze their entry conditions

4. **"How effective are the exit rules?"**
   - Group by exit_reason
   - Compare actual returns vs potential if held longer

### 6. Performance Tips
- Use JSON format for structured analysis
- Load index.json first to avoid scanning all files
- Cache frequently accessed logs
- Use pandas DataFrame for complex analysis