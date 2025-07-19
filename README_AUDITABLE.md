# 🎯 OptionsLab - Auditable Backtesting System

**Trustworthy, traceable options backtesting with full data flow auditing.**

This system provides complete transparency in options trading simulation, giving you confidence in every calculation and result.

## 🚀 Quick Start

### 1. Start the System
```bash
./start_auditable.sh
```

### 2. Open Your Browser
Navigate to: http://localhost:7860

### 3. Run Your First Backtest
1. Select a data file (parquet file with real SPY options data)
2. Choose a strategy (YAML configuration)
3. Set your dates and initial capital
4. Click "Run Auditable Backtest"
5. Review the full audit log

## 🔍 What Makes This System Trustworthy

### ✅ **Real Market Data**
- Uses actual SPY options data from parquet files
- No synthetic or simulated data
- Real prices, Greeks, and implied volatility

### ✅ **Full Traceability**
- Every calculation is logged and visible
- Option selection process is transparent
- Position sizing is auditable
- P&L calculations are verifiable

### ✅ **Strategy Transparency**
- YAML-based strategy definitions
- Clear entry and exit rules
- Risk management parameters
- No hidden logic or black boxes

### ✅ **Verifiable Results**
- Complete audit trail for every trade
- Step-by-step execution log
- Performance metrics with full context
- Error handling with detailed explanations

## 📁 System Architecture

```
thetadata-api/
├── auditable_gradio_app.py      # Main Gradio interface
├── auditable_backtest.py        # Auditable backtest engine
├── simple_test_strategy.yaml    # Example strategy
├── start_auditable.sh          # Startup script
├── spy_options_downloader/     # Real market data
│   └── spy_options_parquet/
│       ├── repaired/           # Working data files
│       └── *.parquet          # Raw data files
└── config/strategies/          # Strategy configurations
```

## 📊 Data Flow

1. **Data Loading**: Real SPY options data from parquet files
2. **Strategy Loading**: YAML configuration with clear parameters
3. **Option Selection**: Transparent filtering and selection process
4. **Position Sizing**: Auditable risk management calculations
5. **Trade Execution**: Logged entry and exit decisions
6. **P&L Calculation**: Verifiable profit/loss calculations
7. **Results Display**: Complete audit trail with performance metrics

## 🎯 Example Strategy

The system includes a simple long call strategy for testing:

```yaml
name: "Simple Long Call Test"
description: "Basic long call strategy for data flow auditing"
strategy_type: "long_call"
parameters:
  initial_capital: 10000
  position_size: 0.1  # 10% of capital per trade
  max_hold_days: 5
  entry_frequency: 3  # Every 3 days
```

## 🔧 Configuration

### Data Files
- **Location**: `spy_options_downloader/spy_options_parquet/`
- **Format**: Parquet files with real SPY options data
- **Priority**: Repaired files are used first (more reliable)

### Strategy Files
- **Location**: `config/strategies/` and root directory
- **Format**: YAML configuration files
- **Structure**: Clear parameters for entry, exit, and risk management

## 📈 Understanding Results

### Audit Log Components
1. **Data Validation**: File loading and data quality checks
2. **Strategy Configuration**: Parameter loading and validation
3. **Option Selection**: Strike and expiration selection process
4. **Position Sizing**: Risk calculation and contract sizing
5. **Trade Execution**: Entry and exit timing
6. **P&L Tracking**: Profit/loss calculation for each trade
7. **Performance Metrics**: Final statistics and analysis

### Key Metrics
- **Final Value**: Total portfolio value at end of period
- **Total Return**: Percentage gain/loss from initial capital
- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted return measure
- **Max Drawdown**: Largest peak-to-trough decline

## 🛠️ Troubleshooting

### Common Issues

**No data files found**
- Check that parquet files exist in `spy_options_downloader/spy_options_parquet/`
- Ensure files are not corrupted

**No strategies available**
- Verify YAML files exist in `config/strategies/`
- Check YAML syntax is valid

**Backtest fails**
- Review the audit log for specific error messages
- Check date ranges are valid
- Ensure sufficient capital for position sizing

### Getting Help

1. **Check the audit log** - it contains detailed error information
2. **Verify file paths** - ensure all required files exist
3. **Review strategy configuration** - check YAML syntax
4. **Test with simple parameters** - start with single-day backtests

## 🔮 Future Enhancements

- **Multiple Strategy Support**: Run multiple strategies simultaneously
- **Advanced Analytics**: More sophisticated performance metrics
- **Risk Management**: Additional risk controls and position limits
- **Data Visualization**: Charts and graphs for results
- **Strategy Builder**: Visual strategy creation interface

## 📚 Technical Details

### Dependencies
- Python 3.8+
- Gradio (for web interface)
- Pandas (for data handling)
- PyYAML (for strategy configuration)
- NumPy (for calculations)

### File Formats
- **Data**: Parquet files with SPY options data
- **Strategies**: YAML configuration files
- **Results**: Markdown-formatted audit logs

### Performance
- **Data Loading**: Optimized for large parquet files
- **Backtest Speed**: Real-time execution with full logging
- **Memory Usage**: Efficient data handling for large datasets

## 🤝 Contributing

This system is designed to be:
- **Transparent**: All code is visible and auditable
- **Extensible**: Easy to add new strategies and features
- **Reliable**: Thorough error handling and validation
- **Educational**: Clear documentation and examples

## 📄 License

This project is for educational and research purposes. Use at your own risk for actual trading decisions.

---

**Remember**: This system provides transparency and auditability, but all trading involves risk. Always verify results and understand the underlying calculations before making any trading decisions. 