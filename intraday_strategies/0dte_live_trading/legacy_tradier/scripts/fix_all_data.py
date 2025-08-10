#!/usr/bin/env python3
"""
Fix all data issues - replace fake Tradier data with real Alpaca data
"""

import sqlite3
import requests
from datetime import datetime, timedelta

# Alpaca credentials
API_KEY = "PKMLDQM62IIIP4975X71"
SECRET_KEY = "84Y8OoZTm34Cp3achHAVgNnbviYSmjCoCTxGft40"

headers = {
    'APCA-API-KEY-ID': API_KEY,
    'APCA-API-SECRET-KEY': SECRET_KEY,
    'accept': 'application/json'
}

print("=" * 70)
print("FIXING ALL DATA ISSUES - REPLACING WITH REAL ALPACA DATA")
print("=" * 70)

# Connect to database
conn = sqlite3.connect('database/market_data.db')
cur = conn.cursor()

# Step 1: Delete fake options data (where all prices are $1.00)
print("\n1. Cleaning fake options data...")
cur.execute("""
    DELETE FROM options_data 
    WHERE date(timestamp) IN ('2025-08-06', '2025-08-07')
    AND last = 1.0
""")
deleted = cur.rowcount
print(f"   Deleted {deleted} fake option records")

# Step 2: Delete SPY data for Aug 6-7 to replace with Alpaca
print("\n2. Removing old SPY data for Aug 6-7...")
cur.execute("""
    DELETE FROM spy_prices 
    WHERE date(timestamp) IN ('2025-08-06', '2025-08-07')
""")
deleted = cur.rowcount
print(f"   Deleted {deleted} SPY records")

conn.commit()

# Step 3: Download SPY data from Alpaca for Aug 6-7
dates = ['2025-08-06', '2025-08-07']

for date in dates:
    print(f"\n3. Fetching SPY data for {date}...")
    
    params = {
        'symbols': 'SPY',
        'start': f'{date}T09:30:00-05:00',
        'end': f'{date}T16:00:00-05:00',
        'timeframe': '1Min',
        'limit': 10000,
        'feed': 'sip'
    }
    
    url = 'https://data.alpaca.markets/v2/stocks/bars'
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        if 'bars' in data and 'SPY' in data['bars']:
            bars = data['bars']['SPY']
            print(f"   Retrieved {len(bars)} bars")
            
            # Insert SPY data
            for bar in bars:
                timestamp = bar['t'].replace('T', ' ').replace('Z', '')[:19]
                
                cur.execute('''
                    INSERT OR REPLACE INTO spy_prices (
                        timestamp, open, high, low, close, volume
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp,
                    bar['o'],
                    bar['h'],
                    bar['l'],
                    bar['c'],
                    bar['v']
                ))
            
            conn.commit()
            
            # Verify the data
            cur.execute(f"""
                SELECT MIN(close), MAX(close), AVG(close)
                FROM spy_prices
                WHERE date(timestamp) = '{date}'
            """)
            stats = cur.fetchone()
            print(f"   Price range: ${stats[0]:.2f} - ${stats[1]:.2f}, Avg: ${stats[2]:.2f}")

# Step 4: Download options data for Aug 6-7
print("\n4. Fetching options data...")

# Define the strangles for each day based on SPY price
options_to_fetch = {
    '2025-08-06': {
        'SPY250806C00634000': {'strike': 634.0, 'type': 'call', 'expiration': '2025-08-06'},
        'SPY250806P00630000': {'strike': 630.0, 'type': 'put', 'expiration': '2025-08-06'}
    },
    '2025-08-07': {
        'SPY250807C00635000': {'strike': 635.0, 'type': 'call', 'expiration': '2025-08-07'},
        'SPY250807P00631000': {'strike': 631.0, 'type': 'put', 'expiration': '2025-08-07'}
    }
}

for date, contracts in options_to_fetch.items():
    print(f"\n   Date: {date}")
    
    # Get SPY price at 3:00 PM to determine appropriate strikes
    cur.execute(f"""
        SELECT close FROM spy_prices
        WHERE timestamp = '{date} 15:00:00'
    """)
    spy_price_result = cur.fetchone()
    
    if spy_price_result:
        spy_price = spy_price_result[0]
        print(f"   SPY at 3:00 PM: ${spy_price:.2f}")
        
        # Adjust strikes to be roughly $3-4 away from SPY
        call_strike = round(spy_price + 3)
        put_strike = round(spy_price - 3)
        
        # Update contract symbols
        contracts = {
            f'SPY{date[2:].replace("-", "")}C{int(call_strike*1000):08d}': {
                'strike': float(call_strike), 'type': 'call', 'expiration': date
            },
            f'SPY{date[2:].replace("-", "")}P{int(put_strike*1000):08d}': {
                'strike': float(put_strike), 'type': 'put', 'expiration': date
            }
        }
        
        print(f"   Fetching strangle: ${call_strike} Call / ${put_strike} Put")
    
    for symbol, contract_info in contracts.items():
        print(f"   Fetching {contract_info['type'].upper()} {contract_info['strike']}: {symbol}")
        
        # Get 1-minute bars from Alpaca for 3:00-4:00 PM window
        params = {
            'symbols': symbol,
            'timeframe': '1Min',
            'start': f'{date}T15:00:00Z',
            'end': f'{date}T16:00:00Z',
            'limit': 100
        }
        
        url = 'https://data.alpaca.markets/v1beta1/options/bars'
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if 'bars' in data and symbol in data['bars']:
                bars = data['bars'][symbol]
                print(f"     Found {len(bars)} bars")
                
                # Insert each bar
                for bar in bars:
                    timestamp = bar['t'].replace('T', ' ').replace('Z', '')
                    
                    cur.execute('''
                        INSERT OR REPLACE INTO options_data (
                            timestamp, symbol, underlying, strike, expiry, option_type,
                            bid, ask, last, volume, open_interest,
                            iv, delta, gamma, theta, vega, rho
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp,
                        symbol,
                        'SPY',
                        contract_info['strike'],
                        contract_info['expiration'],
                        contract_info['type'],
                        bar['l'],  # Use low as bid approximation
                        bar['h'],  # Use high as ask approximation
                        bar['c'],  # Close as last
                        bar['v'],  # Volume
                        0,         # Open interest
                        0,         # IV (to be calculated)
                        0,         # Delta (to be calculated)
                        0,         # Gamma (to be calculated)
                        0,         # Theta (to be calculated)
                        0,         # Vega (to be calculated)
                        0          # Rho (to be calculated)
                    ))
                
                if bars:
                    print(f"     Entry: ${bars[0]['c']:.2f}, Exit: ${bars[-1]['c']:.2f}")
            else:
                print(f"     No data available")

conn.commit()

# Step 5: Verify the data
print("\n" + "=" * 70)
print("DATA VERIFICATION")
print("=" * 70)

for date in ['2025-08-06', '2025-08-07', '2025-08-08']:
    print(f"\n{date}:")
    
    # SPY data
    cur.execute(f"""
        SELECT COUNT(*), MIN(close), MAX(close)
        FROM spy_prices
        WHERE date(timestamp) = '{date}'
    """)
    spy_stats = cur.fetchone()
    if spy_stats[0] > 0:
        print(f"  SPY: {spy_stats[0]} records, ${spy_stats[1]:.2f} - ${spy_stats[2]:.2f}")
    
    # Options data
    cur.execute(f"""
        SELECT option_type, strike, COUNT(*), MIN(last), MAX(last)
        FROM options_data
        WHERE date(timestamp) = '{date}'
        GROUP BY option_type, strike
    """)
    for opt in cur.fetchall():
        print(f"  {opt[0].upper()} ${opt[1]:.0f}: {opt[2]} records, ${opt[3]:.2f} - ${opt[4]:.2f}")

print("\n✅ Data cleanup complete!")
print("✅ Ready to recalculate Greeks with real data")

conn.close()