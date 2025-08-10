# Market Data Directory Structure

This directory contains all tools and data for 0DTE SPY options trading analysis.

## Directory Organization

### 📁 core/
Core database and utility modules used by all other tools.

- **zero_dte_spy_options_database.py** - Main database interface for 0DTE options data
- **zero_dte_analysis_tools.py** - Analysis utilities for options strategies
- **options_database_manager.py** - General options database management

### 📁 backtesting/
Backtesting engines and strategy optimization tools.

- **transparent_strangle_backtester.py** - Educational backtester with detailed explanations
- **strangle_backtest_tool.py** - Production backtesting for strangle strategies
- **strangle_optimizer_visual.py** - Visual optimization tool with 3D profit landscapes
- **simple_strangle_viz.py** - Quick visualization tool for strangle analysis

### 📁 dashboards/
Interactive web dashboards for analysis and monitoring.

- **educational_strangle_dashboard.py** - Gradio dashboard with tutorials and backtesting
- **maintenance_dashboard.py** - System maintenance and data quality monitoring
- **start_strangle_dashboard.sh** - Launch script for strangle dashboard (port 7863)
- **templates/** - HTML templates for dashboards

### 📁 data_management/
Tools for downloading, monitoring, and maintaining market data.

#### downloaders/
- **download_full_year_0dte.py** - Download full year of 0DTE options data
- **robust_download_manager.py** - Fault-tolerant download manager with resume capability
- **spy_options_minute_downloader.py** - Minute-level options data downloader

#### monitoring/
- **download_monitor.py** - Real-time download progress monitoring
- **download_summary.py** - Generate download completion reports
- **watch_download.py** - Live download watcher

#### maintenance/
- **daily_zero_dte_update.py** - Daily cron job for data updates
- **zero_dte_maintenance.py** - Database maintenance utilities
- **verify_*.py** - Data verification scripts

### 📁 analysis/
Analysis and research tools for market data.

#### data_quality/
- **diagnose_data_quality.py** - Comprehensive data quality analysis
- **analyze_strangle_selection.py** - Debug strangle strike selection
- **investigate_strangle_data.py** - Deep dive into specific trades

#### research/
- **analyze_strangles.py** - Strangle strategy research tools
- **visualize_zero_dte_sample.py** - Sample data visualization

#### quick_checks/
- **options_quick_analysis.py** - Quick data checks and summaries
- Various check_*.py scripts for specific validations

### 📁 tests/
Test scripts for API connections and functionality.

### 📁 data/
All market data files - CLEARLY SEPARATED BY TYPE.

#### 📊 options_data/spy_0dte_minute/
**MINUTE-LEVEL OPTIONS DATA** (not daily!)
- 249 trading days of 0DTE SPY options chains
- ~50 contracts tracked every minute (9:30 AM - 4:00 PM)
- ~19,550 records per day
- Includes: bid/ask, Greeks (delta, gamma, theta, vega), implied volatility
- File format: `zero_dte_spy_YYYYMMDD.parquet`

#### 📈 stock_data/spy_minute/
**MINUTE-LEVEL STOCK DATA** (not options!)
- SPY stock price bars at 1-minute intervals
- 391 bars per day (9:30 AM - 4:00 PM)
- Includes: open, high, low, close, volume
- File format: `SPY_1min.parquet`
- **Note**: Options data also contains SPY prices (underlying_price_dollar) but only as snapshots.
  Stock data provides full OHLCV bars with volume - use when you need complete price action.

#### 🗄️ archive/
- Old data formats and duplicate files

### 📁 logs/
Log files and exported results.

### 📁 temp/
Temporary scripts pending review or deletion.

## Quick Start

### Run Educational Dashboard
```bash
cd dashboards
./start_strangle_dashboard.sh
# Open http://localhost:7863
```

### Run a Backtest
```python
import sys
sys.path.append('core')
from transparent_strangle_backtester import TransparentStrangleBacktester

backtester = TransparentStrangleBacktester()
results = backtester.backtest_period("20250728", "20250801")
```

### Check Data Quality
```bash
python analysis/data_quality/diagnose_data_quality.py
```

## Data Format

The main 0DTE database contains parquet files with these columns:
- symbol, expiration, strike, right (CALL/PUT)
- timestamp, bid, ask, bid_size, ask_size
- delta, gamma, theta, vega, rho
- implied_vol, underlying_price

## Known Issues & Solutions

### 1. All Greeks Have Data Quality Issues
**Problems Found** (from ThetaData Greeks endpoint):
- **Delta**: 65% of calls incorrectly show delta=1.0
- **Gamma**: Completely MISSING from dataset (all NaN)
- **Theta**: 81% incorrectly show theta=0.0 (should be negative for 0DTE)
- **Vega**: 69% incorrectly show vega=0.0
- **Rho**: 69% incorrectly show rho=0.0
- **Implied Vol**: 65% show IV=0.0 (impossible)

**Solution**: Implemented Black-Scholes corrections in `core/black_scholes_calculator.py`
- Recalculates ALL Greeks using proper Black-Scholes formulas
- Adds missing gamma calculations
- Ensures theta is negative (time decay)
- Validates Greek relationships (gamma/vega peak at ATM)
- Improves data quality score from 62.5% to 80%+

**Usage**:
```python
from core.black_scholes_calculator import BlackScholesCalculator
calculator = BlackScholesCalculator()
corrected_df = calculator.correct_options_data(df)
```

### 2. Execution Assumptions
**Problem**: Backtests often assume unrealistic mid-price execution
**Solution**: Created enhanced backtester with multiple execution modes:
- **Conservative**: Always cross the spread (most realistic for retail)
- **Midpoint**: Execute at mid with small slippage
- **Aggressive**: Try to get inside the spread (professional traders)

### 3. Wide Bid-Ask Spreads
**Problem**: Spreads widen significantly near close (15:50)
**Solution**: Exit positions by 3:50 PM to avoid worst spreads

### 4. Missing Volume Data
**Status**: Volume data not available in current dataset
**Workaround**: Use bid-ask spreads as liquidity proxy

## Maintenance

- Run `daily_zero_dte_update.py` via cron for daily updates
- Check data quality weekly with diagnosis scripts
- Archive old logs monthly