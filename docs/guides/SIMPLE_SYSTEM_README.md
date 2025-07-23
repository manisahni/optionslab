# OptionsLab Simplified System

## Overview

A dramatically simplified 2-component architecture for options backtesting with AI analysis.

## Architecture

1. **Backtest Runner** (`run_backtest_simple.py`) - Standalone Python script
   - Runs backtests independently 
   - Outputs comprehensive CSV with results + all data
   - No UI, no servers, just computation

2. **Results Viewer** (`view_results_simple.py`) - Streamlit app  
   - Displays backtest results from CSV files
   - AI chat interface with full backtest context
   - Clean separation from backtest execution

## Usage

### 1. Run a Backtest

```bash
python run_backtest_simple.py --strategy long_call --start 2025-01-01 --end 2025-06-30
```

Available strategies:
- `long_call` - Buy call options
- `long_put` - Buy put options  
- `long_straddle` - Buy call and put at same strike
- `covered_call` - Own stock + sell calls
- `cash_secured_put` - Sell puts with cash collateral
- `iron_condor` - Four-leg options spread

Output: `<backtest_id>_<memorable_name>_<timestamp>.csv`

### 2. View Results & AI Analysis

```bash
# Set your Gemini API key
export GEMINI_API_KEY='your-api-key-here'

# Start the viewer
streamlit run view_results_simple.py
```

Features:
- 📈 Performance metrics and equity curve
- 📋 Detailed trade logs
- 🤖 AI chat analysis with full code context
- 📝 View strategy and backtester code

## Key Benefits

✅ **Simple** - Just 2 files, no complex services  
✅ **Robust** - No memory issues or crashes  
✅ **AI-Powered** - Full code context for deep analysis  
✅ **Fast** - Direct execution, no API overhead  
✅ **Debuggable** - Clear separation of concerns  

## AI Analysis

The AI has access to:
- Complete backtest results (trades, metrics, equity curve)
- Full source code (strategy, backtester, portfolio manager)
- All parameters and configuration

This enables deep insights like:
- Why the strategy performed as it did
- Code improvement suggestions
- Risk analysis based on actual implementation
- Parameter optimization recommendations

## Requirements

```bash
pip install streamlit pandas plotly google-generativeai
```

## Get Gemini API Key

Visit: https://makersuite.google.com/app/apikey

## No More Complexity!

❌ No API servers  
❌ No port conflicts  
❌ No service orchestration  
❌ No auto-refresh loops  
❌ No memory leaks  

Just run backtests and analyze results with AI!