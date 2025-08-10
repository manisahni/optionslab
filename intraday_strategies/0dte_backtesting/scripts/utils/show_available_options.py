#!/usr/bin/env python3
"""
Show available 0DTE options for SPY
"""

import os
from datetime import datetime
from dotenv import load_dotenv
import requests
import pytz

# Load environment variables
load_dotenv()

API_KEY = os.getenv('ALPACA_PAPER_API_KEY')
SECRET_KEY = os.getenv('ALPACA_PAPER_SECRET_KEY')

def show_options():
    """Display available 0DTE options"""
    
    print("="*60)
    print("📊 AVAILABLE SPY 0DTE OPTIONS")
    print("="*60)
    
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": SECRET_KEY
    }
    
    # Get SPY price first
    response = requests.get(
        "https://data.alpaca.markets/v2/stocks/SPY/quotes/latest",
        headers=headers
    )
    
    spy_price = 633.0  # Default
    if response.status_code == 200:
        data = response.json()
        quote = data.get('quote', {})
        spy_price = (quote.get('bp', 0) + quote.get('ap', 0)) / 2
        print(f"\n💹 Current SPY Price: ${spy_price:.2f}")
    
    # Get today's date
    et_tz = pytz.timezone('America/New_York')
    today = datetime.now(et_tz).strftime("%Y-%m-%d")
    
    print(f"📅 Looking for options expiring: {today}")
    
    # Get all options for today
    response = requests.get(
        f"https://paper-api.alpaca.markets/v2/options/contracts?underlying_symbol=SPY&expiration_date={today}&limit=100",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        contracts = data.get('option_contracts', data.get('contracts', []))
        
        if contracts:
            print(f"\n✅ Found {len(contracts)} total contracts")
            
            # Separate calls and puts
            calls = []
            puts = []
            
            for contract in contracts:
                symbol = contract.get('symbol', '')
                strike = contract.get('strike_price', 0)
                
                # Parse the symbol to determine type
                if 'C' in symbol:
                    calls.append({'symbol': symbol, 'strike': float(strike) if strike else 0})
                elif 'P' in symbol:
                    puts.append({'symbol': symbol, 'strike': float(strike) if strike else 0})
            
            # Sort by strike
            calls.sort(key=lambda x: x['strike'])
            puts.sort(key=lambda x: x['strike'])
            
            print(f"\n📈 CALLS ({len(calls)} available):")
            print("-" * 40)
            
            # Show ATM and nearby calls
            atm_strike = round(spy_price)
            shown = 0
            for call in calls:
                if atm_strike - 10 <= call['strike'] <= atm_strike + 10:
                    distance = call['strike'] - spy_price
                    mark = " <-- ATM" if abs(distance) < 1 else ""
                    print(f"  {call['symbol']}: Strike ${call['strike']:.0f} (SPY {distance:+.2f}){mark}")
                    shown += 1
                    if shown >= 10:
                        break
            
            print(f"\n📉 PUTS ({len(puts)} available):")
            print("-" * 40)
            
            # Show ATM and nearby puts
            shown = 0
            for put in puts:
                if atm_strike - 10 <= put['strike'] <= atm_strike + 10:
                    distance = put['strike'] - spy_price
                    mark = " <-- ATM" if abs(distance) < 1 else ""
                    print(f"  {put['symbol']}: Strike ${put['strike']:.0f} (SPY {distance:+.2f}){mark}")
                    shown += 1
                    if shown >= 10:
                        break
            
            # Find best strangle combination
            print(f"\n🎯 SUGGESTED STRANGLE (30 delta target):")
            print("-" * 40)
            
            # Find call ~5 points OTM
            call_strike = atm_strike + 3
            selected_call = None
            for call in calls:
                if abs(call['strike'] - call_strike) < 1:
                    selected_call = call
                    break
            
            # Find put ~5 points OTM  
            put_strike = atm_strike - 3
            selected_put = None
            for put in puts:
                if abs(put['strike'] - put_strike) < 1:
                    selected_put = put
                    break
            
            if selected_call and selected_put:
                print(f"  CALL: {selected_call['symbol']} (Strike: ${selected_call['strike']:.0f})")
                print(f"  PUT:  {selected_put['symbol']} (Strike: ${selected_put['strike']:.0f})")
                print(f"\n  This combination targets ~30 delta on each side")
                print(f"  Perfect for the vega-aware strategy!")
            else:
                print("  Could not find suitable strikes")
            
        else:
            print("❌ No contracts found")
            
    else:
        print(f"❌ Failed to get options: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    show_options()