# Backtest Debugger Tool

## Overview

The `debug_backtest.py` script is a diagnostic tool designed to help debug and troubleshoot backtest runs in the ThetaData API project. It captures all output, errors, and execution details to help identify issues during backtest development.

## Features

- **Comprehensive Error Capture**: Captures both stdout and stderr from backtest runs
- **Timestamped Logging**: Creates detailed log files with timestamps for each run
- **Virtual Environment Support**: Automatically detects and uses project virtual environment
- **Loop Mode**: Option to continuously retry failed backtests until successful
- **Colored Output**: Clear visual feedback with emoji indicators for success/failure
- **Detailed Trade Logging**: Shows individual trade entries, exits, and P&L

## Usage

### Basic Usage

Run a single backtest with a strategy configuration file:

```bash
./debug_backtest.py config/strategies/simple_long_call.yaml
```

### Loop Mode

Keep retrying a backtest until it succeeds (useful for debugging intermittent issues):

```bash
./debug_backtest.py config/strategies/simple_long_call.yaml --loop
```

Press `Ctrl+C` to stop the loop.

## Output

### Console Output

The script provides immediate feedback in the console:

```
🔍 Starting backtest debug for: config/strategies/simple_long_call.yaml
📝 Log file: debug_logs/backtest_debug_20250718_235339.log
--------------------------------------------------
✅ Backtest completed successfully!

Last few lines of output:
----------------------------------------
Trade 12: Entry $1.65 → Exit $0.40 → P&L $-375.00 (-75.8%) | stop loss
Trade 13: Entry $1.15 → Exit $0.13 → P&L $-408.00 (-88.7%) | stop loss

✅ Backtest completed! Return: -8.63%
```

### Log Files

Detailed logs are saved to `debug_logs/backtest_debug_YYYYMMDD_HHMMSS.log` containing:

- Full configuration path
- Complete stdout output
- Complete stderr output
- Exit codes
- Exception traces (if any)

## Configuration Requirements

### Strategy YAML Format

The debugger expects strategy configurations to follow the proper format:

```yaml
name: "Strategy Name"
description: "Strategy description"
strategy_type: "long_call"

# Required parameters section
parameters:
  initial_capital: 10000
  position_size: 0.05
  max_positions: 2
  max_hold_days: 30
  entry_frequency: 3

# Exit rules as list of conditions
exit_rules:
  - condition: "profit_target"
    target_percent: 50
    
  - condition: "stop_loss"
    stop_percent: -50
    
  - condition: "time_stop"
    max_days: 21
```

### Python Environment

The debugger requires the following packages (install via `requirements.txt`):

- pandas
- numpy
- PyYAML
- matplotlib
- pyarrow
- fastparquet

## Common Issues and Solutions

### Issue: ModuleNotFoundError

**Solution**: Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Failed to load config: 'parameters'"

**Solution**: Ensure your strategy YAML includes the required `parameters` section.

### Issue: "AttributeError: 'str' object has no attribute 'get'"

**Solution**: Convert `exit_rules` from simple key-value format to list of condition dictionaries.

### Issue: Data files not found

**Solution**: Check that data files exist in the expected directory:
- Default: `spy_options_downloader/spy_options_parquet/`
- Ensure parquet files are present and readable

## Implementation Details

### How It Works

1. **Subprocess Execution**: Runs backtests in a subprocess to capture all output
2. **Dynamic Python Detection**: Automatically uses virtual environment Python if available
3. **Error Extraction**: Parses output to highlight specific error messages
4. **Audit Trail**: Captures AUDIT messages from the backtest for debugging

### Code Structure

The debugger creates a temporary Python script that:
1. Imports the `auditable_backtest` module
2. Sets up data directories and date ranges
3. Runs the backtest with full error capture
4. Returns structured results

## Best Practices

1. **Use Loop Mode Sparingly**: Loop mode is helpful for intermittent issues but can consume resources
2. **Check Logs**: Always review the full log file for complete error context
3. **Clean Old Logs**: Periodically clean the `debug_logs/` directory to save space
4. **Test Incrementally**: Start with simple strategies before testing complex ones

## Future Enhancements

Potential improvements for the debugger:

- [ ] Add data validation checks before running backtest
- [ ] Support for custom date ranges via command line
- [ ] Integration with performance profiling
- [ ] Automatic error pattern detection and suggestions
- [ ] Email/Slack notifications for long-running loops