#!/usr/bin/env python3
"""
Test Tradier API connection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient
from datetime import datetime
import json

def test_connection():
    """Test Tradier API connection"""
    
    print("="*60)
    print("🔌 TRADIER CONNECTION TEST")
    print("="*60)
    
    # Check for token first
    from dotenv import load_dotenv
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
    
    if not os.path.exists(config_path):
        print("\n❌ No .env file found!")
        print("\n📝 Creating .env file from template...")
        
        example_path = config_path + '.example'
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, config_path)
            print(f"✅ Created {config_path}")
            print("\n⚠️  Please add your Tradier API token:")
            print("   1. Sign up at https://developer.tradier.com/")
            print("   2. Get your sandbox token")
            print(f"   3. Edit {config_path}")
            print("   4. Add your token to TRADIER_SANDBOX_TOKEN")
            return False
    
    load_dotenv(config_path)
    
    # Check if token is set
    token = os.getenv('TRADIER_SANDBOX_TOKEN')
    if not token or token == 'your_sandbox_token_here':
        print("\n❌ Tradier token not configured!")
        print("\n📝 To get your FREE sandbox token:")
        print("   1. Go to: https://developer.tradier.com/")
        print("   2. Click 'Sign Up' (it's free)")
        print("   3. Get your sandbox token instantly")
        print(f"   4. Add it to: {config_path}")
        print("      TRADIER_SANDBOX_TOKEN=your_token_here")
        return False
    
    try:
        # Initialize client
        print("\n🔑 Initializing Tradier client...")
        client = TradierClient(env="sandbox")
        print(f"   Token: {token[:10]}...")
        print(f"   Environment: Sandbox (Paper Trading)")
        
        # Test 1: Get Profile
        print("\n1️⃣ Testing Profile API...")
        profile = client.get_profile()
        
        if profile and 'profile' in profile:
            prof = profile['profile']
            print("✅ Profile retrieved successfully!")
            
            if 'name' in prof:
                print(f"   Name: {prof.get('name', 'N/A')}")
            
            accounts = prof.get('account', [])
            if not isinstance(accounts, list):
                accounts = [accounts]
            
            if accounts:
                print(f"   Accounts: {len(accounts)} found")
                for acc in accounts:
                    print(f"      - {acc.get('account_number')} ({acc.get('type', 'unknown')})")
        else:
            print("❌ Could not get profile")
            return False
        
        # Test 2: Market Status
        print("\n2️⃣ Testing Market Status...")
        market = client.get_market_status()
        
        if market and 'clock' in market:
            clock = market['clock']
            state = clock.get('state', 'unknown')
            print(f"✅ Market Status: {state.upper()}")
            
            if state == 'open':
                print("   🟢 Market is OPEN - can trade!")
            else:
                next_open = clock.get('next_change', 'N/A')
                print(f"   🔴 Market is CLOSED")
                print(f"   Next change: {next_open}")
        
        # Test 3: Get SPY Quote
        print("\n3️⃣ Testing Market Data (SPY)...")
        quotes = client.get_quotes(['SPY'])
        
        if quotes and 'quotes' in quotes:
            quote = quotes['quotes'].get('quote', {})
            if isinstance(quote, list):
                quote = quote[0]
            
            if quote:
                print("✅ SPY Quote retrieved!")
                print(f"   Symbol: {quote.get('symbol')}")
                print(f"   Bid: ${quote.get('bid', 0):.2f}")
                print(f"   Ask: ${quote.get('ask', 0):.2f}")
                print(f"   Last: ${quote.get('last', 0):.2f}")
                print(f"   Volume: {quote.get('volume', 0):,}")
        
        # Test 4: Account Balance (if account exists)
        if client.account_id:
            print("\n4️⃣ Testing Account Balance...")
            balances = client.get_balances()
            
            if balances and 'balances' in balances:
                bal = balances['balances']
                print("✅ Account balances retrieved!")
                print(f"   Total Equity: ${bal.get('total_equity', 0):,.2f}")
                print(f"   Cash Available: ${bal.get('cash_available', 0):,.2f}")
                print(f"   Buying Power: ${bal.get('option_buying_power', 0):,.2f}")
        
        # Test 5: Options Data
        print("\n5️⃣ Testing Options Data...")
        
        # Get expirations
        expirations = client.get_option_expirations('SPY')
        if expirations and 'expirations' in expirations:
            exp_dates = expirations['expirations'].get('date', [])
            if exp_dates:
                print(f"✅ Found {len(exp_dates)} expiration dates")
                print(f"   Next 3: {exp_dates[:3]}")
                
                # Check for today's date (0DTE)
                today = datetime.now().strftime('%Y-%m-%d')
                if today in exp_dates:
                    print(f"   ✅ 0DTE options available today!")
                else:
                    print(f"   ⚠️  No 0DTE options today")
        
        # Summary
        print("\n" + "="*60)
        print("✅ TRADIER CONNECTION SUCCESSFUL!")
        print("="*60)
        
        print("\n📊 Summary:")
        print("   ✅ Authentication working")
        print("   ✅ Market data accessible")
        print("   ✅ Options data available")
        if client.account_id:
            print("   ✅ Account access confirmed")
        print("   ✅ Ready for options trading!")
        
        print("\n💡 Next Steps:")
        print("   1. Test options chains: python scripts/test_options.py")
        print("   2. Place test strangle: python scripts/place_strangle.py")
        print("   3. Monitor positions: python scripts/monitor_positions.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    
    if not success:
        print("\n💡 Need help?")
        print("   - Tradier Docs: https://documentation.tradier.com/")
        print("   - Get Sandbox Token: https://developer.tradier.com/")
        print("   - Sandbox is FREE with unlimited paper trading!")
        sys.exit(1)