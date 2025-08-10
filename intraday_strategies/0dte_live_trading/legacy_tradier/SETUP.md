# Tradier Setup Guide

## 🚀 Quick Setup

### Step 1: Get Your API Token

Since you have a Tradier Brokerage account, you have **TWO** options:

#### Option A: Production API (Real Trading)
1. Log into your Tradier account
2. Go to API settings
3. Get your production API token
4. This token works with ALL your accounts
5. This token does NOT expire

#### Option B: Sandbox API (Paper Trading) 
1. Your account includes a sandbox with $100,000 paper money
2. Get sandbox token from your account dashboard
3. 15-minute delayed data (perfect for testing)

### Step 2: Add Token to Config

Edit `/tradier/config/.env`:

```bash
# For SANDBOX (Paper Trading) - Recommended for testing
TRADIER_SANDBOX_TOKEN=your_sandbox_token_here
TRADIER_ENV=sandbox

# OR for PRODUCTION (Real Trading) - Use with caution
TRADIER_PROD_TOKEN=your_production_token_here
TRADIER_ENV=production
```

### Step 3: Test Connection

```bash
cd /Users/nish_macbook/0dte/tradier
python scripts/test_connection.py
```

### Step 4: Test Options Trading

```bash
# Check available 0DTE options
python scripts/test_options.py

# Place a test strangle (sandbox)
python scripts/place_strangle.py
```

## 📊 Features Available

### With Sandbox (Paper Trading):
- ✅ $100,000 paper money
- ✅ Full options trading
- ✅ Multi-leg orders (strangles)
- ⚠️ 15-minute delayed data
- ❌ No streaming data

### With Production (Live):
- ✅ Real-time market data
- ✅ Full options trading
- ✅ Streaming quotes
- ✅ Account activity
- ⚠️ Real money at risk

## 🎯 For 0DTE Strangle Testing

**Recommendation**: Start with SANDBOX
- Test the strangle logic safely
- Verify order placement works
- Monitor positions without risk
- Switch to production when ready

## 🔗 Important Links

- Tradier Dashboard: https://dash.tradier.com/
- API Documentation: https://documentation.tradier.com/
- Sandbox Guide: https://documentation.tradier.com/brokerage-api/overview/sandbox

---

**Note**: The 15-minute delay in sandbox is actually GOOD for testing because it prevents overreacting to real-time moves while testing the logic.