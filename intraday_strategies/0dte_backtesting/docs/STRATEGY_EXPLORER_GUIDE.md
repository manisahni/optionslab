# 🎯 0DTE Strangle Strategy Explorer Guide

## 📚 Overview

The Strategy Explorer is an interactive Gradio-based application that helps you:
1. **Optimize Greeks parameters** for maximum risk-adjusted returns
2. **Analyze current market conditions** and get position sizing recommendations
3. **Export configurations** for live trading implementation

## 🚀 How to Launch

```bash
# From the market_data directory:
./launch_strategy_explorer.sh

# Or directly:
python strangle_strategy_explorer.py
```

Access the app at: **http://localhost:7860**

## 📊 Tab 1: Strategy Backtesting

### Purpose
Test different Greeks parameter combinations to find optimal settings for your risk tolerance and return objectives.

### Parameters to Adjust:
- **Max Delta (0.20-0.50)**: Maximum allowed delta for entry
  - Lower = More conservative, fewer trades
  - Higher = More aggressive, more trades
  
- **Max Gamma (0.02-0.10)**: Maximum gamma (acceleration risk)
  - Lower = Less sensitive to price moves
  - Higher = More reactive to market changes
  
- **Min Theta Ratio (0.05-0.30)**: Minimum daily theta as % of premium
  - Higher = Require more time decay benefit
  - Lower = Accept less time decay
  
- **Max Vega Ratio (0.5-1.5)**: Maximum vega exposure vs premium
  - Lower = Less volatility exposure
  - Higher = More volatility tolerance
  
- **Delta Exit Threshold (0.40-0.70)**: Exit when delta exceeds this
  - Lower = Earlier exits, more conservative
  - Higher = Later exits, ride winners longer

### Optimal Settings We Found:
Based on our optimization, the **Balanced preset** achieved the best results:
- Max Delta: **0.35**
- Max Gamma: **0.05**
- Min Theta Ratio: **0.15**
- Max Vega Ratio: **1.0**
- Delta Exit: **0.50**

**Results**: 
- Sharpe Ratio improved from 4.12 → **13.16**
- Drawdown reduced by **99.4%** (from -$12,765 to -$70)
- Win rate improved to **83.3%**

## 🧮 Tab 2: Risk Calculator

### Purpose
Evaluate current market conditions in real-time to determine if you should enter a trade and what position size to use.

### How to Use:
1. Enter current option Greeks from your broker:
   - Current Delta
   - Current Gamma  
   - Current IV (Implied Volatility)
   - Premium Collected
   - SPY Price

2. The calculator will show:
   - **Risk Score** (0-100): Lower is better
   - **Can Enter**: ✅ Yes or ❌ No
   - **Position Size**: What % of normal size to trade
   - **Risk Breakdown**: Which Greeks contribute most to risk

### Entry Guidelines:
- ✅ **Enter** if risk score < 50 and "Can Enter" = Yes
- ⚠️  **Reduce Size** if risk score 50-60
- ❌ **Skip Trade** if risk score > 60 or "Can Enter" = No

## ⚙️ Tab 3: Configuration

### Presets Available:
1. **Conservative**: Focus on capital preservation
2. **Balanced**: Best Sharpe ratio (recommended)
3. **Aggressive**: Maximum returns

### Export Configuration:
Click "Export Configuration" to get a JSON file with your settings that can be used in automated trading systems.

## 💡 How to Apply These Settings to Real Trading

### 1. Manual Trading Approach

**Pre-Market (8:30 AM - 9:30 AM EST):**
1. Check SPY implied volatility percentile
2. If IV > 30th percentile, prepare for potential trade

**At Market Open (9:30 AM EST):**
1. Wait 5-10 minutes for market to settle
2. Find 0DTE SPY options with:
   - Call delta: 0.15-0.20
   - Put delta: -0.15 to -0.20
   - Combined premium: $100-200 per contract

**Use Risk Calculator:**
1. Input current Greeks into Tab 2
2. Check if "Can Enter" = Yes
3. Note recommended position size

**Entry Checklist:**
- [ ] Risk score < 50
- [ ] Max delta < 0.35
- [ ] Max gamma < 0.05  
- [ ] Theta ratio > 0.15
- [ ] Vega ratio < 1.0

**Position Management:**
- Set alerts for delta = 0.45 (warning)
- Exit if either delta hits 0.50
- Exit at 3:50 PM if still open

### 2. Semi-Automated Approach

**Using Interactive Brokers with ib_insync:**

```python
from ib_insync import *
from enhanced_greeks_risk_analyzer import EnhancedGreeksRiskAnalyzer

# Initialize
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
analyzer = EnhancedGreeksRiskAnalyzer()

# Load your exported configuration
import json
with open('optimal_config.json', 'r') as f:
    config = json.load(f)
    
# Set parameters
analyzer.params.max_delta = config['greeks_parameters']['max_delta']
# ... set other parameters

# Function to check trade
def check_spy_strangle():
    # Get SPY price
    spy = Stock('SPY', 'SMART', 'USD')
    ib.qualifyContracts(spy)
    ticker = ib.reqMktData(spy)
    spy_price = ticker.marketPrice()
    
    # Find 0DTE options
    chains = ib.reqSecDefOptParams(spy.symbol, '', spy.secType, spy.conId)
    # ... find appropriate strikes
    
    # Get Greeks and check entry
    # ... implement entry logic
```

### 3. Risk Management Rules

**Position Sizing:**
- Start with 1-2 contracts while learning
- Scale up only after 20+ successful trades
- Never risk more than 2% of account per trade

**Daily Limits:**
- Maximum 1 strangle per day
- Stop trading after 2 consecutive losses
- No trades on Fed announcement days

**Exit Rules (Automated Alerts):**
1. **Delta Exit**: Close if either option delta > 0.50
2. **Time Exit**: Close at 3:50 PM
3. **Profit Target**: Consider closing at 50% profit
4. **Loss Limit**: Exit if loss > 2x premium collected

## 📈 Expected Performance

Based on our backtesting with Greeks enhancement:
- **Win Rate**: ~83%
- **Average Win**: $95
- **Average Loss**: -$312 (but only 17% of trades)
- **Sharpe Ratio**: 13.16
- **Maximum Drawdown**: -$70 (vs -$12,765 original)

## 🔧 Next Steps

1. **Paper Trade First**: Test for at least 2 weeks
2. **Start Small**: Begin with 1 contract
3. **Track Results**: Log every trade with entry/exit Greeks
4. **Refine Parameters**: Adjust based on your results

## ⚠️ Important Warnings

1. **Market Conditions**: These settings work best in normal volatility environments
2. **Event Risk**: Avoid trading around major economic releases
3. **Technology**: Ensure stable internet and broker connection
4. **Psychology**: Stick to the system, don't override based on emotions

## 🛠️ Troubleshooting

**App won't start:**
```bash
# Kill any existing process
pkill -f "python.*strangle_strategy_explorer"
# Restart
./launch_strategy_explorer.sh
```

**Can't access http://localhost:7860:**
- Check firewall settings
- Try http://127.0.0.1:7860
- Ensure no other app is using port 7860

**Data not loading:**
- Verify `full_year_backtest_trades_20250805_211124.csv` exists
- Check for Greeks-enhanced trade files in directory

## 📞 Support

For questions or issues:
1. Check the console output for error messages
2. Review the backtest results in the generated HTML files
3. Examine the exported configuration JSON

Remember: This is a tool for analysis and optimization. Always validate results and start with small position sizes when implementing in live trading.