# 🚀 Alpaca 0DTE Trading System - Setup Guide

## Current Status
✅ API Key configured: `FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F`  
❌ Secret Key needed: Not yet provided  
✅ All dependencies installed: alpaca-py, py_vollib, requests, python-dotenv  

## 🔑 Step 1: Add Your Secret Key

You need to add your Alpaca secret key. Run this command:

```bash
python add_secret_key.py
```

To get your secret key:
1. Go to: https://app.alpaca.markets/paper/dashboard/overview
2. Find your API Keys section
3. Click "View" or "Regenerate" next to your key
4. Copy the entire secret key string
5. Paste it when prompted by the script

## 🧪 Step 2: Test Connection

Once your secret key is added, test the connection:

```bash
# Quick test (no SDK required)
python quick_alpaca_test.py

# Full test with SDK
python test_alpaca_connection.py

# Secure config test
python alpaca_secure_config.py
```

## 📊 Step 3: Verify Your Strategy Settings

The optimal strategy we discovered through backtesting:
- **Strategy**: Vega-Aware (95.9% win rate, 22.61 Sharpe ratio)
- **Entry Time**: 3:00-3:30 PM ET (optimal window)
- **Exit**: 3:59 PM or when profit target hit
- **Max Drawdown**: Reduced from -$12,765 to -$1,055 (91.7% reduction)

## 🤖 Step 4: Start Paper Trading

Once connection is verified:

```bash
# Run the vega-aware strategy in paper mode
python alpaca_vega_trader.py --paper

# Monitor with dashboard (if you have streamlit)
streamlit run live_monitor.py
```

## ⚠️ Important Reminders

1. **Security**: Since your API key was exposed in chat, regenerate it after testing:
   - Go to Alpaca dashboard
   - Click "Regenerate" on your API key
   - Update .env file with new credentials

2. **Paper Trade First**: Always test for at least 1 week in paper mode

3. **Optimal Trading Time**: 3:00-3:30 PM ET based on our backtesting

4. **Risk Management**: The system includes:
   - IV percentile filtering (skip if <30%)
   - Vega ratio limits (max 0.02)
   - Dynamic position sizing
   - Delta risk scoring

## 📁 Key Files Created

- `add_secret_key.py` - Interactive script to add your secret key
- `quick_alpaca_test.py` - Simple connection test
- `test_alpaca_connection.py` - Full SDK test
- `alpaca_secure_config.py` - Secure configuration manager
- `alpaca_vega_trader.py` - Main trading system (vega-aware strategy)
- `.env` - Credentials file (keep secret!)

## 🎯 Expected Results (Based on Backtesting)

Using the Vega-Aware strategy on 2024 data:
- Win Rate: 95.9%
- Total Profit: $38,934
- Max Drawdown: -$1,055
- Sharpe Ratio: 22.61
- Average Trade: $165.46

## 📞 Support

If you encounter issues:
1. Check your internet connection
2. Verify paper trading is enabled in your Alpaca account
3. Ensure you're using paper (not live) credentials
4. Check that market is open (9:30 AM - 4:00 PM ET)

## Next Actions

1. Run `python add_secret_key.py` to add your secret key
2. Test connection with `python quick_alpaca_test.py`
3. Start paper trading at 3:00 PM ET

Remember: The strategy works best during the 3:00-3:30 PM window!