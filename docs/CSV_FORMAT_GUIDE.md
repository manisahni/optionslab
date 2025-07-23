# Comprehensive CSV Format Guide

## Overview

The OptionsLab system uses a comprehensive CSV format that stores all backtest data in a single Excel-compatible file. Each CSV file contains complete backtest information linked by a unique backtest ID, ensuring full traceability from strategy execution to analysis.

## File Structure

### File Naming Convention
```
{backtest_id}_{memorable_name}_{timestamp}.csv
```

Example:
```
17cc0ae9-10b5-453f-aa53-986ad87968fd_sunrise_strategy_20250722_231610.csv
```

### CSV Sections

#### 1. Metadata Header Section
The file begins with metadata stored as CSV comments (lines starting with `#`):

```csv
# BACKTEST_ID,17cc0ae9-10b5-453f-aa53-986ad87968fd
# MEMORABLE_NAME,sunrise_strategy
# STRATEGY,simple_long_call
# STRATEGY_FILE,strategies/long_call.yaml
# START_DATE,2022-01-01
# END_DATE,2022-12-31
# BACKTEST_DATE,2025-07-22T23:16:10
# INITIAL_CAPITAL,10000
# FINAL_VALUE,9156.00
# TOTAL_RETURN,-0.0844
# SHARPE_RATIO,0.8523
# MAX_DRAWDOWN,-0.1567
# WIN_RATE,0.44
# TOTAL_TRADES,25
```

#### 2. Compliance Scorecard Section
Performance compliance metrics:

```csv
# 
# COMPLIANCE SCORECARD
# OVERALL_COMPLIANCE,85.60
# DELTA_COMPLIANCE,92.00
# DTE_COMPLIANCE,88.00
# COMPLIANT_TRADES,21
# NON_COMPLIANT_TRADES,4
```

#### 3. Strategy Configuration Section
Complete strategy parameters in hierarchical format:

```csv
# 
# STRATEGY CONFIGURATION
# STRATEGY_CONFIG,name,Simple Long Call
# STRATEGY_CONFIG,description,Buy OTM calls when conditions align
# STRATEGY_CONFIG,parameters,<section>
# STRATEGY_CONFIG,.initial_capital,10000
# STRATEGY_CONFIG,.position_size,0.05
# STRATEGY_CONFIG,.max_positions,1
# STRATEGY_CONFIG,.entry,<section>
# STRATEGY_CONFIG,..delta_range,[0.25, 0.40]
# STRATEGY_CONFIG,..dte_range,[30, 60]
# STRATEGY_CONFIG,.exit,<section>
# STRATEGY_CONFIG,..profit_target,0.5
# STRATEGY_CONFIG,..stop_loss,-0.5
# STRATEGY_CONFIG,..max_hold_days,30
```

#### 4. Audit Log Section (Optional)
Execution audit trail:

```csv
# 
# AUDIT LOG (Last 100 lines)
# AUDIT,"🚀 AUDIT: Starting auditable backtest"
# AUDIT,"🔑 AUDIT: Backtest ID: 17cc0ae9-10b5-453f-aa53-986ad87968fd"
# AUDIT,"📅 AUDIT: Processing 2022-01-03"
# AUDIT,"✅ AUDIT: Executing trade"
```

#### 5. Trade Data Section
After the header sections, the actual trade data begins:

```csv
# 
# ===== TRADE DATA BEGINS BELOW =====
# 
backtest_id,trade_id,entry_date,exit_date,option_type,strike,expiration,contracts,entry_price,exit_price,entry_underlying,exit_underlying,pnl,pnl_pct,days_held,exit_reason,entry_delta,exit_delta,entry_iv,exit_iv,compliance_score,greeks_history
17cc0ae9-10b5-453f-aa53-986ad87968fd,T1,2022-01-03,2022-01-14,C,470.0,2022-02-18,21,2.25,0.48,463.67,459.87,-374.25,-79.07,11,stop_loss,0.35,0.12,0.1823,0.2156,85.0,"[{""date"":""2022-01-03"",""delta"":0.35,...}]"
```

## Loading CSV Files

### Using the csv_enhanced Module

```python
from optionslab.csv_enhanced import load_comprehensive_csv

# Load a comprehensive CSV file
data = load_comprehensive_csv('path/to/backtest.csv')

# Access different sections
metadata = data['metadata']
strategy_config = data['strategy_config']
trades_df = data['trades']
audit_log = data['audit_log']

# Access specific metadata
backtest_id = metadata['backtest_id']
total_return = metadata['total_return']
sharpe_ratio = metadata['sharpe_ratio']
```

### Using Pandas Directly

For just the trade data:

```python
import pandas as pd

# Skip header lines and load trade data
with open('path/to/backtest.csv', 'r') as f:
    lines = f.readlines()
    
# Find where trade data starts
trade_start = 0
for i, line in enumerate(lines):
    if '===== TRADE DATA BEGINS BELOW =====' in line:
        trade_start = i + 2
        break

# Load trades
trades_df = pd.read_csv('path/to/backtest.csv', skiprows=trade_start)
```

## Excel Compatibility

The CSV format is fully Excel-compatible:

1. **Open in Excel**: Double-click the CSV file to open in Excel
2. **Header Comments**: Metadata appears as comments at the top
3. **Trade Data**: Starts after the header separator, formatted as a standard table
4. **Filtering**: Use Excel's filter features on the trade data
5. **Pivot Tables**: Create pivot tables from the trade data section

## Benefits

1. **Single File**: All backtest data in one place
2. **Unique ID**: Complete traceability with backtest_id
3. **Self-Contained**: Strategy configuration included
4. **Excel-Compatible**: Easy analysis without programming
5. **Human-Readable**: Clear section separators and formatting
6. **AI-Friendly**: Structured format for AI analysis

## Example Use Cases

### Finding Profitable Trades
```python
# Load data
data = load_comprehensive_csv('backtest.csv')
trades = data['trades']

# Find profitable trades
profitable = trades[trades['pnl'] > 0]
print(f"Win rate: {len(profitable) / len(trades):.2%}")
```

### Analyzing by Exit Reason
```python
# Group by exit reason
exit_analysis = trades.groupby('exit_reason').agg({
    'pnl': ['count', 'sum', 'mean'],
    'pnl_pct': 'mean'
})
print(exit_analysis)
```

### Loading into Excel for Custom Analysis
1. Open the CSV file in Excel
2. Select the trade data (below the header)
3. Insert → Table
4. Use Excel's analysis tools (pivot tables, charts, etc.)

## Migration from JSON

If you have existing JSON files, the system automatically handles CSV format now. The AI assistant and UI have been updated to work exclusively with the comprehensive CSV format.