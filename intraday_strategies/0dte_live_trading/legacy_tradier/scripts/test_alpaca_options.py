#!/usr/bin/env python3
"""
Test Alpaca options data access
"""

import requests
from datetime import datetime, timedelta

# Alpaca credentials
API_KEY = "PKMLDQM62IIIP4975X71"
SECRET_KEY = "84Y8OoZTm34Cp3achHAVgNnbviYSmjCoCTxGft40"

print("Testing Alpaca Options Data Access...")
print("=" * 50)

# Test 1: Get options bars
headers = {
    'APCA-API-KEY-ID': API_KEY,
    'APCA-API-SECRET-KEY': SECRET_KEY,
    'accept': 'application/json'
}

# Try to get options bars for a SPY option
# SPY 638 Call expiring Jan 10, 2025
symbol = "SPY250110C00638000"  # Standard OCC format

params = {
    'symbols': symbol,
    'timeframe': '1Min',
    'start': '2025-01-08T15:00:00Z',
    'end': '2025-01-08T16:00:00Z',
    'limit': 10
}

url = 'https://data.alpaca.markets/v1beta1/options/bars'
print(f"\n1. Testing options bars endpoint:")
print(f"   Symbol: {symbol}")
print(f"   URL: {url}")

response = requests.get(url, headers=headers, params=params)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    if 'bars' in data and symbol in data['bars']:
        bars = data['bars'][symbol]
        print(f"   ✅ Found {len(bars)} bars")
        if bars:
            print(f"   Sample bar: {bars[0]}")
    else:
        print(f"   Response: {data}")
elif response.status_code == 403:
    print("   ❌ Authentication failed or options data not included in plan")
else:
    print(f"   Error: {response.text[:200]}")

# Test 2: Get latest option quote
print(f"\n2. Testing options quotes endpoint:")
url2 = 'https://data.alpaca.markets/v1beta1/options/quotes/latest'
params2 = {'symbols': symbol}

response2 = requests.get(url2, headers=headers, params=params2)
print(f"   Status: {response2.status_code}")

if response2.status_code == 200:
    data = response2.json()
    print(f"   Response: {data}")
elif response2.status_code == 403:
    print("   ❌ Authentication failed or options data not included in plan")

# Test 3: Get option trades
print(f"\n3. Testing options trades endpoint:")
url3 = 'https://data.alpaca.markets/v1beta1/options/trades'
params3 = {
    'symbols': symbol,
    'start': '2025-01-08',
    'end': '2025-01-08',
    'limit': 5
}

response3 = requests.get(url3, headers=headers, params=params3)
print(f"   Status: {response3.status_code}")

if response3.status_code == 200:
    data = response3.json()
    if 'trades' in data:
        print(f"   Response: {data}")
elif response3.status_code == 403:
    print("   ❌ Authentication failed or options data not included in plan")

print("\n" + "=" * 50)
print("SUMMARY:")
print("-" * 50)

if any(r.status_code == 200 for r in [response, response2, response3]):
    print("✅ Alpaca options data IS accessible!")
    print("   Your account has access to options data")
else:
    print("❌ Alpaca options data NOT accessible")
    print("   Likely reasons:")
    print("   1. Paper trading account may not include options data")
    print("   2. Need Alpaca Unlimited plan ($99/month)")
    print("   3. Or pay-as-you-go for options data")

print("\nFor the VegaAware strategy, you would need:")
print("• SPY options bars (1-minute during 3:00-4:00 PM)")
print("• Options quotes for strangle positions")
print("• Greeks would need to be calculated separately")