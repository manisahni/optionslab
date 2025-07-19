# Project Structure Overview

## Directory Organization

```
thetadata-api/
│
├── optionslab/                    # Core backtesting system
│   ├── auditable_backtest.py     # Main backtesting engine
│   ├── auditable_gradio_app.py   # Web interface
│   ├── start_auditable.sh        # Launch script
│   └── README.md                 # Backtesting documentation
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
├── strategies/                   # Strategy YAML files
│   ├── simple_test_strategy.yaml
│   ├── advanced_test_strategy.yaml
│   └── ...
│
└── data/                        # Data storage (gitignored)
    └── backtest_results/        # Export outputs
```

## Important Notes

1. **thetadata_client/** - DO NOT DELETE. Contains critical API integration code.
2. **optionslab/** - Core backtesting system with audit trail capability
3. **data/** - All data files are gitignored for security and size
4. **strategies/** - YAML configuration files for different trading strategies

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