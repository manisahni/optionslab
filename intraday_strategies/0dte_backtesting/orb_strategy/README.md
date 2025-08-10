# 0DTE Opening Range Breakout (ORB) Strategy

A dedicated section for developing, backtesting, and trading Opening Range Breakout strategies with 0DTE options.

## 📊 Strategy Overview

The ORB strategy trades breakouts from the opening range using credit spreads on 0DTE SPY options.

### Backtested Performance (from research):
- **60-minute ORB**: 88.8% win rate, $30,708 profit, -$3,231 max drawdown ✅
- **30-minute ORB**: 82.6% win rate, $19,555 profit, -$8,306 max drawdown
- **15-minute ORB**: 78.1% win rate, $19,053 profit, -$7,602 max drawdown

## 🎯 Strategy Rules

### Entry Signals:
- **Bullish**: Price breaks above opening range high → Short Put Spread
- **Bearish**: Price breaks below opening range low → Short Call Spread

### Position Details:
- **Spread Width**: $15
- **Short Strike**: $0.01 outside opening range
- **Max Trades**: 1 per day (first breakout only)
- **Min Range**: 0.2% of SPY price

### Exit Rules:
- Time exit at 3:59 PM
- Stop loss at 2x credit received
- Profit target at 80% of max profit

## 📁 Project Structure

```
orb_strategy/
├── core/                  # Core components
│   ├── orb_calculator.py # Opening range calculations
│   ├── breakout_detector.py # Breakout detection
│   ├── position_builder.py  # Credit spread construction
│   └── orb_metrics.py    # Performance metrics
│
├── strategies/           # ORB variations
│   ├── orb_15min.py     # 15-minute ORB
│   ├── orb_30min.py     # 30-minute ORB
│   ├── orb_60min.py     # 60-minute ORB (best)
│   └── orb_adaptive.py  # Adaptive timeframe
│
├── backtesting/         # Backtesting engine
│   ├── orb_backtester.py
│   ├── performance_analyzer.py
│   └── optimization.py
│
├── live_trading/        # Live execution
│   ├── orb_trader.py
│   ├── alpaca_executor.py
│   └── risk_manager.py
│
├── dashboards/          # Visualization
│   └── orb_dashboard.py
│
└── config/             # Configuration
    └── orb_settings.yaml
```

## 🚀 Quick Start

### 1. Run Backtest
```bash
python backtesting/run_backtest.py --strategy 60min --start 2024-01-01
```

### 2. View Dashboard
```bash
python dashboards/orb_dashboard.py
```

### 3. Paper Trade
```bash
python live_trading/orb_trader.py --paper --strategy 60min
```

### 4. Optimize Parameters
```bash
python backtesting/optimization.py --timeframes 15,30,60 --optimize
```

## 📈 Usage Examples

### Basic Backtest:
```python
from backtesting.orb_backtester import ORBBacktester

backtester = ORBBacktester()
results = backtester.run_backtest(
    strategy='60min',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
print(f"Win Rate: {results['win_rate']:.1%}")
print(f"Total P/L: ${results['total_pnl']:,.0f}")
```

### Live Trading:
```python
from live_trading.orb_trader import ORBLiveTrader

trader = ORBLiveTrader(strategy='60min', paper=True)
trader.run()  # Runs continuously during market hours
```

## 🔧 Configuration

Edit `config/orb_settings.yaml` to adjust:
- Opening range timeframes
- Credit spread widths
- Risk parameters
- Position sizing

## 📊 Performance Metrics

The system tracks:
- Win rate
- Total P/L
- Max drawdown
- Profit factor
- Average P/L per trade
- Sharpe ratio
- Time in market

## ⚠️ Risk Management

- Maximum 1 trade per day
- Position size: 2% of account
- Stop loss: 200% of credit received
- Daily loss limit: 5% of account
- Automatic exit at 3:59 PM

## 🔄 Development Status

- [x] Core structure created
- [ ] ORB calculator implementation
- [ ] Backtest engine
- [ ] Live trading integration
- [ ] Performance dashboard
- [ ] Parameter optimization

## 📝 Notes

This is a dedicated research and trading section for ORB strategies, separate from the main vega strangle strategy. It's designed for experimentation and can be integrated with the main system once proven profitable.