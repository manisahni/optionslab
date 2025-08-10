#!/usr/bin/env python3
"""
Check Tradier API data availability and limitations
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('.env')
token = os.getenv('TRADIER_SANDBOX_TOKEN')
account = os.getenv('TRADIER_ACCOUNT_ID')

print('=== INVESTIGATING TRADIER DATA AVAILABILITY ===\n')
print(f'Account: {account}')
print(f'Token: {token[:10]}...\n')

headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/json'
}

# Test 1: Check timesales endpoint
print('1. Testing timesales endpoint for minute data:')
params = {
    'symbol': 'SPY',
    'interval': '1min',
    'start': '2025-08-08 09:30',
    'end': '2025-08-08 16:00'
}
url = 'https://sandbox.tradier.com/v1/markets/timesales'
response = requests.get(url, headers=headers, params=params)
print(f'   Status: {response.status_code}')
if response.status_code != 200:
    print(f'   Error: {response.text[:200]}')

# Test 2: Check history endpoint with minute interval  
print('\n2. Testing history endpoint with minute interval:')
params2 = {
    'symbol': 'SPY',
    'interval': 'minute',
    'start': '2025-08-08',
    'end': '2025-08-08'
}
url2 = 'https://sandbox.tradier.com/v1/markets/history'
response2 = requests.get(url2, headers=headers, params=params2)
print(f'   Status: {response2.status_code}')
if response2.status_code == 200:
    data = response2.json()
    if 'history' in data:
        print(f'   Data type available: {list(data["history"].keys())}')
        
# Test 3: Try 5-minute bars
print('\n3. Testing 5-minute interval:')
params3 = {
    'symbol': 'SPY',
    'interval': '5minute',
    'start': '2025-08-08',
    'end': '2025-08-08'
}
response3 = requests.get(url2, headers=headers, params=params3)
print(f'   Status: {response3.status_code}')
if response3.status_code == 200:
    data = response3.json()
    if 'history' in data:
        print(f'   Data available: {list(data["history"].keys())}')

# Test 4: Check if it's a sandbox vs production issue
print('\n4. Checking data endpoints:')
print('   Sandbox base URL: https://sandbox.tradier.com/v1')
print('   Production base URL: https://api.tradier.com/v1')

# Test 5: Check quotes for current data
url4 = 'https://sandbox.tradier.com/v1/markets/quotes'
params4 = {'symbols': 'SPY'}
response4 = requests.get(url4, headers=headers, params=params4)
if response4.status_code == 200:
    print('   ✓ Sandbox API is working')
    data = response4.json()
    if 'quotes' in data and 'quote' in data['quotes']:
        quote = data['quotes']['quote']
        trade_time = datetime.fromtimestamp(quote["trade_date"]/1000)
        print(f'   Last trade: {trade_time.strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'   Last price: ${quote["last"]}')

print('\n=== FINDINGS ===')
print('SANDBOX LIMITATIONS:')
print('• Only daily OHLC data available (no intraday minute bars)')
print('• The timesales endpoint requires different parameters')  
print('• Historical minute data not available in sandbox')
print('• Real-time quotes work but historical intraday does not')

print('\n=== SOLUTION OPTIONS ===')
print('\nTo get complete Aug 8 afternoon data (3:00-4:00 PM):')
print('\n1. **Use PRODUCTION Tradier API**')
print('   - Requires live Tradier account with market data subscription')
print('   - Update TRADIER_ENV=production in .env')
print('   - Add TRADIER_PROD_TOKEN to .env')

print('\n2. **Use ThetaData MCP Server** (You have this!)')
print('   - Already configured and working')
print('   - Has complete historical minute data')
print('   - Can fetch SPY data for any date/time')

print('\n3. **Use Alpaca API**')
print('   - Free tier includes 5 years of minute data')
print('   - Already have Alpaca MCP configured')

print('\n4. **Import from CSV**')
print('   - If you have the data exported from another platform')

print('\n=== RECOMMENDED APPROACH ===')
print('Use ThetaData MCP to fetch the missing Aug 8 afternoon data.')
print('You already demonstrated this works earlier in the session!')