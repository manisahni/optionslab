# 0DTE Live Trading System

## Directory Structure

### `/alpaca_vegaware/` - Active Trading System (Alpaca-based)
The main production trading system using Alpaca for both data and execution.

- **vegaware_trader.py** - Main VegaAware strategy implementation
  - 13-point entry criteria with 80% threshold
  - 0.15 delta strike selection
  - Greeks-based position management
  - Stop loss (2x credit) and profit target (50%)

- **monitor.py** - Real-time position monitoring
  - Live P&L tracking
  - Position Greeks display
  - Order status updates

- **core/** - Core components
  - `client.py` - Alpaca API wrapper
  - `greeks.py` - Black-Scholes Greeks calculator
  - `db.py` - Database operations

- **test_connection.py** - API connectivity test
- **test_strategy.py** - Strategy criteria validation

### `/legacy_tradier/` - Legacy System (Archived)
Previous Tradier-based implementation, kept for reference only.

## Quick Start

```bash
# Start the trading system
./start_alpaca_vegaware.sh

# Options:
# 1) Test Connection - Verify API access
# 2) Test Strategy - Check entry criteria
# 3) Live Trading - Start real money trading
# 4) Monitor Only - View positions
# 5) Paper Trading - Test mode
```

## VegaAware Strategy

### Entry Window
- **Time**: 2:30 PM - 3:30 PM ET
- **Optimal**: 3:00 PM ET
- **Exit**: By 3:55 PM ET

### Entry Criteria (80% required)
1. Market open
2. In time window
3. SPY spread < $0.02
4. Find 0.15 delta strikes
5. Premium > $0.30
6. Vega < 2.0
7. Delta balanced (< 0.10)
8. Account has buying power
9. No existing positions
10. Not Friday
11. IV percentile check
12. Risk/reward > 2:1
13. No pending events

### Position Management
- **Stop Loss**: -2x credit received
- **Profit Target**: 50% of credit
- **Strike Breach**: Exit if SPY touches strike
- **Vega Explosion**: Exit if vega > 3.0
- **Time Exit**: Close by 3:55 PM ET

## Configuration

### API Keys
Located in `/alpaca_vegaware/.env`:
- Alpaca paper/live credentials
- Environment selection

### Database
SQLite database at `tradier/data/trading.db`:
- Options data
- Trade history
- Performance metrics

## Historical Win Rate
- **Target**: 93.7% (from original research)
- **Achieved**: Testing in progress

## Risk Warning
⚠️ **LIVE TRADING RISK**: This system trades real money when in live mode. Always test thoroughly with paper trading first.