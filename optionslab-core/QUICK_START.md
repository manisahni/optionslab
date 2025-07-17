# 🚀 Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Three Ways to Use the Backtester

### 1. 🎮 Interactive Mode (Recommended for Beginners)
```bash
python backtester_enhanced.py --interactive
```
Guided setup with explanations and validation.

### 2. 🔍 Explore Available Options
```bash
# View all strategies with descriptions
python backtester_enhanced.py --strategies

# See usage examples
python backtester_enhanced.py --examples

# Get help
python backtester_enhanced.py --help
```

### 3. ⚡ Direct Command Line
```bash
# Basic usage
python backtester_enhanced.py \
    --strategy long_call \
    --start-date 20220601 \
    --end-date 20220630 \
    --initial-capital 100000
```

## Quick Tests

### Test with Recent Data (1 month)
```bash
python backtester_enhanced.py \
    --strategy straddle \
    --start-date 20240601 \
    --end-date 20240630
```

### Bull Market Test (2021)
```bash
python backtester_enhanced.py \
    --strategy long_call \
    --start-date 20210101 \
    --end-date 20211231 \
    --delta-threshold 0.30
```

### Bear Market Test (2022)
```bash
python backtester_enhanced.py \
    --strategy long_put \
    --start-date 20220101 \
    --end-date 20221231 \
    --delta-threshold 0.30
```

### COVID Volatility Test
```bash
python backtester_enhanced.py \
    --strategy straddle \
    --start-date 20200301 \
    --end-date 20200630 \
    --delta-threshold 0.50
```

## Save Results
```bash
python backtester_enhanced.py \
    --strategy long_call \
    --start-date 20220101 \
    --end-date 20220630 \
    --output results/my_backtest
```

This creates:
- `results/my_backtest.csv` - Trade log
- `results/my_backtest_portfolio.csv` - Portfolio history

## Features

✅ **Interactive Mode** - Guided setup  
✅ **Strategy Descriptions** - Learn before you test  
✅ **Input Validation** - Helpful error messages  
✅ **Progress Tracking** - Real-time updates  
✅ **Colorized Output** - Easy to read results  
✅ **Smart Defaults** - Works out of the box  
✅ **Data Validation** - Checks available data  
✅ **Rich Help** - Examples and explanations  

## Need Help?

- 🎮 **New to options?** → Use `--interactive` mode
- 📚 **Need examples?** → Use `--examples` 
- 🔍 **Compare strategies?** → Use `--strategies`
- ❓ **Stuck?** → Use `--help`

## Data Coverage

Your dataset includes **5 years** of SPY options data:
- **Period:** July 2020 - July 2025  
- **Trading Days:** 1,254 days
- **Coverage:** 96.4% (missing only holidays)
- **Options per Day:** 8,000-10,000 contracts
- **Full Greeks:** Delta, Gamma, Theta, Vega, Rho