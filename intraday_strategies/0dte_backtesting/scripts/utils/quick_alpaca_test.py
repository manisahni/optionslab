#!/usr/bin/env python3
"""
Quick Alpaca connection test - minimal dependencies
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def quick_test():
    """Quick test without SDK"""
    
    print("="*50)
    print("QUICK ALPACA TEST")
    print("="*50)
    
    # Get credentials
    api_key = os.getenv('ALPACA_PAPER_API_KEY', 'FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F')
    secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY', '')
    
    if not secret_key or secret_key == 'YOUR_SECRET_KEY_HERE_FROM_ALPACA_DASHBOARD':
        print("\n❌ Secret key not set!")
        print("\nTo add your secret key, run:")
        print("   python add_secret_key.py")
        return False
    
    print(f"\n🔑 Credentials loaded:")
    print(f"   API Key: {api_key[:10]}...")
    print(f"   Secret: {secret_key[:10]}...")
    
    # Test account endpoint
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key
    }
    
    try:
        # Get account info
        url = "https://paper-api.alpaca.markets/v2/account"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            account = response.json()
            print("\n✅ CONNECTION SUCCESSFUL!")
            print(f"\nAccount Details:")
            print(f"  Account #: {account.get('account_number', 'N/A')}")
            print(f"  Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
            print(f"  Cash: ${float(account.get('cash', 0)):,.2f}")
            print(f"  Equity: ${float(account.get('equity', 0)):,.2f}")
            
            # Check market status
            clock_response = requests.get(
                "https://paper-api.alpaca.markets/v2/clock", 
                headers=headers
            )
            if clock_response.status_code == 200:
                clock = clock_response.json()
                print(f"\nMarket Status:")
                print(f"  Open: {clock.get('is_open', False)}")
                if not clock.get('is_open'):
                    print(f"  Next Open: {clock.get('next_open', 'N/A')}")
            
            # Get SPY quote
            data_url = "https://data.alpaca.markets/v2/stocks/SPY/quotes/latest"
            quote_response = requests.get(data_url, headers=headers)
            if quote_response.status_code == 200:
                data = quote_response.json()
                quote = data.get('quote', {})
                print(f"\nSPY Quote:")
                print(f"  Bid: ${quote.get('bp', 0):.2f}")
                print(f"  Ask: ${quote.get('ap', 0):.2f}")
                print(f"  Spread: ${(quote.get('ap', 0) - quote.get('bp', 0)):.2f}")
            
            print("\n" + "="*50)
            print("✅ ALL TESTS PASSED!")
            print("="*50)
            print("\nYour Alpaca connection is working!")
            print("\n📋 Next Steps:")
            print("1. Install SDK: pip install alpaca-py py_vollib")
            print("2. Test full system: python alpaca_secure_config.py")
            print("3. Start paper trading: python alpaca_vega_trader.py --paper")
            print("\n⚠️ Remember: Trade 3:00-3:30 PM ET for best results!")
            
            return True
            
        elif response.status_code == 401:
            print("\n❌ Authentication failed!")
            print("   Check your API key and secret key")
            print("\nRun: python add_secret_key.py")
            
        elif response.status_code == 403:
            print("\n❌ Access forbidden!")
            print("   Your secret key may be incorrect")
            print("\nRun: python add_secret_key.py")
            
        else:
            print(f"\n❌ Failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    if not quick_test():
        print("\n💡 TIP: Run 'python add_secret_key.py' to set up your credentials")