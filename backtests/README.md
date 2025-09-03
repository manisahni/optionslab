# Centralized Backtest Management System

## Overview

The centralized backtest management system provides a unified framework for running, storing, analyzing, and visualizing options backtests across different market conditions. This system integrates seamlessly with both Jupyter notebooks and the Gradio web interface.

## Key Features

- **Automated Storage**: Backtests are automatically organized by year, strategy type, and timestamp
- **Market Regime Detection**: Built-in EWMA volatility analysis for regime-aware backtesting
- **Comprehensive Analysis**: Test strategies across mandatory market periods (bear markets, volatility spikes)
- **Result Indexing**: Automatic indexing and search capabilities for all backtest results
- **Dual Interface**: Access results via notebooks or Gradio UI
- **Full Audit Trail**: Complete trade-by-trade documentation with entry/exit reasoning

## Directory Structure

```
backtests/
├── results/                    # All backtest results stored here
│   ├── YYYY/                  # Organized by year
│   │   └── strategy_type/     # By strategy (long_call, short_put, etc.)
│   │       └── timestamp/     # Unique timestamp for each run
│   │           ├── audit_log.json      # Complete trade details
│   │           ├── config.yaml         # Strategy configuration used
│   │           ├── performance.json    # Metrics and statistics
│   │           ├── equity_curve.html   # Interactive chart
│   │           └── trades.csv          # Trade log for analysis
│   └── index.json             # Master index of all backtests
│
├── backtest_manager.py        # Core management module
├── market_regime_analyzer.py  # Market condition detection
├── run_comprehensive_analysis.py # Run across all periods
├── gradio_results_viewer.py   # Web UI for viewing results
└── notebooks/
    └── templates/
        └── backtest_analysis.py # Analysis template
```

## Usage Examples

### 1. Run a Simple Backtest

```python
from backtests.backtest_manager import BacktestManager

manager = BacktestManager()

# Run a single backtest
results = manager.run_backtest(
    config_file='config/long_call_simple.yaml',
    start_date='2023-01-01',
    end_date='2024-12-31',
    initial_capital=10000
)

print(f"Results saved to: {results['result_dir']}")
print(f"Total Return: {results['metrics']['total_return']:.2%}")
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
```

### 2. Run Comprehensive Analysis

```python
from backtests.run_comprehensive_analysis import run_comprehensive_backtest

# Test across all mandatory periods
results = run_comprehensive_backtest(
    config_file='config/long_call_regime_filtered.yaml',
    initial_capital=10000
)

# Results include:
# - Full dataset (2020-2025)
# - 2022 bear market
# - 2023 recovery
# - 2024 stability
# - 2025 rate volatility
```

### 3. Analyze Market Regimes

```python
from backtests.market_regime_analyzer import MarketRegimeAnalyzer

analyzer = MarketRegimeAnalyzer()
analysis = analyzer.analyze_full_history()

# Get regime breakdown
print(f"Low Volatility Days: {analysis['regime_stats']['low_vol_pct']:.1f}%")
print(f"Normal Days: {analysis['regime_stats']['normal_vol_pct']:.1f}%")
print(f"High Volatility Days: {analysis['regime_stats']['high_vol_pct']:.1f}%")

# Major drawdowns identified
for dd in analysis['major_drawdowns']:
    print(f"{dd['start']} to {dd['end']}: {dd['magnitude']:.1f}% drawdown")
```

### 4. View Results in Gradio UI

```python
# Launch the results viewer
python backtests/gradio_results_viewer.py

# Or integrate into existing app
from backtests.gradio_results_viewer import create_backtest_viewer
viewer = create_backtest_viewer()
viewer.launch(server_port=7863)
```

### 5. Search and Compare Results

```python
from backtests.backtest_manager import BacktestManager

manager = BacktestManager()

# Search for specific backtests
results = manager.search_backtests(
    strategy_type='long_call',
    min_sharpe=1.0,
    year=2024
)

# Compare multiple strategies
comparison = manager.compare_strategies(
    strategies=['long_call', 'short_put'],
    period='2024-01-01 to 2024-12-31'
)
```

## Market Regime Detection

The system uses EWMA (Exponentially Weighted Moving Average) volatility for regime detection:

- **Low Volatility**: < 15% annualized (calm markets)
- **Normal Volatility**: 15-25% annualized (typical conditions)
- **High Volatility**: > 25% annualized (stressed markets)

### Regime Filtering in Strategies

```yaml
# config/long_call_regime_filtered.yaml
market_filters:
  enabled: true
  volatility_regime:
    method: "ewma"  # Uses 20-day EWMA
    max_volatility: 25  # Skip entry above 25% vol
    min_volatility: 10   # Skip entry below 10% vol
```

## Mandatory Testing Periods

All comprehensive backtests MUST include these periods:

1. **Full Dataset** (2020-07-15 to 2025-07-11)
   - Complete 5-year performance baseline
   
2. **2022 Bear Market** (2022-01-01 to 2022-12-31)
   - Tests strategy during -25.4% drawdown
   - High volatility regime dominant
   
3. **2023 Recovery** (2023-01-01 to 2023-12-31)
   - Post-bear market recovery dynamics
   
4. **2024 Stability** (2024-01-01 to 2024-12-31)
   - Low volatility trending market
   
5. **2025 Rate/Tariff Volatility** (2025-01-01 to 2025-07-11)
   - Interest rate and tariff uncertainty

## Integration with Notebooks

Use the provided template for consistent analysis:

```python
# Copy template for new analysis
import shutil
shutil.copy(
    'backtests/notebooks/templates/backtest_analysis.py',
    'backtests/notebooks/my_strategy_analysis.py'
)

# Template includes:
# - Automatic result loading
# - Performance comparison charts
# - Regime analysis
# - Trade-by-trade review
```

## Performance Metrics

Each backtest automatically calculates:

- **Returns**: Total, annualized (CAGR), monthly, daily
- **Risk**: Sharpe ratio, Sortino ratio, maximum drawdown
- **Trading**: Win rate, profit factor, average win/loss
- **Implementation**: Slippage impact, commission drag
- **Greeks**: Delta/gamma/theta/vega attribution (if tracked)

## Best Practices

1. **Always run comprehensive analysis** for new strategies
2. **Document parameter choices** in config files
3. **Review audit logs** to verify trade logic
4. **Compare against SPY baseline** for context
5. **Test across different volatility regimes**
6. **Store all results** for future comparison

## Troubleshooting

### No results appearing in UI
- Check that backtests/results/ directory exists
- Verify index.json is being updated
- Ensure proper permissions on result directories

### Backtest fails to complete
- Check data availability for requested dates
- Verify strategy config YAML syntax
- Review logs for specific error messages

### Market regime not detected
- Ensure SPY price data is available
- Check that EWMA calculation has sufficient history (20+ days)

## Advanced Features

### Custom Period Analysis

```python
# Define custom test periods
custom_periods = [
    {"name": "COVID Crash", "start": "2020-02-01", "end": "2020-04-30"},
    {"name": "Meme Stock Mania", "start": "2021-01-01", "end": "2021-03-31"},
    {"name": "Fed Pivot", "start": "2023-10-01", "end": "2024-01-31"}
]

results = manager.run_period_analysis(
    config_file='config/my_strategy.yaml',
    periods=custom_periods
)
```

### Batch Strategy Testing

```python
# Test multiple strategies at once
strategies = [
    'config/long_call_simple.yaml',
    'config/long_call_regime_filtered.yaml',
    'config/short_put_weekly.yaml'
]

for strategy in strategies:
    manager.run_comprehensive_backtest(strategy)
    
# Generate comparison report
manager.generate_comparison_report(strategies)
```

## Further Documentation

- **[BACKTESTING_CHECKLIST.md](../BACKTESTING_CHECKLIST.md)** - Golden rules for accurate backtests
- **[DATA_MANAGEMENT.md](../DATA_MANAGEMENT.md)** - Data handling and quality checks
- **[SYSTEM_CAPABILITIES.md](../SYSTEM_CAPABILITIES.md)** - Advanced features and validation