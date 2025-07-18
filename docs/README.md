# OptionsLab - Options Backtesting System

Simple, fast options backtesting with SPY data using Gradio interface.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the backend API server
python backend.py

# In another terminal, start the Gradio app
./run_gradio.sh
```

## Features

- **Simple Web Interface**: Clean Gradio UI for easy backtesting
- **Fast Backend**: Efficient FastAPI-based backtesting engine
- **Strategies**: Long call and long put options strategies
- **Real-time Results**: Interactive charts and performance metrics
- **Trade Analysis**: Detailed trade logs and performance breakdown

## Project Structure

```
├── simple_gradio_app.py   # Main Gradio web interface
├── run_gradio.sh          # App launcher script
├── backend.py             # FastAPI backend server
├── backtest_engine.py     # Core backtesting functions
├── requirements.txt       # Dependencies
├── config/                # Strategy configurations
├── spy_options_downloader/
│   └── spy_options_parquet/  # SPY options data
└── results/               # Output files
```

## Usage

1. **Start the Backend**: `python backend.py`
2. **Launch the App**: `./run_gradio.sh`
3. **Open Browser**: Navigate to `http://localhost:7860`
4. **Configure Backtest**:
   - Select strategy (long_call or long_put)
   - Set date range
   - Enter initial capital
5. **Run Backtest**: Click "Run Backtest" to see results

## Available Strategies

- **long_call**: Buy call options on SPY
- **long_put**: Buy put options on SPY

## Performance Metrics

- Total Return
- Sharpe Ratio
- Maximum Drawdown
- Win Rate
- Total Trades
- Equity Curve Visualization
- Trade Log Analysis

## Example Output

The app displays:
- **Performance Summary**: Key metrics at a glance
- **Equity Curve**: Interactive portfolio value chart
- **Trade Table**: Recent trades with entry/exit details
- **AI Analysis**: Optional AI-powered insights (when configured)