#!/usr/bin/env python3
"""
Place a 0DTE strangle on SPY using Tradier
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient, OptionsManager, OrderManager
from datetime import datetime
import time

def place_strangle():
    """Place a 0DTE strangle on SPY"""
    
    print("="*60)
    print("🎯 0DTE STRANGLE PLACEMENT - TRADIER")
    print("="*60)
    
    try:
        # Initialize client
        print("\n🔑 Initializing Tradier client...")
        client = TradierClient(env="sandbox")  # Change to "production" for live
        options_mgr = OptionsManager(client)
        order_mgr = OrderManager(client)
        
        # Check market status
        if not client.is_market_open():
            print("\n⚠️  Market is closed!")
            market = client.get_market_status()
            if market and 'clock' in market:
                next_change = market['clock'].get('next_change', 'N/A')
                print(f"   Next change: {next_change}")
            return False
        
        print("✅ Market is OPEN")
        
        # Get current time
        now = datetime.now()
        print(f"\n📅 Time: {now.strftime('%I:%M %p ET')}")
        
        # Get SPY quote
        print("\n📊 Getting SPY price...")
        quotes = client.get_quotes(['SPY'])
        
        if not quotes or 'quotes' not in quotes:
            print("❌ Could not get SPY quote")
            return False
        
        quote = quotes['quotes'].get('quote', {})
        if isinstance(quote, list):
            quote = quote[0]
        
        spy_bid = quote.get('bid', 0)
        spy_ask = quote.get('ask', 0)
        spy_price = (spy_bid + spy_ask) / 2
        
        print(f"   SPY: ${spy_price:.2f}")
        print(f"   Bid: ${spy_bid:.2f}")
        print(f"   Ask: ${spy_ask:.2f}")
        
        # Find strangle strikes
        print("\n🔍 Finding strangle strikes...")
        strikes = options_mgr.find_strangle_strikes('SPY', target_delta=0.15, dte=0)
        
        if not strikes:
            print("❌ Could not find suitable strikes")
            return False
        
        call_option, put_option = strikes
        
        print(f"\n✅ Strangle strikes found:")
        print(f"   CALL: {call_option['symbol']} (Strike: ${call_option['strike']})")
        print(f"   PUT: {put_option['symbol']} (Strike: ${put_option['strike']})")
        
        # Get quotes for the options
        print("\n💰 Getting option quotes...")
        strangle_quotes = options_mgr.get_strangle_quotes(
            call_option['symbol'],
            put_option['symbol']
        )
        
        if strangle_quotes:
            if 'call' in strangle_quotes:
                call_q = strangle_quotes['call']
                print(f"\n   CALL ({call_option['symbol']}):")
                print(f"     Bid: ${call_q['bid']:.2f}")
                print(f"     Ask: ${call_q['ask']:.2f}")
                print(f"     Mid: ${call_q['mid']:.2f}")
                print(f"     Volume: {call_q['volume']}")
            
            if 'put' in strangle_quotes:
                put_q = strangle_quotes['put']
                print(f"\n   PUT ({put_option['symbol']}):")
                print(f"     Bid: ${put_q['bid']:.2f}")
                print(f"     Ask: ${put_q['ask']:.2f}")
                print(f"     Mid: ${put_q['mid']:.2f}")
                print(f"     Volume: {put_q['volume']}")
            
            # Calculate expected credit
            if 'call' in strangle_quotes and 'put' in strangle_quotes:
                credit = options_mgr.calculate_strangle_credit(
                    strangle_quotes['call'],
                    strangle_quotes['put']
                )
                print(f"\n   💵 Expected Credit: ${credit:.2f}")
        
        # Check account balance
        print("\n💰 Checking account...")
        balances = client.get_balances()
        
        if balances and 'balances' in balances:
            bal = balances['balances']
            buying_power = bal.get('option_buying_power', 0)
            print(f"   Option Buying Power: ${buying_power:,.2f}")
            
            if buying_power < 1000:
                print("⚠️  Low buying power for options trading")
        
        # Confirm before placing order
        print("\n" + "="*60)
        print("📝 READY TO PLACE STRANGLE")
        print("="*60)
        
        print(f"\n🎯 Order Details:")
        print(f"   SELL 1 {call_option['symbol']} (Call @ ${call_option['strike']})")
        print(f"   SELL 1 {put_option['symbol']} (Put @ ${put_option['strike']})")
        
        if client.env == "sandbox":
            print("\n✅ SANDBOX MODE - Paper money only")
        else:
            print("\n⚠️  PRODUCTION MODE - REAL MONEY!")
        
        # Auto-confirm for sandbox, manual for production
        if client.env == "production":
            response = input("\n➡️  Type 'YES' to place order: ")
            if response.strip().upper() != 'YES':
                print("\n❌ Order cancelled")
                return False
        else:
            print("\n🤖 Auto-placing order (sandbox mode)...")
            time.sleep(2)
        
        # Place the strangle order
        print("\n📤 Placing strangle order...")
        result = order_mgr.place_strangle(
            call_option['symbol'],
            put_option['symbol'],
            quantity=1
        )
        
        if result:
            print("\n" + "="*60)
            print("✅ STRANGLE ORDER PLACED SUCCESSFULLY!")
            print("="*60)
            
            # Save order info
            order_info = {
                'timestamp': now.isoformat(),
                'spy_price': spy_price,
                'call_symbol': call_option['symbol'],
                'call_strike': call_option['strike'],
                'put_symbol': put_option['symbol'],
                'put_strike': put_option['strike'],
                'environment': client.env
            }
            
            import json
            with open('tradier_strangle_order.json', 'w') as f:
                json.dump(order_info, f, indent=2)
            
            print("\n📋 Order saved to: tradier_strangle_order.json")
            
            print("\n💡 Next Steps:")
            print("   1. Monitor position: python scripts/monitor_positions.py")
            print("   2. Check P&L regularly")
            print("   3. Close before 3:59 PM ET")
            
            return True
        else:
            print("\n❌ Order placement failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = place_strangle()
    
    if not success:
        print("\n💡 Troubleshooting:")
        print("   1. Check your API token in config/.env")
        print("   2. Verify market is open")
        print("   3. Check account has options trading enabled")
        sys.exit(1)