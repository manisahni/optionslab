# OptionsLab Architecture

## Overview

OptionsLab has been refactored from a monolithic architecture into a modular design with clear separation of concerns. The main orchestration engine (`backtest_engine.py`) coordinates specialized modules that each handle specific aspects of the backtesting process.

## Module Structure

### Core Engine
- **backtest_engine.py** (488 lines)
  - Main orchestration engine
  - Coordinates all modules to run backtests
  - Contains `run_auditable_backtest()` function

### Data Management
- **data_loader.py** (176 lines)
  - Loads market data from parquet files
  - Loads and validates strategy configurations
  - Handles data filtering by date range

### Option Selection
- **option_selector.py** (208 lines)
  - Finds suitable options based on delta/DTE requirements
  - Calculates position sizing
  - Enforces liquidity filters

### Market Analysis
- **market_filters.py** (243 lines)
  - Implements market condition filters (IV regime, MA, RSI, Bollinger)
  - Determines when trades can be entered based on market state

### Position Management
- **greek_tracker.py** (147 lines)
  - Tracks option Greeks throughout position lifecycle
  - Records entry, current, and exit Greeks
  - Provides Greek-based analytics

- **trade_recorder.py** (222 lines)
  - Records trade entries and exits
  - Tracks compliance with strategy rules
  - Maintains trade history

### Exit Strategy
- **exit_conditions.py** (173 lines)
  - Implements all exit logic (profit targets, stop losses, DTE/delta limits)
  - Checks multiple exit conditions in priority order

### Performance Analysis
- **backtest_metrics.py** (261 lines)
  - Calculates performance metrics
  - Generates compliance scorecards
  - Creates implementation analytics

## Module Dependencies

```
backtest_engine.py
    ├── data_loader.py
    ├── option_selector.py
    ├── market_filters.py
    ├── greek_tracker.py
    ├── trade_recorder.py
    ├── exit_conditions.py
    └── backtest_metrics.py
```

## Key Design Principles

1. **Single Responsibility**: Each module handles one specific aspect of backtesting
2. **Clear Interfaces**: Modules communicate through well-defined data structures
3. **Testability**: Individual modules can be tested in isolation
4. **Maintainability**: Changes to one aspect don't require understanding the entire system
5. **Reusability**: Modules can be used independently for other analysis tasks