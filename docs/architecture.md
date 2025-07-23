# OptionsLab Architecture

## Overview

OptionsLab is a professional-grade options backtesting system with a modular architecture, AI integration, and comprehensive visualization capabilities. The system uses a clean separation of concerns with the main orchestration engine (`backtest_engine.py`) coordinating specialized modules for each aspect of backtesting.

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
  - Computes risk-adjusted returns

### Visualization
- **visualization.py** (1000+ lines)
  - Creates all charts and plots
  - P&L curves, heatmaps, distributions
  - Greeks evolution tracking
  - Compliance visualizations

### AI Integration
- **ai_openai.py** (700+ lines)
  - OpenAI API integration
  - Strategy analysis functions
  - Performance optimization suggestions
  - Natural language chat interface
  - Vision capabilities for chart analysis

### Data Storage
- **csv_enhanced.py** (400+ lines)
  - Comprehensive CSV format for trade logs
  - Includes metadata, trades, strategy config, audit logs
  - Handles timestamp serialization
  - Excel-compatible format

### Web Interface
- **app.py** (1300+ lines)
  - Gradio-based web interface
  - Multi-tab layout for backtesting, visualization, AI
  - Unified backtest management
  - Real-time updates
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

## Data Flow

1. **User Input** → Gradio Interface (`app.py`)
2. **Configuration** → Strategy YAML + Parameters
3. **Data Loading** → `data_loader.py` reads parquet files
4. **Backtest Execution** → `backtest_engine.py` orchestrates:
   - Market filtering
   - Option selection
   - Position entry/exit
   - Greeks tracking
   - Trade recording
5. **Results Processing** → Metrics calculation, compliance scoring
6. **Storage** → CSV format via `csv_enhanced.py`
7. **Visualization** → Charts via `visualization.py`
8. **AI Analysis** → OpenAI integration via `ai_openai.py`

## Key Design Principles

1. **Single Responsibility**: Each module handles one specific aspect of backtesting
2. **Clear Interfaces**: Modules communicate through well-defined data structures
3. **Testability**: Individual modules can be tested in isolation
4. **Maintainability**: Changes to one aspect don't require understanding the entire system
5. **Reusability**: Modules can be used independently for other analysis tasks
6. **Extensibility**: Easy to add new strategies, indicators, or analysis tools
7. **Transparency**: Full audit trails and compliance tracking