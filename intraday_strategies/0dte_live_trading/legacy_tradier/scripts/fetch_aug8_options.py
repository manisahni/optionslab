#!/usr/bin/env python3
"""
Fetch Aug 8 options data from Alpaca for VegaAware strategy
"""

import requests
from datetime import datetime

# Alpaca credentials
API_KEY = "PKMLDQM62IIIP4975X71"
SECRET_KEY = "84Y8OoZTm34Cp3achHAVgNnbviYSmjCoCTxGft40"

headers = {
    'APCA-API-KEY-ID': API_KEY,
    'APCA-API-SECRET-KEY': SECRET_KEY,
    'accept': 'application/json'
}

print("Fetching Aug 8 Options Data for VegaAware Strategy")
print("=" * 60)

# For Aug 8, 2025 0DTE options (SPY at $635.75 at 3:00 PM)
# We need: Call $638, Put $634
contracts = {
    'call': 'SPY250808C00638000',  # SPY Aug 8 2025 $638 Call
    'put': 'SPY250808P00634000'     # SPY Aug 8 2025 $634 Put
}

# Fetch options bars for 3:00-4:00 PM window
for option_type, symbol in contracts.items():
    print(f"\n{option_type.upper()}: {symbol}")
    print("-" * 40)
    
    # Get 1-minute bars
    params = {
        'symbols': symbol,
        'timeframe': '1Min',
        'start': '2025-08-08T15:00:00Z',  # 3:00 PM ET in UTC (during DST)
        'end': '2025-08-08T16:00:00Z',    # 4:00 PM ET in UTC
        'limit': 100
    }
    
    url = 'https://data.alpaca.markets/v1beta1/options/bars'
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if 'bars' in data and symbol in data['bars']:
            bars = data['bars'][symbol]
            print(f"  Found {len(bars)} bars")
            
            # Show sample data
            if bars:
                print(f"  First bar (3:00 PM):")
                print(f"    Time: {bars[0]['t']}")
                print(f"    Open: ${bars[0]['o']:.2f}")
                print(f"    High: ${bars[0]['h']:.2f}")
                print(f"    Low: ${bars[0]['l']:.2f}")
                print(f"    Close: ${bars[0]['c']:.2f}")
                print(f"    Volume: {bars[0]['v']}")
                
                if len(bars) >= 30:
                    print(f"  Bar at 3:30 PM:")
                    bar_30 = bars[29]  # 30th minute
                    print(f"    Time: {bar_30['t']}")
                    print(f"    Close: ${bar_30['c']:.2f}")
                
                if len(bars) >= 60:
                    print(f"  Last bar (4:00 PM):")
                    print(f"    Time: {bars[-1]['t']}")
                    print(f"    Close: ${bars[-1]['c']:.2f}")
        else:
            print(f"  No data found")
    else:
        print(f"  Error {response.status_code}: {response.text[:100]}")

# Try to get latest quotes
print("\n" + "=" * 60)
print("Checking Latest Quotes:")
print("-" * 40)

url_quotes = 'https://data.alpaca.markets/v1beta1/options/quotes/latest'
params_quotes = {'symbols': ','.join(contracts.values())}

response_quotes = requests.get(url_quotes, headers=headers, params=params_quotes)
if response_quotes.status_code == 200:
    data = response_quotes.json()
    if 'quotes' in data:
        for symbol, quote in data['quotes'].items():
            if quote:
                print(f"\n{symbol}:")
                print(f"  Bid: ${quote.get('bp', 0):.2f}")
                print(f"  Ask: ${quote.get('ap', 0):.2f}")
                print(f"  Last: ${quote.get('price', 0):.2f}")
    else:
        print("No quote data available")

print("\n" + "=" * 60)
print("IMPORTANT NOTES:")
print("-" * 40)
print("• If no data found: Options may not have traded during that time")
print("• Greeks must be calculated separately")
print("• For complete analysis, combine with SPY price data")
print("• Consider using ThetaData for more comprehensive options data")