# SPY Options Backtester

A comprehensive command-line tool for backtesting options trading strategies using historical SPY options data.

## Features

- **Multiple Strategies**: Long calls, long puts, straddles, covered calls, and custom strategies
- **Professional Portfolio Management**: Position tracking, P&L calculation, Greeks monitoring
- **Risk Management**: Portfolio-level risk controls, position sizing, VaR calculations
- **Comprehensive Reporting**: HTML reports, performance charts, trade analysis
- **High-Performance Data Processing**: Efficient handling of 5+ years of options data

## Installation

### Prerequisites
```bash
pip install -r requirements.txt
```

### Required Dependencies
- pandas >= 2.0.0
- numpy >= 1.24.0
- pyarrow >= 12.0.0
- matplotlib >= 3.7.0
- seaborn >= 0.12.0
- scipy (for risk calculations)

## Quick Start

### Basic Long Call Strategy
```bash
python backtester.py \
    --strategy long_call \
    --start-date 20220101 \
    --end-date 20221231 \
    --delta-threshold 0.30 \
    --initial-capital 100000
```

### Long Straddle Strategy
```bash
python backtester.py \
    --strategy straddle \
    --start-date 20210101 \
    --end-date 20211231 \
    --delta-threshold 0.50 \
    --stop-loss 0.50 \
    --profit-target 1.00
```

### Covered Call Strategy
```bash
python backtester.py \
    --strategy covered_call \
    --start-date 20220101 \
    --end-date 20221231 \
    --delta-threshold 0.30 \
    --min-dte 20 \
    --max-dte 45
```

## Available Strategies

### 1. Long Call (`long_call`)
- **Description**: Buy call options with specified delta
- **Parameters**: 
  - `delta_threshold`: Target delta for entry (default: 0.30)
  - `entry_frequency`: Days between entries (default: 5)

### 2. Long Put (`long_put`)
- **Description**: Buy put options with specified delta
- **Parameters**:
  - `delta_threshold`: Target delta for entry (default: -0.30)
  - `entry_frequency`: Days between entries (default: 5)

### 3. Long Straddle (`straddle`)
- **Description**: Buy call and put at same strike (volatility play)
- **Parameters**:
  - `delta_threshold`: Target delta (ATM = 0.50)
  - `max_straddles`: Maximum concurrent straddles (default: 2)

### 4. Covered Call (`covered_call`)
- **Description**: Sell OTM calls (assumes stock ownership)
- **Parameters**:
  - `shares_owned`: Number of shares owned (default: 100)
  - `delta_threshold`: Target delta for short calls (default: 0.30)

## Command Line Arguments

### Required
- `--strategy`: Strategy to backtest (long_call, long_put, straddle, covered_call)
- `--start-date`: Start date in YYYYMMDD format
- `--end-date`: End date in YYYYMMDD format

### Optional
- `--initial-capital`: Starting capital (default: $100,000)
- `--delta-threshold`: Delta threshold for entry (default: 0.30)
- `--min-dte`: Minimum days to expiration (default: 10)
- `--max-dte`: Maximum days to expiration (default: 60)
- `--stop-loss`: Stop loss percentage (default: 0.50 = 50%)
- `--profit-target`: Profit target percentage (default: 1.00 = 100%)
- `--position-size`: Max position size as fraction of capital (default: 0.05 = 5%)
- `--output`: Output directory for results and reports

## Data Requirements

The backtester expects SPY options data in parquet format with the following columns:
- `date`: Trading date
- `expiration`: Option expiration date
- `strike`: Strike price (in dollars)
- `right`: Option type ('C' for call, 'P' for put)
- `bid`, `ask`: Bid/ask prices
- `volume`: Trading volume
- `delta`, `gamma`, `theta`, `vega`, `rho`: Greeks
- `implied_vol`: Implied volatility
- `underlying_price`: SPY price

## Output

### Console Output
- Real-time backtest progress
- Trade execution details
- Final performance summary

### File Outputs (when `--output` specified)
- `trades.csv`: Detailed trade log
- `portfolio.csv`: Daily portfolio snapshots
- `backtest_report.html`: Comprehensive HTML report with charts
- `summary.json`: Machine-readable performance summary

## Performance Metrics

### Return Metrics
- Total Return
- Annualized Return
- Sharpe Ratio
- Maximum Drawdown
- Volatility

### Trade Metrics
- Total Trades
- Win Rate
- Average Win/Loss
- Profit Factor
- Largest Win/Loss

### Risk Metrics
- Value at Risk (VaR)
- Portfolio Greeks exposure
- Position concentration
- Days to expiration analysis

## Examples

### Compare Multiple Strategies
```bash
# Long calls
python backtester.py --strategy long_call --start-date 20220101 --end-date 20221231 --output results/long_calls

# Long puts  
python backtester.py --strategy long_put --start-date 20220101 --end-date 20221231 --output results/long_puts

# Straddles
python backtester.py --strategy straddle --start-date 20220101 --end-date 20221231 --output results/straddles
```

### Parameter Sensitivity Analysis
```bash
# Test different delta thresholds
for delta in 0.20 0.30 0.40; do
    python backtester.py \
        --strategy long_call \
        --start-date 20220101 \
        --end-date 20221231 \
        --delta-threshold $delta \
        --output results/delta_$delta
done
```

### Different Time Periods
```bash
# 2020 (COVID volatility)
python backtester.py --strategy straddle --start-date 20200301 --end-date 20201231

# 2021 (Bull market)
python backtester.py --strategy long_call --start-date 20210101 --end-date 20211231

# 2022 (Bear market)
python backtester.py --strategy long_put --start-date 20220101 --end-date 20221231
```

## Advanced Usage

### Test Data Loader
```bash
python data_loader.py  # Test data loading functionality
```

### Custom Strategy Development
1. Create new strategy class inheriting from `SimpleStrategy`
2. Implement `generate_signals()` method
3. Add to strategy factory in `backtester.py`

### Risk Analysis
The backtester includes comprehensive risk management:
- Position size limits
- Portfolio delta exposure limits
- Value at Risk calculations
- Concentration risk monitoring

## Performance Tips

1. **Data Caching**: The data loader caches frequently accessed files
2. **Date Filtering**: Use narrow date ranges for faster testing
3. **Memory Management**: Clear cache for very long backtests
4. **Parallel Processing**: The framework supports concurrent strategy execution

## Troubleshooting

### Common Issues

**"No data file found for date"**
- Ensure parquet files are in the correct directory
- Check date format (YYYYMMDD)
- Verify data files exist for the specified period

**"Could not find option for signal"**
- Option may not exist for specified criteria
- Try wider delta thresholds or DTE ranges
- Check data quality for that date

**Memory issues with long backtests**
- Use data loader's `clear_cache()` method
- Process shorter date ranges
- Reduce concurrent positions

### Performance Optimization
- Use SSD storage for parquet files
- Increase system RAM for large datasets  
- Consider data preprocessing for frequently accessed ranges

## File Structure
```
spy_backtester/
├── backtester.py              # Main CLI interface
├── config.py                  # Configuration settings
├── data_loader.py             # Data loading utilities
├── strategy_base.py           # Base strategy classes
├── portfolio_manager.py       # Portfolio tracking
├── risk_manager.py           # Risk management
├── reporter.py               # Performance reporting
├── strategies/
│   ├── simple_strategies.py  # Basic strategy implementations
│   └── __init__.py
├── results/                  # Generated reports (created automatically)
├── requirements.txt          # Dependencies
└── README.md                # This file
```

## Contributing

To add new strategies:
1. Create strategy class in `strategies/` directory
2. Inherit from `SimpleStrategy` or `StrategyBase`
3. Implement required methods
4. Add to strategy factory in `backtester.py`
5. Update documentation

## Disclaimer

This backtester is for educational and research purposes only. Past performance does not guarantee future results. Options trading involves substantial risk and is not suitable for all investors.