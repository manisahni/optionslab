# Trade Logs Directory

This directory contains comprehensive trade logs from all backtesting sessions.

## Directory Structure

```
trade_logs/
├── YYYY/           # Year
│   └── MM/         # Month
│       └── {backtest_id}_{memorable_name}_{timestamp}.csv
├── archived/       # Deleted/archived logs for recovery
└── index.csv       # Metadata index of all logs
```

## File Format

Each trade log is a comprehensive CSV file containing:
- **Metadata Header**: Backtest configuration and performance metrics as CSV comments
- **Strategy Configuration**: Complete strategy parameters
- **Trade Data**: Full trade details in tabular format
- **Audit Log**: Optional execution audit trail

## Fields Included

1. **Trade Identification**
   - trade_id, entry_date, exit_date
   - option_type (C/P), strike, expiration

2. **Pricing Information**
   - entry_price, exit_price
   - bid/ask spreads at entry and exit
   - contracts, total cost

3. **Greeks**
   - Delta, Gamma, Theta, Vega, Rho
   - Values at both entry and exit

4. **Performance Metrics**
   - P&L ($), P&L (%)
   - Annualized return
   - Days held

5. **Market Context**
   - Underlying price at entry/exit
   - Underlying move ($ and %)
   - IV at entry/exit

6. **Strategy Logic**
   - Entry reason
   - Exit reason

## AI Access Guide

For AI analysis, use the comprehensive CSV files to:
1. Access complete backtest data including metadata, config, and trades
2. Find logs using the `index.csv` file by date range or strategy
3. Load multiple logs for trend analysis
4. Each CSV file contains all data linked by a unique backtest ID

Example AI query:
"Analyze all long call trades from January 2025 and identify patterns in profitable vs losing trades"

## Maintenance

- Logs older than 90 days are automatically archived
- Use the Log Management tab in the Gradio interface to:
  - View historical logs
  - Delete specific logs
  - Clear old logs
  - Export logs for external analysis