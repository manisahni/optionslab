# Notebooks Organization Guide

## Directory Structure

```
notebooks/
├── strategies/          # Production-ready, tested strategies
│   ├── pmcc/           # Poor Man's Covered Call strategies
│   ├── strangles/      # Short strangle strategies
│   └── iron_condor/    # Iron condor strategies
│
├── research/           # Active development and experiments
│
├── archive/            # Old versions kept for reference
│   └── 2024/          # Organized by year
│
├── templates/          # Starting points for new work
│   └── research_template.py
│
└── utils/              # Shared utility functions
    └── research_utils.py
```

## Workflow

### 1. Start New Research
```bash
# Copy template for new research
cp templates/research_template.py research/my_new_strategy.py
```

### 2. Development Process
- **Research phase**: Work in `research/` folder
- **Test thoroughly**: Validate with multiple years of data
- **Visual validation**: Always plot results before trusting

### 3. Promote to Strategies
Once a strategy is tested and working:
```bash
# Move to appropriate strategy folder
mv research/my_strategy.py strategies/strangles/my_strategy.py
```

### 4. Archive Old Versions
Keep old versions for reference:
```bash
# Archive with date
mv strategies/pmcc/old_version.py archive/2024/pmcc/old_version_v1.py
```

## File Naming Conventions

### Strategy Files
- **Clear names**: `comprehensive.py`, `rolling.py`, `vs_spy.py`
- **No redundant suffixes**: Avoid `_backtest`, `_fixed`, `_final`
- **Version in archive only**: `v1`, `v2` only in archive folder

### Research Files
- **Descriptive**: `explore_vega_neutral.py`, `test_delta_hedging.py`
- **Date prefix for experiments**: `20240901_experiment.py`

## Using Jupytext

All `.py` files are Jupytext-compatible. To work with them:

```bash
# Convert to notebook
jupytext --to notebook research/my_strategy.py

# Sync changes back
jupytext --sync research/my_strategy.ipynb

# Set up pairing
jupytext --set-formats ipynb,py:percent research/my_strategy.py
```

## Best Practices

### 1. Always Start with Data Validation
```python
from utils.research_utils import validate_options_data

df = pd.read_parquet('path/to/data.parquet')
validate_options_data(df)  # Check for common issues
```

### 2. Visual-First Development
- Plot raw data before calculations
- Verify option chains visually
- Check P&L charts for anomalies

### 3. Document Assumptions
```python
# ASSUMPTION: Strike prices in dollars (not cents)
# ASSUMPTION: No early assignment for American options
# DATA QUIRK: 2022 data has some zero bid prices
```

### 4. Performance Benchmarks
Always compare against:
- Buy & hold SPY
- Simple LEAP strategy
- Your strategy variations

## Common Data Issues

| Issue | Check | Fix |
|-------|-------|-----|
| Strike in cents | `df['strike'].max() > 10000` | `df['strike'] / 1000` |
| Missing dates | Date continuity | Note gaps, don't interpolate |
| Zero bids | Common for far OTM | Filter: `df[df['bid'] > 0]` |
| Bad Greeks | NaN or extreme values | Use mid-price fallback |

## Strategy Categories

### PMCC (Poor Man's Covered Call)
- Long-dated call (LEAP) + short near-term calls
- Capital efficient alternative to covered calls
- Files: `comprehensive.py`, `rolling.py`, `vs_spy.py`

### Strangles (Coming Soon)
- Short OTM call + short OTM put
- Profit from range-bound markets
- High win rate, manage risk carefully

### Iron Condors (Coming Soon)
- Credit spread with defined risk
- Short strangle + protective wings
- Lower risk than naked strangles

## Quick Commands

```bash
# Run a strategy
cd notebooks
python strategies/pmcc/comprehensive.py

# Convert notebook to HTML
jupyter nbconvert --to html strategies/pmcc/comprehensive.ipynb

# Check data format
python -c "import pandas as pd; df = pd.read_parquet('../data/spy_options/SPY_OPTIONS_2024_COMPLETE.parquet'); print(df.info())"
```

## Tips for Success

1. **Start simple**: Basic mechanics first, add complexity later
2. **Use small date ranges**: Test with 1 month before running full years
3. **Keep failed attempts**: Archive them with notes on why they failed
4. **Version control friendly**: Use .py format for clean diffs
5. **Reproducible**: Set random seeds, document package versions

---

*Remember: Every successful strategy started as a messy research notebook!*