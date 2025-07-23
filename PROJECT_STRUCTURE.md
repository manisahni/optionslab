# Project Structure Overview

## Directory Organization

```
thetadata-api/
│
├── optionslab/                    # Core backtesting system
│   ├── app.py                    # Gradio web interface (main entry)
│   ├── backtest_engine.py        # Main orchestration engine
│   ├── data_loader.py            # Data loading utilities
│   ├── option_selector.py        # Option selection logic
│   ├── market_filters.py         # Market condition filters
│   ├── greek_tracker.py          # Greeks tracking
│   ├── trade_recorder.py         # Trade recording
│   ├── exit_conditions.py        # Exit logic
│   ├── backtest_metrics.py       # Performance metrics
│   ├── visualization.py          # Chart generation
│   ├── ai_openai.py             # OpenAI integration
│   ├── csv_enhanced.py          # CSV storage format
│   ├── data/                    # SPY options data (2020-2025)
│   └── trade_logs/              # Backtest results storage
│
├── thetadata_client/             # ⚠️ CRITICAL: ThetaData API client
│   ├── __init__.py              # Package initialization
│   ├── discovery.py             # Option discovery utilities
│   ├── utils.py                 # Data fetching utilities
│   ├── README.md                # Client documentation
│   └── .gitkeep                 # Ensures directory is tracked
│
├── spy_options_downloader/       # Data download utilities
│   ├── downloader.py            # Main download script
│   ├── analyze_greeks.py        # Greeks analysis
│   └── spy_options_parquet/     # Downloaded data (gitignored)
│
├── tests/                        # Test suite
│   ├── test_*.py               # Individual test files
│   └── run_all_tests.py        # Master test runner
│
├── docs/                         # Documentation
│   ├── README.md               # Main documentation
│   └── API_REFERENCE.md        # API documentation
│
├── simple_test_strategy.yaml     # Default strategy configuration
├── start_optionslab.sh          # Launch script
├── requirements.txt             # Python dependencies
└── .gitignore                   # Git ignore rules
```

## Key Components

### 🎯 **optionslab/** - Core System
- Modular architecture with clean separation of concerns
- Full audit trail capability
- AI integration for intelligent analysis
- Comprehensive visualization suite

### 🤖 **AI Integration**
- OpenAI API for natural language analysis
- Strategy compliance checking
- Performance optimization suggestions
- Vision capabilities for chart analysis

### 📊 **Data Management**
- SPY options data from 2020-2025 (parquet format)
- CSV-based trade logging with full metadata
- Memorable naming system for backtests
- Excel-compatible output format

### 🌐 **Web Interface**
- Gradio-based UI on port 7862
- Multi-tab interface:
  - Run Backtest
  - Visualizations
  - AI Assistant
  - AI Viz Analysis
  - Log Manager

## Data Flow

1. ThetaData Terminal → thetadata_client → SPY options data
2. Downloaded data → spy_options_parquet/
3. Backtesting engine → reads parquet files
4. Results → exported to data/backtest_results/

## Quick Start

```bash
# Start the backtesting system
cd optionslab
./start_auditable.sh

# Download new data
cd spy_options_downloader
python downloader.py
```