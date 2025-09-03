# Daily OptionsLab System - Project Instructions

## ⚠️ PROJECT BOUNDARIES

### This Project Scope
- **ONLY** daily EOD options strategies
- **ONLY** strategies that hold overnight/multiple days
- **ONLY** YAML-defined systematic strategies
- **Focus**: Daily options backtesting with full audit trails

### DO NOT Reference
- ❌ `/Users/nish_macbook/trading/0dte-intraday/` - Different project
- ❌ Intraday or 0DTE strategies - Wrong timeframe
- ❌ Minute-level data analysis - We use daily data
- ❌ ORB or opening range strategies - That's 0dte-intraday

## 📚 Detailed Documentation

For comprehensive instructions on specific topics, see:

- **[PROTECTED_FILES.md](./PROTECTED_FILES.md)** - Core infrastructure protection rules
- **[DATA_MANAGEMENT.md](./DATA_MANAGEMENT.md)** - SPY options dataset and data handling
- **[BACKTESTING_CHECKLIST.md](./BACKTESTING_CHECKLIST.md)** - Golden checklist for options backtests
- **[NOTEBOOK_STANDARDS.md](./NOTEBOOK_STANDARDS.md)** - Research notebook guidelines
- **[TESTING_METHODOLOGY.md](./TESTING_METHODOLOGY.md)** - 5-phase testing approach
- **[SYSTEM_CAPABILITIES.md](./SYSTEM_CAPABILITIES.md)** - Advanced position management features
- **[backtests/README.md](./backtests/README.md)** - Centralized backtest management system
- **[BACKTEST_USAGE_GUIDE.md](./BACKTEST_USAGE_GUIDE.md)** - Step-by-step backtesting guide

## Project Architecture

### Directory Structure
```
daily-optionslab/
├── optionslab/             # Core backtesting infrastructure (PROTECTED)
│   ├── app.py              # Gradio UI (port 7862)
│   ├── backtest_engine.py  # Main orchestration
│   ├── option_selector.py  # Option selection logic
│   └── visualization.py    # Chart generation
│
├── data/spy_options/       # 1,265 EOD files (PROTECTED - DO NOT DELETE)
├── config/                 # Strategy YAML configurations
├── notebooks/              # Research and strategy development
├── backtests/              # Centralized backtest management
│   ├── results/            # Stored backtest results by year/strategy
│   ├── backtest_manager.py # Core management module
│   ├── gradio_results_viewer.py # UI for viewing results
│   └── notebooks/templates/ # Analysis templates
├── thetadata_client/       # ThetaData API client (PROTECTED)
└── venv/                   # Project-specific environment
```

## Quick Start

### Starting OptionsLab
```bash
cd /Users/nish_macbook/trading/daily-optionslab
source venv/bin/activate
./start_optionslab.sh
# Open: http://localhost:7862
```

### Running a Backtest
```python
from optionslab.backtest_engine import run_auditable_backtest

results = run_auditable_backtest(
    data_file='data/spy_options/',
    config_file='config/short_put.yaml',
    start_date='2023-01-01',
    end_date='2024-12-31'
)
```

### Centralized Backtest Management

Store, manage, and compare all backtest results:

```bash
# Run and store backtest with automatic indexing
venv/bin/python backtests/backtest_manager.py run \
    --config config/strategy.yaml \
    --start 2024-01-01 \
    --end 2024-12-31 \
    --description "Q4 2024 strategy test"

# List all stored backtests
venv/bin/python backtests/backtest_manager.py list

# Get specific backtest details
venv/bin/python backtests/backtest_manager.py get --id <result_id>

# Compare multiple backtests
venv/bin/python backtests/backtest_manager.py compare --ids id1,id2,id3

# Launch interactive results viewer UI
venv/bin/python backtests/gradio_results_viewer.py
# Opens at http://localhost:7863
```

The system automatically:
- Stores all results in `backtests/results/` organized by year/strategy/timestamp
- Maintains a searchable index of all backtests
- Captures complete audit trails and metrics
- Enables comparison across strategies and time periods
- Integrates with both notebook and Gradio interfaces

## Key Principles

### 🚫 Protected Files
- **NEVER modify** core optionslab modules without explicit permission
- User MUST explicitly request: "modify optionslab/[filename]"
- See [PROTECTED_FILES.md](./PROTECTED_FILES.md) for details

### 📊 Use Existing Data First
- We have **1,265 daily SPY options files** (July 2020 - July 2025)
- **ALWAYS use existing data** before downloading new data
- See [DATA_MANAGEMENT.md](./DATA_MANAGEMENT.md) for details

### ✅ Follow Testing Methodology
- Use 5-phase incremental testing approach
- Test components before integration
- See [TESTING_METHODOLOGY.md](./TESTING_METHODOLOGY.md) for details

### 📋 Use Backtesting Checklist
- Follow 9-step golden checklist for all backtests
- Ensure reproducible, accurate results
- See [BACKTESTING_CHECKLIST.md](./BACKTESTING_CHECKLIST.md) for details

## 🎯 USE EXISTING MODULES FIRST

Before writing ANY new backtesting code, check if optionslab already has it:

| Task | Use This Module | Key Function |
|------|-----------------|--------------|
| Load data | `data_loader` | `load_data()` - handles strike conversion! |
| Find options | `option_selector` | `find_suitable_options()` |
| Track Greeks | `greek_tracker` | `GreekTracker` class |
| Record trades | `trade_recorder` | `TradeRecorder` class |
| Check exits | `exit_conditions` | `check_exit()` |
| Calculate metrics | `backtest_metrics` | `calculate_performance_metrics()` |
| Generate charts | `visualization` | `create_backtest_charts()` |
| Run complete backtest | `backtest_engine` | `run_auditable_backtest()` |

## Strategy Configuration

Strategies are defined in YAML files:
```yaml
name: "Short Strangle Daily"
type: "short_strangle"
entry:
  delta_range: [0.15, 0.25]
  dte_range: [30, 45]
exit:
  take_profit: 0.50
  stop_loss: 2.00
risk:
  max_position_size: 0.10
```

## Critical Rules

### DO NOT
- ❌ Mix daily with intraday strategies
- ❌ Modify protected files without permission
- ❌ Delete or overwrite existing SPY data
- ❌ Reference 0dte-intraday project
- ❌ Run without ThetaData Terminal active

### ALWAYS
- ✅ Use YAML for strategy definitions
- ✅ Check audit trail for every trade
- ✅ Validate data before backtesting
- ✅ Use existing infrastructure first
- ✅ Follow the testing methodology
- ✅ Use centralized backtest manager for storing results

## Common Issues & Solutions

### ImportError Fix
- **Problem**: ImportError when running from wrong directory
- **Solution**: Run from project root using module syntax
```bash
# Wrong: python optionslab/app.py
# Right: python -m optionslab.app
```

### Port Already in Use
```bash
lsof -i :7862
kill -9 <PID>
```

### ThetaData Connection
- Check terminal is running: `lsof -i :11000`
- Restart if needed
- See global CLAUDE.md for ThetaData setup

## Quick Commands

```bash
# Check context
pwd  # Should show: /Users/nish_macbook/trading/daily-optionslab

# Activate environment
source venv/bin/activate

# Start application
./start_optionslab.sh

# Download today's data (if needed)
python spy_options_downloader/downloader.py --date $(date +%Y%m%d)

# Backtest management
python backtests/backtest_manager.py list  # List all backtests
python backtests/backtest_manager.py get --id <result_id>  # Get specific result
python backtests/backtest_manager.py compare --ids id1,id2  # Compare results
python backtests/backtest_manager.py summary  # System statistics

# Run tests
python -m pytest tests/ -v
```

## 📊 Comprehensive Backtesting Guidelines

### Centralized Backtest Management System
We have a **centralized system** for managing all backtests. See [backtests/README.md](./backtests/README.md) for details.

**Quick Commands:**
```python
# Run single backtest
from backtests.backtest_manager import BacktestManager
manager = BacktestManager()
results = manager.run_backtest('config/long_call_simple.yaml', '2023-01-01', '2024-12-31')

# Run comprehensive analysis across all periods
from backtests.run_comprehensive_analysis import run_comprehensive_backtest
results = run_comprehensive_backtest('config/long_call_regime_filtered.yaml')

# View results in UI
# python backtests/gradio_results_viewer.py
```

### ALWAYS Use Full Available Dataset
We have **5+ years of daily SPY options data** (July 2020 - July 2025) covering:
- 2020: COVID recovery period (high volatility)
- 2021: Bull market with low volatility
- 2022: Bear market with -25.4% drawdown
- 2023: Recovery with multiple 10-15% corrections
- 2024-2025: Recent bull market

### Mandatory Backtesting Periods
When testing any strategy, ALWAYS run backtests across:

```python
# Required test periods for comprehensive analysis
MANDATORY_PERIODS = [
    {"name": "Full Dataset", "start": "2020-07-15", "end": "2025-07-11"},
    {"name": "2022 Bear Market", "start": "2022-01-01", "end": "2022-12-31"},
    {"name": "2023 Recovery", "start": "2023-01-01", "end": "2023-12-31"},
    {"name": "2024 Bull Run", "start": "2024-01-01", "end": "2024-12-31"},
]
```

### Market Regime Analysis
The system identifies three volatility regimes:
- **Low Volatility** (<15% annualized): 620 days, +18.7% avg returns
- **Normal Volatility** (15-25%): 379 days, +2.3% avg returns  
- **High Volatility** (>25%): 105 days, +31.7% avg returns

Major drawdown periods to test specifically:
- **2022 Q1-Q4**: Extended -25% bear market (285 days)
- **2023 Q3-Q4**: Multiple 10-15% corrections

### Comprehensive Testing Protocol
```bash
# Run full comprehensive analysis for any strategy
venv/bin/python backtests/run_comprehensive_analysis.py \
    --config config/your_strategy.yaml \
    --analyze-regimes \
    --compare-periods
```

This will:
1. Backtest across all mandatory periods
2. Analyze performance by market regime
3. Identify optimal market conditions for the strategy
4. Store results in centralized system for comparison

### Strategy Validation Requirements
Before considering any strategy "validated", it must:
- ✅ Be tested on the FULL 5-year dataset
- ✅ Show performance metrics for each market regime
- ✅ Demonstrate behavior during 2022 bear market
- ✅ Have clear rules for when to pause/resume trading
- ✅ Include drawdown analysis and recovery periods

## Performance Expectations

### Typical Strategy Results (Full Period)
- **Short Strangle**: 60-70% win rate, 1.5 Sharpe
- **Iron Condor**: 65-75% win rate, 1.2 Sharpe
- **Calendar Spread**: 55-65% win rate, 1.0 Sharpe
- **Long Call**: Variable by regime (test all periods)
- **PMCC**: Requires defensive adjustments in bear markets

### Risk Guidelines
- Max position: 10% of capital
- Max portfolio heat: 30%
- Stop at 2x credit received
- Take profit at 50% of max profit
- **Regime-specific adjustments required**

## Advanced Features

### Greeks-Based Position Management
- Stop loss system with daily mark-to-market
- Full Greeks tracking (delta, gamma, vega, theta)
- Greeks-based exit conditions
- Portfolio-level Greeks aggregation
- See [SYSTEM_CAPABILITIES.md](./SYSTEM_CAPABILITIES.md) for details

### AI Integration
- Strategy compliance checking
- Performance optimization suggestions
- Natural language trade analysis
- Chart interpretation with GPT-4V
- Set OPENAI_API_KEY in `.env` to enable

## Research & Development

For creating new strategies or research notebooks:
- **ALWAYS** start from templates in `notebooks/templates/`
- **CHECK** existing strategies in `notebooks/strategies/`
- **FOLLOW** standards in [NOTEBOOK_STANDARDS.md](./NOTEBOOK_STANDARDS.md)
- **USE** Jupytext for version control
- **VALIDATE** data quality before analysis

---
**Remember**: This is the DAILY project for EOD options strategies only.