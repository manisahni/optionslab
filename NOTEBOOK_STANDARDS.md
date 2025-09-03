# 📓 Research Notebook Standards

## Notebook Organization
```
notebooks/
├── templates/              # Starting templates (USE THESE!)
│   └── research_template.py    # Standard template for ALL new research
├── utils/                  # Shared utility functions
│   └── research_utils.py       # Common data validation, metrics
├── research/               # Active development (start here)
│   └── strategy_exploration_YYYY.py
├── strategies/             # Production-ready implementations
│   ├── pmcc/              # Poor Man's Covered Call
│   ├── zebra/             # Zebra strategies
│   ├── strangles/         # Short strangles
│   └── iron_condor/       # Iron condors
└── archive/               # Historical versions with notes
    └── 2024/              # Organized by year
```

## 🔴 CRITICAL: Check Existing Infrastructure Before Writing New Code

### When Creating New Notebooks:

1. **ALWAYS start from the template**:
```bash
# Copy the template as your starting point
cp notebooks/templates/research_template.py notebooks/research/my_new_strategy.py
```

2. **FIRST check what already exists** - Before writing any utility function:
   - Check `optionslab/` modules for backtesting functions
   - Check `notebooks/utils/research_utils.py` for common utilities
   - Check existing strategies in `notebooks/strategies/` for similar patterns
   - The template already includes:
     - Data loading with validation
     - Strike price format checking (cents vs dollars) - NOW AUTOMATIC in data_loader!
     - Performance metrics calculation
     - SPY benchmark comparison
     - Visualization framework
   - **CRITICAL**: `optionslab/data_loader.py` now automatically converts strikes from cents!

3. **REUSE existing backtesting infrastructure when available**:
```python
# First, explore what's available
from optionslab import backtest_engine, option_selector, visualization

# Check if these modules have what you need:
# - backtest_engine: run_backtest(), calculate_returns()
# - option_selector: find_options_by_delta(), filter_by_dte()
# - visualization: create_performance_charts(), plot_trades()

# Only write custom code if existing functions don't meet your needs
```

4. **ADAPT the template structure**:
   - Section 1-3: Keep data loading/validation (modify if needed)
   - Section 4: Implement YOUR strategy logic
   - Section 5-10: Use or extend the analysis framework

## Jupytext & Papermill Standards

### Core Principles
All notebooks in this project **MUST** use Jupytext and Papermill for:
- **Version Control**: .py files are git-friendly (diffs, merges, reviews)
- **Reproducibility**: Parameterized execution with consistent results
- **Automation**: Batch processing and CI/CD integration
- **Collaboration**: Clean code reviews without notebook JSON noise

### Jupytext Configuration
Project uses `.jupytext.toml` for automatic pairing:
- **Primary format**: `.py` files with percent format
- **Secondary format**: `.ipynb` for interactive development
- **Auto-sync**: Changes in either format sync to the other
- **Clean metadata**: No unnecessary notebook metadata in .py files

### Papermill Standards

#### Parameter Cell
Every notebook MUST have a parameters cell for Papermill:
```python
# %% tags=["parameters"]
# Papermill parameters - these will be overridden during execution
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"
INITIAL_CAPITAL = 10000
STRATEGY_TYPE = "pmcc"
OUTPUT_DIR = "results/"
```

#### Execution Pattern
```python
# Execute with parameters
papermill notebooks/research/strategy.py \
    notebooks/research/strategy_executed.ipynb \
    -p START_DATE "2023-01-01" \
    -p END_DATE "2023-12-31" \
    -p INITIAL_CAPITAL 25000
```

#### Batch Execution
Use `notebooks/utils/batch_execute.py` for parameter sweeps:
```python
from notebooks.utils.batch_execute import run_parameter_sweep

# Test strategy across different market periods
periods = [
    {"START_DATE": "2020-03-01", "END_DATE": "2020-12-31"},  # COVID recovery
    {"START_DATE": "2022-01-01", "END_DATE": "2022-12-31"},  # Bear market
    {"START_DATE": "2023-01-01", "END_DATE": "2023-12-31"},  # Recovery
]

results = run_parameter_sweep(
    "notebooks/strategies/pmcc/pmcc_backtest.py",
    periods,
    output_dir="results/pmcc_sweep/"
)
```

## File Format Rules

### Required Headers
All notebook .py files MUST start with Jupytext header:
```python
# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
# ---
```

### Cell Markers
Use percent format for cells:
```python
# %%
# Code cell

# %% [markdown]
# Markdown cell

# %% tags=["parameters"]
# Parameter cell for Papermill
```

## Workflow Commands

### Create New Notebook
```bash
# Start from template
cp notebooks/templates/research_template.py notebooks/research/new_strategy.py

# Create paired .ipynb
jupytext --sync notebooks/research/new_strategy.py
```

### Sync Changes
```bash
# After editing .py or .ipynb
jupytext --sync notebooks/research/my_strategy.py
```

### Execute with Parameters
```bash
# Single execution
papermill notebooks/research/strategy.py output.ipynb -p PARAM value

# Batch execution
python notebooks/utils/batch_execute.py --config sweep_config.yaml
```

## Best Practices

### DO ✅
- **Always** pair .py and .ipynb files
- **Always** include parameter cell for Papermill
- **Always** commit .py files to git
- **Always** use relative imports from project root
- **Always** validate data before processing
- **Always** document parameters in docstrings

### DON'T ❌
- **Never** commit .ipynb files with outputs (clear before commit)
- **Never** use absolute paths in notebooks
- **Never** hardcode parameters (use parameter cell)
- **Never** create notebooks without Jupytext pairing
- **Never** mix notebook and module code

## Git Workflow
```bash
# Before committing notebooks
jupytext --sync notebooks/**/*.py  # Sync all notebooks
jupyter nbconvert --clear-output --inplace notebooks/**/*.ipynb  # Clear outputs
git add notebooks/**/*.py  # Add .py files
git add -u notebooks/**/*.ipynb  # Update .ipynb files
```

## CI/CD Integration
Notebooks can be tested in CI using Papermill:
```yaml
# .github/workflows/test_notebooks.yml
- name: Test Notebooks
  run: |
    papermill notebooks/tests/test_strategy.py /tmp/output.ipynb \
      -p TEST_MODE true \
      -p DATA_SIZE small
```

## Research Workflow

### 1. Start with Template (REQUIRED)
```bash
# Always copy from template, never create empty file
cp notebooks/templates/research_template.py notebooks/research/my_strategy_v1.py
```

### 2. Use Jupytext Format
```bash
# Set up two-way sync between .py and .ipynb
venv/bin/jupytext --set-formats ipynb,py:percent notebooks/research/my_strategy_v1.py
```

### 3. Data Validation First
Always validate data format before processing:
```python
from notebooks.research_utils import validate_options_data, load_spy_data

# Load and validate data
df = load_spy_data([2023, 2024])

# Critical checks
assert df['strike'].max() < 10000, "Strikes likely in cents, divide by 1000"
assert not df['date'].isna().any(), "Missing dates found"
```

### 4. Visual-First Validation
- Plot raw data before calculations
- Check for spikes/anomalies visually  
- Verify option chain makes sense

### 5. Incremental Complexity
- **v1**: Basic strategy mechanics
- **v2**: Add position management
- **v3**: Add risk controls
- **comprehensive**: Multi-period analysis

## Common Data Issues

| Issue | Detection | Fix |
|-------|-----------|-----|
| Strike prices in cents | `df['strike'].max() > 10000` | `df['strike'] = df['strike'] / 1000` |
| Missing dates | Check date continuity | Note gaps, don't interpolate |
| Zero bids | Common for far OTM | Filter: `df[df['bid'] > 0]` |
| Bad Greeks | Check for NaN/extreme values | Use mid_price fallback |

## 🎯 When Asked to Create New Research Notebooks

### WORKFLOW - Check First, Then Build:

1. **Start with the template**:
```python
# Copy template as foundation
import shutil
shutil.copy('notebooks/templates/research_template.py', 
            'notebooks/research/new_strategy.py')
```

2. **Explore existing infrastructure FIRST**:
```python
# Check what's already available before writing new code
import optionslab.backtest_engine as be
import optionslab.option_selector as os
help(be)  # See available functions
help(os)  # Check option selection utilities

# Look at existing strategies for patterns
# notebooks/strategies/pmcc/comprehensive.py - complex multi-leg example
# notebooks/strategies/zebra/zebra_improved.py - advanced position management
```

3. **Reuse when possible, extend when needed**:
```python
# PREFERRED: Use existing functions
from optionslab.backtest_engine import run_backtest
from optionslab.option_selector import find_options_by_delta

# IF NEEDED: Extend for specific requirements
def my_custom_entry_logic(df, existing_positions):
    # Build on top of existing infrastructure
    candidates = find_options_by_delta(df, delta_range=(0.15, 0.25))
    # Add your custom filtering
    return filter_by_my_criteria(candidates)
```

### Best Practices:
- ✅ **Check first**: Look for existing functions before writing new ones
- ✅ **Reuse common patterns**: Study existing strategies for similar logic
- ✅ **Extend thoughtfully**: Add custom logic only for unique requirements
- ✅ **Keep template structure**: It handles common pitfalls (strike format, etc.)
- ⚠️ **Avoid duplication**: If you're writing something generic, it probably exists
- ⚠️ **Document differences**: Note when/why you diverge from existing patterns

### Key Existing Components to Check:
- **Data Loading**: Template handles parquet loading and validation
- **Backtesting**: `optionslab.backtest_engine` for systematic tests
- **Option Selection**: `optionslab.option_selector` for finding options
- **Visualization**: `optionslab.visualization` for standard charts
- **Metrics**: `notebooks.utils.research_utils` for performance calcs
- **Trade Logging**: `optionslab.csv_enhanced` for detailed records

## Performance Metrics Standard

Use `research_utils.calculate_performance_metrics()` for consistency:
- Total Return
- Sharpe Ratio (annualized)
- Sortino Ratio
- Maximum Drawdown
- Volatility (annualized)
- Win Rate
- Best/Worst Days

## Quick Validation Commands

```bash
# Check data format quickly
venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/spy_options/spy_options_eod_20240815.parquet')
print(f'Strike range: {df.strike.min()}-{df.strike.max()}')
print(f'Records: {len(df):,}')
"

# Run research notebook
venv/bin/python notebooks/research/my_analysis.py

# Convert notebook to HTML for sharing
venv/bin/jupyter nbconvert --to html notebooks/research/my_analysis.ipynb
```

## Research Best Practices

1. **Document assumptions** - Note data quirks found
2. **Keep failed attempts** - Archive with notes on why they failed
3. **Version control friendly** - Use Jupytext .py format
4. **Reproducible** - Set random seeds, document package versions
5. **Fast iteration** - Use small date ranges first, then expand

## Lessons Learned from PMCC Research

Common pitfalls to avoid:
- **Strike format confusion**: Always check if strikes are in cents
- **Position value bugs**: Carefully handle long vs short positions
- **Leverage misconceptions**: Short options can destroy leverage
- **Path dependencies**: Use consistent relative paths from project root