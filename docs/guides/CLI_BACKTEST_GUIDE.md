# 🎯 CLI Backtest System with AI Analysis

## Overview

A complete command-line backtesting system with:
- 📊 **Charts** - Equity curve, drawdown, monthly returns
- 📈 **Tables** - Performance metrics and trade logs
- 🤖 **AI Analysis** - Automatic insights from Gemini
- 💬 **Interactive Chat** - Ask questions about results

## Basic Usage

### 1. Simple Backtest
```bash
python run_backtest_cli.py --strategy long_call --start 2025-01-01 --end 2025-06-30
```

### 2. With Plots Saved
```bash
python run_backtest_cli.py --strategy long_call --save-plots
```

### 3. With AI Analysis
```bash
export GEMINI_API_KEY='your-key-here'
python run_backtest_cli.py --strategy long_call
```

### 4. With Interactive Chat
```bash
python run_backtest_cli.py --strategy long_call --chat
```

### 5. Save Everything
```bash
python run_backtest_cli.py --strategy long_call --save-plots --save-json --chat
```

## Available Options

### Strategies
- `long_call` - Buy call options
- `long_put` - Buy put options
- `long_straddle` - Buy both call and put
- `covered_call` - Own stock + sell calls
- `cash_secured_put` - Sell puts with cash
- `iron_condor` - 4-leg spread

### Parameters
- `--start YYYY-MM-DD` - Start date (default: 2025-01-01)
- `--end YYYY-MM-DD` - End date (default: 2025-06-30)
- `--capital AMOUNT` - Initial capital (default: 100000)
- `--save-plots` - Save charts to PNG file
- `--save-json` - Save full results to JSON
- `--no-ai` - Disable AI analysis
- `--chat` - Enable interactive AI chat

## Output

### 1. Performance Table
```
📈 PERFORMANCE METRICS
==================================================
| Metric        | Value   |
|===============|=========|
| Total Return  | -17.70% |
| Sharpe Ratio  | -3.33   |
| Max Drawdown  | 21.72%  |
...
```

### 2. Trade Log
```
📋 RECENT TRADES (Last 10)
==================================================
| Entry   | Exit   | Type | Strike | Qty | P&L    |
|=========|========|======|========|=====|========|
| 2025-01 | 2025-02| C    | $580   | 10  | -$1,234|
...
```

### 3. Charts (3 panels)
- **Equity Curve** - Portfolio value over time
- **Drawdown** - Peak-to-trough declines
- **Monthly Returns** - Bar chart of monthly performance

### 4. AI Analysis
```
🤖 AI ANALYSIS
==================================================
This backtest shows poor performance with a -17.70% return...
Key weaknesses: High drawdown, negative Sharpe ratio...
Recommendations: 1) Adjust delta targets, 2) Tighten stops...
```

### 5. Interactive Chat
```
💬 AI CHAT MODE
==================================================
🤔 You: Why did the strategy lose money in February?
🤖 AI: Looking at the trades in February, the main issue was...

🤔 You: What if I changed the delta to 0.4?
🤖 AI: Increasing delta to 0.4 would select more in-the-money options...
```

## Examples

### Complete Analysis Session
```bash
# Set API key
export GEMINI_API_KEY='your-key-here'

# Run full analysis with chat
python run_backtest_cli.py \
  --strategy long_call \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --capital 50000 \
  --save-plots \
  --save-json \
  --chat
```

### Batch Analysis
```bash
# Test multiple strategies
for strategy in long_call long_put covered_call; do
  python run_backtest_cli.py --strategy $strategy --save-plots --save-json
done
```

## Benefits

✅ **No Web Frameworks** - Pure CLI, always works  
✅ **Complete Analysis** - Charts + metrics + AI  
✅ **Interactive** - Chat with AI about results  
✅ **Scriptable** - Easy to automate and batch  
✅ **Fast** - Direct execution, no overhead  

## Troubleshooting

1. **No AI response**: Check `GEMINI_API_KEY` is set
2. **Import errors**: Run `pip install matplotlib tabulate google-generativeai`
3. **No data**: Ensure SPY options data is downloaded

This is the simplest, most reliable way to run backtests with AI analysis!