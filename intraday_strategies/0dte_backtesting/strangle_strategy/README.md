# 0DTE Strangle Strategy

A comprehensive system for backtesting and trading short strangles on SPY 0DTE options with advanced Greek-aware risk management.

## 📊 Strategy Overview

The strangle strategy sells both out-of-the-money puts and calls to collect premium, with sophisticated entry/exit rules based on Greeks and market conditions.

### Key Features
- **Vega-Aware Risk Management**: Dynamic position sizing based on vega exposure
- **Greek Corrections**: Enhanced delta calculations for accurate strike selection
- **Optimal Entry Window**: 3:00-3:30 PM ET based on extensive backtesting
- **Transparent Backtesting**: Full trade-level transparency and auditability

### Performance Metrics (2024 Backtesting)
- **Win Rate**: 95.9%
- **Sharpe Ratio**: 22.61
- **Max Drawdown**: -$1,055 (91.7% reduction from unfiltered)
- **Average Trade**: $165.46
- **Annual Return**: ~40% on margin requirements

## 📁 Project Structure

```
strangle_strategy/
├── backtesting/              # Backtesting engines
│   ├── transparent_strangle_backtester.py    # Full transparency backtester
│   ├── enhanced_strangle_backtester.py       # Enhanced with execution modeling
│   ├── strangle_optimizer_visual.py          # Visual parameter optimization
│   ├── simple_strangle_viz.py                # Simple visualization tool
│   └── strangle_backtest_tool.py             # CLI backtesting tool
│
├── analysis/                 # Analysis tools
│   ├── enhanced_strangle_analysis.py         # Comprehensive analysis
│   ├── strangle_band_analysis.py             # Strike band analysis
│   ├── strangle_comparison_demo.py           # Strategy comparison
│   └── run_strangle_analysis.py              # Analysis runner
│
├── dashboards/              # Interactive dashboards
│   ├── comprehensive_strangle_dashboard.py   # Full-featured dashboard
│   ├── educational_strangle_dashboard.py     # Educational interface
│   └── start_strangle_dashboard.sh           # Dashboard launcher
│
├── reports/                 # Generated reports and outputs
│   ├── *.pkl               # Analysis results (pickle format)
│   ├── *.csv               # Trade logs and metrics
│   ├── *.html              # Visual reports
│   └── *.txt               # Text reports
│
└── README.md               # This file
```

## 🚀 Quick Start

### 1. Run a Simple Backtest

```bash
cd /Users/nish_macbook/0dte
python strangle_strategy/backtesting/simple_strangle_viz.py
```

### 2. Launch Interactive Dashboard

```bash
# Educational dashboard with explanations
./strangle_strategy/dashboards/start_strangle_dashboard.sh

# Or comprehensive analysis dashboard
python strangle_strategy/dashboards/comprehensive_strangle_dashboard.py
```

### 3. Run Parameter Optimization

```bash
python strangle_strategy/backtesting/strangle_optimizer_visual.py
```

## 📈 Strategy Rules

### Entry Criteria
- **Time**: 3:00-3:30 PM ET (last 60-90 minutes of trading)
- **Delta Target**: 0.15-0.20 for both puts and calls
- **Minimum Premium**: $0.30 per side
- **Vega Filter**: Total vega < 2.0 (risk management)

### Position Management
- **Max Loss**: 2x collected premium (stop loss)
- **Profit Target**: 80% of max profit (optional)
- **Time Exit**: 3:59 PM ET (1 minute before close)
- **Position Sizing**: Based on vega-adjusted risk

### Risk Filters
1. **Vega Ratio Filter**: Skip high vega environments
2. **Premium Quality**: Minimum premium requirements
3. **Greek Validation**: Ensure Greeks are within acceptable ranges
4. **Time Decay**: Maximize theta collection in final hour

## 🔧 Advanced Features

### 1. Transparent Backtesting
```python
from strangle_strategy.backtesting.transparent_strangle_backtester import TransparentStrangleBacktester

backtester = TransparentStrangleBacktester()
results = backtester.backtest_period("2024-01-01", "2024-12-31")
backtester.generate_report()
```

### 2. Enhanced Execution Modeling
```python
from strangle_strategy.backtesting.enhanced_strangle_backtester import EnhancedStrangleBacktester, ExecutionConfig

config = ExecutionConfig(mode="conservative", use_corrected_deltas=True)
backtester = EnhancedStrangleBacktester(exec_config=config)
results = backtester.backtest_period("2024-01-01", "2024-12-31")
```

### 3. Parameter Optimization
```python
from strangle_strategy.backtesting.strangle_optimizer_visual import StrangleOptimizer

optimizer = StrangleOptimizer()
best_params = optimizer.optimize(
    delta_range=(0.10, 0.25),
    entry_times=["15:00", "15:15", "15:30"],
    vega_limits=[1.5, 2.0, 2.5]
)
```

## 📊 Performance Analysis

### Key Metrics to Monitor
- **Win Rate**: Should be > 90% for this strategy
- **Average Winner/Loser Ratio**: Target 1:8 or better
- **Max Consecutive Losses**: Usually < 3
- **Sharpe Ratio**: Target > 2.0
- **Calmar Ratio**: Return/Max Drawdown > 3.0

### Market Conditions
- **Best Performance**: Low to moderate volatility days
- **Avoid**: Major economic announcements, FOMC days
- **Optimal**: Regular trading days with normal volume

## 🛠️ Configuration

### Adjustable Parameters
```python
# In backtesting scripts
DELTA_TARGET = 0.15      # Target delta for strikes
ENTRY_TIME = "15:00"     # Entry time (3:00 PM ET)
EXIT_TIME = "15:59"      # Exit time (3:59 PM ET)
MAX_VEGA = 2.0          # Maximum total vega
MIN_PREMIUM = 0.30      # Minimum premium per side
STOP_LOSS_MULT = 2.0    # Stop loss multiplier
```

## 📚 Educational Resources

### Understanding the Greeks
- **Delta**: Probability of expiring in-the-money
- **Gamma**: Rate of delta change (acceleration risk)
- **Theta**: Time decay (our profit engine)
- **Vega**: Volatility sensitivity (primary risk)
- **Rho**: Interest rate sensitivity (minimal for 0DTE)

### Risk Management
1. **Position Sizing**: Never risk more than 2% per trade
2. **Vega Limits**: Keep total vega under control
3. **Time Stops**: Always exit before close
4. **Correlation**: Reduce size in high correlation environments

## 🔍 Troubleshooting

### Common Issues
1. **Import Errors**: Ensure you're running from the `/Users/nish_macbook/0dte` directory
2. **Data Not Found**: Check that options data is downloaded in `/data/options/`
3. **Dashboard Won't Start**: Verify port 7863 is available

## 📈 Next Steps

1. **Paper Trading**: Test with Alpaca paper account
2. **Live Monitoring**: Set up real-time Greek monitoring
3. **Automation**: Implement automated entry/exit
4. **Scaling**: Adjust position sizing based on account size

## 📝 Notes

- All times are in Eastern Time (ET)
- Backtesting uses actual tick-level options data
- Greek calculations use Black-Scholes model
- Execution modeling accounts for bid-ask spreads

## 🤝 Contributing

To add new features or strategies:
1. Create new files in appropriate subdirectory
2. Follow existing naming conventions
3. Include comprehensive docstrings
4. Add unit tests where applicable
5. Update this README with new features

---

*Last Updated: January 2025*