# OptionsLab - Auditable Backtesting System

This directory contains the core backtesting system files.

## Core Files

- `auditable_backtest.py` - Main backtesting engine with full audit trail
- `auditable_gradio_app.py` - Web interface for running backtests
- `start_auditable.sh` - Launch script for the system

## Features

- Full audit trail for every decision
- Greeks and IV tracking
- Technical indicators (MA, RSI, Bollinger Bands)
- Multiple exit strategies
- Export to CSV/JSON
- Comprehensive visualization

## Usage

```bash
cd optionslab
./start_auditable.sh
```

Then open http://localhost:7860 in your browser.

## Data Requirements

The system expects SPY options data in parquet format. Data should be placed in:
```
../spy_options_downloader/spy_options_parquet/
```

## Strategy Configuration

Strategies are defined in YAML files. See the example strategy files in the parent directory.