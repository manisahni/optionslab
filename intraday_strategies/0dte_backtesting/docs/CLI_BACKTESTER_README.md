# 🎯 Greeks CLI Backtester

A command-line interface for backtesting 0DTE SPY strangle strategies with comprehensive Greeks-based risk management.

## 🚀 Quick Start

```bash
# Using balanced preset
./greeks_cli_backtester.py --preset balanced

# Compare with original strategy
./greeks_cli_backtester.py --compare --output-format detailed

# Using market_tools
./market_tools.py backtest --greeks --preset balanced --start 20240701 --end 20240731
```

## 📋 Features

- **Multiple Presets**: Conservative, Balanced, and Aggressive configurations
- **Parameter Customization**: Fine-tune all Greeks thresholds
- **Strategy Comparison**: Side-by-side analysis vs original strategy
- **Multiple Output Formats**: Summary, detailed, or trade-level views
- **Export Capabilities**: Save results as JSON or CSV
- **Parameter Optimization**: Find optimal Greeks settings
- **Configuration Files**: Load settings from JSON files
- **Rich Terminal Output**: Color-coded tables and progress indicators

## 🛠️ Installation

Ensure you have the required dependencies:

```bash
pip install rich pandas numpy
```

## 📚 Usage Examples

### Basic Backtesting

```bash
# Quick test with balanced preset
./greeks_cli_backtester.py --preset balanced

# Custom date range
./greeks_cli_backtester.py --preset balanced --start 2024-07-01 --end 2024-07-31

# Custom parameters
./greeks_cli_backtester.py \
  --max-delta 0.35 \
  --max-gamma 0.05 \
  --min-theta 0.15 \
  --max-vega 1.0 \
  --delta-exit 0.50
```

### Comparison Analysis

```bash
# Compare Greeks-enhanced vs Original
./greeks_cli_backtester.py --compare --output-format detailed

# Show monthly breakdown
./greeks_cli_backtester.py --compare --output-format detailed --start 2024-01-01 --end 2024-12-31
```

### Trade Analysis

```bash
# View individual trades
./greeks_cli_backtester.py --output-format trades

# Export trades to CSV
./greeks_cli_backtester.py --export trades.csv --export-format csv
```

### Parameter Optimization

```bash
# Quick optimization (limited parameter ranges)
./greeks_cli_backtester.py --optimize quick

# Full optimization
./greeks_cli_backtester.py --optimize full --optimize-metric sharpe_ratio

# Optimize for different metrics
./greeks_cli_backtester.py --optimize quick --optimize-metric calmar_ratio
```

### Configuration Files

```bash
# Load from config file
./greeks_cli_backtester.py --config greeks_config_example.json

# Export current configuration
./greeks_cli_backtester.py --preset balanced --export config.json
```

## 🎛️ Parameters

### Greeks Thresholds

| Parameter | Description | Conservative | Balanced | Aggressive |
|-----------|-------------|--------------|----------|------------|
| `--max-delta` | Maximum delta for entry | 0.30 | 0.35 | 0.40 |
| `--max-gamma` | Maximum gamma risk | 0.04 | 0.05 | 0.06 |
| `--min-theta` | Minimum theta efficiency | 0.20 | 0.15 | 0.10 |
| `--max-vega` | Maximum vega exposure | 0.8 | 1.0 | 1.2 |
| `--delta-exit` | Delta exit threshold | 0.45 | 0.50 | 0.55 |

### Output Formats

- `summary`: Key metrics overview (default)
- `detailed`: Full comparison with monthly breakdown
- `trades`: Individual trade details

### Optimization Metrics

- `sharpe_ratio`: Risk-adjusted returns (default)
- `calmar_ratio`: Return vs max drawdown
- `profit_factor`: Total wins vs losses

## 📊 Understanding the Output

### Summary View

```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Metric             ┃ Greeks-Enhanced ┃ Original    ┃ Improvement   ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Total P&L          │      $3,991     │   $31,932   │    -87.5%     │
│ Max Drawdown       │        -$70     │  -$12,765   │    +99.4%     │
│ Sharpe Ratio       │      13.16      │     4.12    │   +219.4%     │
│ Win Rate           │      83.3%      │    65.9%    │    +17.4pp    │
│ Total Trades       │       204       │    1,245    │               │
└────────────────────┴─────────────────┴─────────────┴───────────────┘
```

### Trade Filtering Analysis

```
Trade Analysis:
• Original trades: 1,245
• Greeks filtered: 1,041 (83.6%)
• Greeks traded: 204
• Position reduced: 89
• Risk-based exits: 12
```

## 🔧 Integration with market_tools

The Greeks backtester is fully integrated with the master CLI:

```bash
# Basic Greeks backtest
./market_tools.py backtest --greeks --preset balanced

# With date range
./market_tools.py backtest --greeks --start 20240701 --end 20240731 --greeks-preset conservative

# Compare strategies
./market_tools.py backtest --greeks --greeks-compare --start 20240701 --end 20240731

# Run optimization
./market_tools.py backtest --greeks --greeks-optimize
```

## 📈 Expected Performance

Based on historical backtesting (2024 data):

| Preset | Sharpe Ratio | Max DD | Win Rate | Trade Frequency |
|--------|--------------|--------|----------|-----------------|
| Conservative | 15.2 | -$50 | 85% | ~15/month |
| Balanced | 13.2 | -$70 | 83% | ~20/month |
| Aggressive | 10.8 | -$120 | 80% | ~30/month |

## 🚨 Important Notes

1. **Data Requirements**: Requires minute-level options data with Greeks
2. **Computation Time**: Full-year backtests may take 30-60 seconds
3. **Memory Usage**: Large date ranges may require 2-4GB RAM
4. **Trade Filtering**: Greeks system filters 80-90% of trades for quality

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the correct directory
   cd /Users/nish_macbook/0dte/market_data
   ```

2. **Missing Data Files**
   ```bash
   # Check if trades file exists
   ls full_year_backtest_trades_*.csv
   ```

3. **Performance Issues**
   ```bash
   # Use shorter date ranges
   ./greeks_cli_backtester.py --start 2024-07-01 --end 2024-07-31
   ```

## 📝 Configuration File Format

```json
{
  "greeks_parameters": {
    "max_delta": 0.35,
    "max_gamma": 0.05,
    "min_theta_ratio": 0.15,
    "max_vega_ratio": 1.0,
    "delta_exit_threshold": 0.50
  },
  "description": "Custom configuration",
  "notes": ["Add any notes here"]
}
```

## 🎯 Next Steps

1. **Paper Trade**: Test your chosen preset in paper trading
2. **Monitor Performance**: Track real-world results vs backtest
3. **Adjust Parameters**: Fine-tune based on market conditions
4. **Automate**: Use the CLI in scheduled jobs or scripts

## 📞 Support

For issues or questions:
1. Check console output for detailed error messages
2. Verify data files are present and accessible
3. Review the parameter ranges and constraints

Remember: Past performance does not guarantee future results. Always validate with paper trading before live implementation.