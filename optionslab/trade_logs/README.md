# Trade Logs Directory

This directory contains comprehensive trade logs from all backtesting sessions.

## Directory Structure

```
trade_logs/
├── YYYY/           # Year
│   └── MM/         # Month
│       └── trades_{strategy}_{start_date}_to_{end_date}_{timestamp}.csv
│       └── trades_{strategy}_{start_date}_to_{end_date}_{timestamp}.json
├── archived/       # Deleted/archived logs for recovery
└── index.json      # Metadata index of all logs
```

## File Format

Each trade log contains:
- **CSV Format**: Full trade details in tabular format
- **JSON Format**: Same data in structured JSON for programmatic access

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

For AI analysis, use the `index.json` file to:
1. Find logs by date range or strategy
2. Load multiple logs for trend analysis
3. Access summary statistics without parsing full files

Example AI query:
"Analyze all long call trades from January 2025 and identify patterns in profitable vs losing trades"

## Maintenance

- Logs older than 90 days are automatically archived
- Use the Log Management tab in the Gradio interface to:
  - View historical logs
  - Delete specific logs
  - Clear old logs
  - Export logs for external analysis