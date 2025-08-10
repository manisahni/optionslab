# 0DTE SPY Options Trading Dashboard

## 🎯 Overview
Professional trading dashboard for zero-day-to-expiration (0DTE) SPY options implementing a **93.7% win rate** strangle strategy with real-time Greeks monitoring and systematic entry criteria.

## ✨ Features

### Dashboard (4 Tabs)
1. **📊 Trading View** - Real-time charts with buy/sell signals
2. **✅ Strategy Checklist** - 13-point criteria evaluation
3. **📈 Risk Analysis** - Position and Greeks monitoring
4. **📚 Strategy Guide** - Trading rules and education

### Capabilities
- **Pre-market data** from 4:00 AM ET
- **Real-time updates** every 10 seconds
- **Greeks calculations** (Delta, Gamma, Theta, Vega)
- **Trade recommendations** based on strategy score
- **Historical analysis** with 21 days of data

## 📈 Performance
- **Win Rate**: 93.7% - 95.9%
- **Sharpe Ratio**: 22.61
- **Max Drawdown**: 0.70%
- **Strategy**: Short strangle at 3:00 PM ET

## 🚀 Quick Start

```bash
# 1. Navigate to project
cd /Users/nish_macbook/0dte

# 2. Start dashboard
./start_dashboard.sh

# 3. Open browser
# Go to: http://localhost:7870
```

## 🛠️ Setup

### Requirements
- Python 3.9+
- Tradier API account (sandbox or production)
- 4GB RAM minimum

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API
cp .env.example .env
# Add your Tradier API key to .env
```

## 📝 Strategy Rules

### Entry Criteria (3:00 PM ET)
- Time window: 2:30-3:30 PM (optimal: 3:00 PM)
- Delta target: 0.15-0.20 for both legs
- Minimum premium: $0.30 per side
- Vega limit: < 2.0
- IV environment: < 80%

### Exit Rules
- Let expire (most common)
- Stop loss at 2x premium collected
- Exit by 3:55 PM to avoid final minutes

## 📁 Project Structure
```
0dte/
├── tradier/              # Main trading system
│   ├── dashboard/       # Web dashboard
│   ├── core/            # Greeks & calculations
│   ├── scripts/         # Utilities
│   └── database/        # Market data cache
├── docs/                 # Documentation
├── scripts/              # Helper scripts
└── start_dashboard.sh    # Main launcher
```

## 🔧 Troubleshooting

### Dashboard not showing today's data?
```bash
python tradier/scripts/refresh_today_data.py
```

### Port already in use?
```bash
lsof -i :7870
kill -9 <PID>
```

### Missing dependencies?
```bash
pip install --upgrade -r requirements.txt
```

## ⚠️ Disclaimer
**For educational purposes only.** Options trading involves substantial risk. Past performance does not guarantee future results. The 93.7% win rate was achieved in backtesting and may not reflect live trading results.

## 📚 Documentation
- [Strategy Guide](docs/STRATEGY_CHECKLIST_FEATURE.md)
- [Dashboard Tabs](docs/DASHBOARD_TABS_UPDATE.md)
- [Greeks Explanation](docs/THETA_VALUES_EXPLANATION.md)
- [Live Data Setup](docs/LIVE_DATA_FIX.md)