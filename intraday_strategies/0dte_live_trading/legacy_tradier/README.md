# Tradier Options Trading Module

A dedicated module for trading 0DTE SPY options using Tradier's API, which has excellent options support.

## 📊 Why Tradier?

- **Full options support** including multi-leg orders
- **Real-time options data** with Greeks
- **Paper trading** available (sandbox environment)
- **Competitive pricing** for options trades
- **RESTful API** with good documentation

## 🚀 Quick Start

### 1. Get Tradier Account

1. **Sandbox (Paper Trading)**:
   - Sign up at: https://developer.tradier.com/
   - Get free sandbox API token instantly
   - Unlimited paper trading

2. **Live Trading**:
   - Open account at: https://tradier.com/
   - Get production API token
   - Real money trading

### 2. Configure API Credentials

```bash
# Edit the .env file
cd tradier/config
cp .env.example .env
# Add your API token
```

### 3. Test Connection

```bash
# Test sandbox connection
python scripts/test_connection.py

# Test options data
python scripts/test_options.py
```

### 4. Place Test Strangle

```bash
# Place a test strangle
python scripts/place_strangle.py
```

## 📁 Project Structure

```
tradier/
├── config/              # Configuration files
│   ├── .env.example    # Example environment file
│   └── .env            # Your API credentials (create this)
│
├── core/               # Core trading functionality
│   ├── __init__.py
│   ├── client.py       # Tradier API client
│   ├── options.py      # Options-specific functions
│   └── orders.py       # Order management
│
├── scripts/            # Executable scripts
│   ├── test_connection.py     # Test API connection
│   ├── test_options.py        # Test options data
│   ├── place_strangle.py      # Place strangle orders
│   └── monitor_positions.py   # Monitor open positions
│
├── tests/              # Test suite
│   └── test_tradier.py
│
└── README.md           # This file
```

## 🔑 API Endpoints

### Sandbox (Paper Trading)
- Base URL: `https://sandbox.tradier.com/v1/`
- Stream URL: `https://sandbox-stream.tradier.com/v1/`

### Production (Live Trading)
- Base URL: `https://api.tradier.com/v1/`
- Stream URL: `https://stream.tradier.com/v1/`

## 📊 Features

- **Options Chains**: Get full options chains with Greeks
- **Multi-leg Orders**: Build complex options strategies
- **Real-time Quotes**: Stream live options prices
- **Position Management**: Track P&L in real-time
- **Risk Analytics**: Calculate position Greeks

## 🎯 Strangle Strategy Implementation

The module implements our 0DTE strangle strategy:
- Entry: 3:00-3:30 PM ET
- Delta target: 0.15-0.20
- Exit: 3:59 PM or stop/target
- Risk management via Greeks

## 📝 API Documentation

Full Tradier API docs: https://documentation.tradier.com/

## ⚠️ Important Notes

1. **Sandbox Limitations**:
   - Delayed quotes (15 min)
   - Limited historical data
   - Perfect for testing logic

2. **Production Requirements**:
   - Funded account required
   - Real-time data subscription
   - Options approval needed

3. **Rate Limits**:
   - Sandbox: 60 requests/minute
   - Production: 120 requests/minute

---

*Module created for 0DTE SPY options trading*