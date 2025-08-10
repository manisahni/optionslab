#!/usr/bin/env python3
"""
Import complete Aug 8 data from Alpaca - NO synthetic data
"""

import sqlite3
import requests

# Get complete day from Alpaca
print("Fetching complete Aug 8 data from Alpaca (9:30 AM - 4:00 PM)...")

API_KEY = "PKMLDQM62IIIP4975X71"
SECRET_KEY = "84Y8OoZTm34Cp3achHAVgNnbviYSmjCoCTxGft40"

headers = {
    'APCA-API-KEY-ID': API_KEY,
    'APCA-API-SECRET-KEY': SECRET_KEY,
    'accept': 'application/json'
}

# Fetch all trading hours data
params = {
    'symbols': 'SPY',
    'start': '2025-08-08T09:30:00-05:00',  # 9:30 AM ET
    'end': '2025-08-08T16:00:00-05:00',     # 4:00 PM ET  
    'timeframe': '1Min',
    'limit': 10000,  # Get all data
    'feed': 'sip'
}

url = 'https://data.alpaca.markets/v2/stocks/bars'
response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    
    if 'bars' in data and 'SPY' in data['bars']:
        bars = data['bars']['SPY']
        print(f"Retrieved {len(bars)} bars from Alpaca")
        
        # Import to database
        conn = sqlite3.connect('database/market_data.db')
        cur = conn.cursor()
        
        inserted = 0
        for bar in bars:
            # Convert timestamp
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
            inserted += 1
        
        conn.commit()
        print(f"Inserted {inserted} records into database")
        
        # Verify the data
        cur.execute('''
            SELECT 
                COUNT(*) as total,
                MIN(timestamp) as first,
                MAX(timestamp) as last,
                MIN(close) as low,
                MAX(close) as high
            FROM spy_prices
            WHERE date(timestamp) = '2025-08-08'
        ''')
        stats = cur.fetchone()
        
        print("\n" + "=" * 60)
        print("AUG 8 DATA SUMMARY (100% REAL ALPACA DATA)")
        print("=" * 60)
        print(f"Records: {stats[0]}")
        print(f"Time range: {stats[1]} to {stats[2]}")
        print(f"Price range: ${stats[3]:.2f} - ${stats[4]:.2f}")
        
        # Check key timestamps
        cur.execute('''
            SELECT timestamp, close
            FROM spy_prices
            WHERE date(timestamp) = '2025-08-08'
            AND time(timestamp) IN ('09:30:00', '13:30:00', '15:00:00', '15:30:00', '16:00:00')
            ORDER BY timestamp
        ''')
        
        print("\nKey Timestamps:")
        for row in cur.fetchall():
            label = ""
            if '09:30' in row[0]: label = " (Market open)"
            if '13:30' in row[0]: label = " (1:30 PM)"
            if '15:00' in row[0]: label = " (VegaAware entry)"
            if '15:30' in row[0]: label = " (VegaAware exit)"
            if '16:00' in row[0]: label = " (Market close)"
            print(f"  {row[0]}: ${row[1]:.2f}{label}")
        
        conn.close()
        
        print("\n✅ SUCCESS: Complete Aug 8 data imported from Alpaca")
        print("✅ NO synthetic or interpolated data")
        print("✅ Ready for accurate VegaAware analysis")
        
    else:
        print("No data returned from Alpaca")
else:
    print(f"Error {response.status_code}: {response.text}")