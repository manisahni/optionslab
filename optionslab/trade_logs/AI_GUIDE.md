# AI Guide for Trade Log Analysis

## Quick Start for AI Analysis

### 1. Finding Logs
```python
# Load the index to find available logs
import pandas as pd
index_df = pd.read_csv('trade_logs/index.csv')

# Find logs by strategy
long_call_logs = index_df[index_df['strategy'].str.contains('long_call', na=False)]

# Find logs by date range
jan_2025_logs = index_df[(index_df['year'] == 2025) & (index_df['month'] == 1)]

# Load a comprehensive CSV file
from optionslab.csv_enhanced import load_comprehensive_csv
backtest_data = load_comprehensive_csv('path/to/backtest.csv')
metadata = backtest_data['metadata']
trades_df = backtest_data['trades']
strategy_config = backtest_data['strategy_config']
```

### 2. Analyzing Trade Patterns
Common analysis tasks:
- **Win Rate Analysis**: Compare entry/exit conditions of winning vs losing trades
- **Greeks Evolution**: Track how Delta, Theta, etc. change from entry to exit
- **Market Timing**: Analyze underlying price movements vs option performance
- **Strategy Optimization**: Identify optimal entry/exit parameters

### 3. Data Structure
Each comprehensive CSV file contains:

**Metadata Header Section:**
```
# BACKTEST_ID,unique-identifier-here
# MEMORABLE_NAME,backtest_name
# STRATEGY,simple_long_call
# START_DATE,2022-01-01
# END_DATE,2022-12-31
# INITIAL_CAPITAL,10000
# FINAL_VALUE,9156.00
# TOTAL_RETURN,-0.0844
# SHARPE_RATIO,0.85
# MAX_DRAWDOWN,-0.15
# WIN_RATE,0.44
# TOTAL_TRADES,25
```

**Trade Data Section:**
```csv
backtest_id,trade_id,entry_date,option_type,strike,entry_delta,exit_delta,pnl,pnl_pct,...
uuid-here,1,2022-01-03,C,487.5,0.112,0.025,-374.00,-79.07,...
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
- Use the comprehensive CSV format for complete backtest data
- Load index.csv first to find relevant backtests
- Each CSV file contains all data linked by a unique backtest ID
- CSV format is Excel-compatible for additional analysis
- Use pandas DataFrame for complex analysis
- The csv_enhanced module provides easy loading of all data sections