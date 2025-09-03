# Backtest Usage Guide

A step-by-step guide for running options backtests using the Daily OptionsLab system.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Running Your First Backtest](#running-your-first-backtest)
3. [Understanding Strategy Configuration](#understanding-strategy-configuration)
4. [Market Regime Filtering](#market-regime-filtering)
5. [Comprehensive Analysis](#comprehensive-analysis)
6. [Interpreting Results](#interpreting-results)
7. [Common Workflows](#common-workflows)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites
```bash
cd /Users/nish_macbook/trading/daily-optionslab
source venv/bin/activate
```

### Simplest Backtest
```python
from backtests.backtest_manager import BacktestManager

manager = BacktestManager()
results = manager.run_backtest(
    config_file='config/long_call_simple.yaml',
    start_date='2024-01-01',
    end_date='2024-12-31'
)

print(f"Return: {results['metrics']['total_return']:.2%}")
print(f"Sharpe: {results['metrics']['sharpe_ratio']:.2f}")
```

## Running Your First Backtest

### Step 1: Choose a Strategy Configuration

Available strategies in `config/`:
- `long_call_simple.yaml` - Basic long call strategy
- `long_call_regime_filtered.yaml` - Long calls with volatility filtering
- `pmcc_strategy.yaml` - Poor Man's Covered Call

### Step 2: Select Date Range

We have data from July 2020 to July 2025. Key periods:
- **Bull Market**: 2021-01-01 to 2021-12-31
- **Bear Market**: 2022-01-01 to 2022-12-31
- **Recovery**: 2023-01-01 to 2023-12-31
- **Recent**: 2024-01-01 to 2025-07-11

### Step 3: Run the Backtest

```python
from optionslab.backtest_engine import run_auditable_backtest

# Basic backtest
results = run_auditable_backtest(
    data_file='data/spy_options/',
    config_file='config/long_call_simple.yaml',
    start_date='2023-01-01',
    end_date='2024-12-31',
    initial_capital=10000
)

# Access results
audit_log = results['audit_log']
metrics = audit_log['metrics']
trades = audit_log['trades']

print(f"Total Trades: {len(trades)}")
print(f"Win Rate: {metrics['win_rate']:.1%}")
print(f"Total Return: {metrics['total_return']:.2%}")
```

## Understanding Strategy Configuration

### Basic Configuration Structure

```yaml
name: "Long Call Strategy"
strategy_type: "long_call"
description: "Buy ATM calls 30-45 DTE"

parameters:
  initial_capital: 10000
  commission_per_contract: 0.65
  max_hold_days: 45
  position_size: 0.05  # 5% of capital per trade

option_selection:
  delta_criteria:
    target: 0.50      # ATM
    tolerance: 0.10   # Accept 0.40-0.60 delta
    minimum: 0.40
    maximum: 0.60
    
  dte_criteria:
    target: 35
    minimum: 30
    maximum: 45
    
  liquidity_criteria:
    min_volume: 100
    max_spread_pct: 0.10  # 10% max bid-ask spread

exit_rules:
  - condition: "profit_target"
    threshold: 50.0  # Exit at 50% profit
  - condition: "stop_loss"
    threshold: -30.0  # Exit at 30% loss
  - condition: "time_stop"
    dte_threshold: 7  # Exit with 7 days to expiration
```

### Key Parameters Explained

- **position_size**: Percentage of capital for each trade
- **delta_criteria**: Controls option moneyness selection
- **dte_criteria**: Days to expiration requirements
- **liquidity_criteria**: Ensures tradeable options
- **exit_rules**: Multiple conditions checked daily

## Market Regime Filtering

### Enable Volatility-Based Filtering

```yaml
# In your strategy config
market_filters:
  enabled: true
  
  volatility_regime:
    method: "ewma"           # 20-day EWMA volatility
    max_volatility: 25       # Don't enter above 25% vol
    min_volatility: 10       # Don't enter below 10% vol
    
  trend_filter:
    enabled: true
    sma_period: 50           # 50-day SMA
    require_uptrend: true    # Only trade in uptrends
```

### Understanding Volatility Regimes

The system classifies market conditions:
- **Low Vol (<15%)**: Calm markets, trends persist
- **Normal (15-25%)**: Typical conditions
- **High Vol (>25%)**: Stressed markets, higher premiums

### Example: Regime-Filtered Strategy

```python
# Compare with and without regime filtering
configs = [
    'config/long_call_simple.yaml',
    'config/long_call_regime_filtered.yaml'
]

for config in configs:
    results = manager.run_backtest(config, '2022-01-01', '2022-12-31')
    print(f"{config}: Return = {results['metrics']['total_return']:.2%}")

# Regime-filtered typically performs better in bear markets
```

## Comprehensive Analysis

### Run Across All Market Conditions

```python
from backtests.run_comprehensive_analysis import run_comprehensive_backtest

# Automatically tests across all mandatory periods
results = run_comprehensive_backtest(
    config_file='config/long_call_regime_filtered.yaml',
    initial_capital=10000
)

# Results include performance for:
# - Full 5-year dataset
# - 2022 bear market
# - 2023 recovery
# - 2024 stability
# - 2025 volatility

for period, metrics in results.items():
    print(f"{period}: {metrics['total_return']:.2%} return, {metrics['sharpe']:.2f} Sharpe")
```

### Analyze Market Regimes

```python
from backtests.market_regime_analyzer import MarketRegimeAnalyzer

analyzer = MarketRegimeAnalyzer()
regime_analysis = analyzer.analyze_full_history()

# See which regimes your strategy performed best in
regime_performance = analyzer.analyze_strategy_by_regime(
    'config/long_call_simple.yaml'
)

print("Performance by Volatility Regime:")
for regime, stats in regime_performance.items():
    print(f"{regime}: {stats['avg_return']:.2%} avg return")
```

## Interpreting Results

### Key Metrics to Review

1. **Total Return**: Overall profitability
2. **Sharpe Ratio**: Risk-adjusted returns (>1.0 is good)
3. **Max Drawdown**: Worst peak-to-trough loss
4. **Win Rate**: Percentage of profitable trades
5. **Profit Factor**: Gross profits / Gross losses

### Reading the Audit Log

```python
# Access detailed trade information
audit_log = results['audit_log']

# Review individual trades
for trade in audit_log['trades'][:5]:  # First 5 trades
    print(f"Entry: {trade['entry_date']}, "
          f"Strike: ${trade['strike']}, "
          f"P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.1%})")
    print(f"  Entry Reason: {trade['entry_reasoning']}")
    print(f"  Exit Reason: {trade['exit_reason']}")
```

### Visualizing Results

```python
# Launch Gradio UI to view charts
import subprocess
subprocess.Popen(['python', 'backtests/gradio_results_viewer.py'])

# Or generate charts programmatically
from optionslab.visualization import create_backtest_charts
charts = create_backtest_charts(
    equity_curve=results['equity_curve'],
    trades=results['trades']
)
charts['equity_curve'].show()  # Display equity curve
```

## Common Workflows

### Workflow 1: Strategy Development

```python
# 1. Start with small date range for quick iteration
test_results = manager.run_backtest(
    'config/my_strategy.yaml',
    '2024-01-01', '2024-03-31'  # Q1 only
)

# 2. If promising, expand to full year
if test_results['metrics']['sharpe_ratio'] > 1.0:
    year_results = manager.run_backtest(
        'config/my_strategy.yaml',
        '2024-01-01', '2024-12-31'
    )

# 3. Finally, run comprehensive analysis
if year_results['metrics']['sharpe_ratio'] > 1.0:
    full_results = run_comprehensive_backtest('config/my_strategy.yaml')
```

### Workflow 2: Parameter Optimization

```python
# Test different delta targets
delta_targets = [0.30, 0.40, 0.50]
results_by_delta = {}

for delta in delta_targets:
    # Modify config
    config = load_strategy_config('config/long_call_simple.yaml')
    config['option_selection']['delta_criteria']['target'] = delta
    
    # Run backtest
    results = run_backtest_with_config(config, '2024-01-01', '2024-12-31')
    results_by_delta[delta] = results['metrics']['total_return']

# Find optimal delta
best_delta = max(results_by_delta, key=results_by_delta.get)
print(f"Best delta: {best_delta} with {results_by_delta[best_delta]:.2%} return")
```

### Workflow 3: Strategy Comparison

```python
# Compare multiple strategies
strategies = {
    'Long Call': 'config/long_call_simple.yaml',
    'Filtered Call': 'config/long_call_regime_filtered.yaml',
    'PMCC': 'config/pmcc_strategy.yaml'
}

comparison = {}
for name, config in strategies.items():
    results = manager.run_backtest(config, '2023-01-01', '2024-12-31')
    comparison[name] = {
        'return': results['metrics']['total_return'],
        'sharpe': results['metrics']['sharpe_ratio'],
        'max_dd': results['metrics']['max_drawdown']
    }

# Display comparison
import pandas as pd
df = pd.DataFrame(comparison).T
print(df.round(2))
```

## Troubleshooting

### Common Issues and Solutions

#### "No suitable options found"
- **Cause**: Filters too restrictive
- **Solution**: Widen delta tolerance or reduce liquidity requirements
```yaml
delta_criteria:
  tolerance: 0.15  # Increase from 0.10
liquidity_criteria:
  min_volume: 50   # Reduce from 100
```

#### "FileNotFoundError for data"
- **Cause**: Missing data files for date range
- **Solution**: Check available dates
```python
import os
files = os.listdir('data/spy_options')
dates = sorted([f.split('_')[-1].split('.')[0] for f in files])
print(f"Data available: {dates[0]} to {dates[-1]}")
```

#### "Zero trades executed"
- **Cause**: Market filters preventing entry
- **Solution**: Check filter conditions
```python
# Debug market conditions
from backtests.market_regime_analyzer import MarketRegimeAnalyzer
analyzer = MarketRegimeAnalyzer()
regime = analyzer.get_regime_for_date('2024-01-15')
print(f"Market regime: {regime}")
```

#### Low Sharpe Ratio
- **Cause**: High volatility or poor timing
- **Solution**: Add regime filtering or adjust position sizing
```yaml
parameters:
  position_size: 0.03  # Reduce from 0.05
market_filters:
  enabled: true        # Enable filtering
```

### Performance Tips

1. **Start Simple**: Use `long_call_simple.yaml` as baseline
2. **Test Incrementally**: Start with recent data, expand if successful
3. **Compare to Buy-Hold**: Always benchmark against SPY
4. **Document Changes**: Track what parameters you modify
5. **Use Comprehensive Analysis**: Test across all market conditions

## Next Steps

1. **Explore Advanced Features**:
   - Greeks-based exits (see SYSTEM_CAPABILITIES.md)
   - Multi-leg strategies (iron condors, strangles)
   - Custom exit conditions

2. **Create Custom Strategies**:
   - Copy existing YAML as template
   - Modify parameters incrementally
   - Test across different periods

3. **Analyze Results**:
   - Use notebooks in `backtests/notebooks/templates/`
   - Generate custom visualizations
   - Export to Excel for further analysis

## Additional Resources

- [BACKTESTING_CHECKLIST.md](./BACKTESTING_CHECKLIST.md) - Golden rules for accurate backtests
- [backtests/README.md](./backtests/README.md) - Centralized system documentation
- [SYSTEM_CAPABILITIES.md](./SYSTEM_CAPABILITIES.md) - Advanced features
- [DATA_MANAGEMENT.md](./DATA_MANAGEMENT.md) - Data handling details