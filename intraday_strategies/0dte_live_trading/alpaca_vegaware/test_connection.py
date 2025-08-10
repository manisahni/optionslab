#!/usr/bin/env python3
"""
Test Alpaca Connection
"""

from alpaca_vegaware.core.client import AlpacaClient
from datetime import datetime

def test_alpaca():
    """Test Alpaca functionality"""
    print("=" * 70)
    print("TESTING ALPACA INTEGRATION")
    print("=" * 70)
    
    # Initialize client
    client = AlpacaClient(paper=True)
    
    # Test 1: Account Info
    print("\n1. Account Information:")
    account = client.get_account()
    if account:
        print(f"   Account: {account.get('account_number')}")
        print(f"   Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
        print(f"   Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
        print("   ✅ Account access successful")
    else:
        print("   ❌ Failed to get account info")
    
    # Test 2: Market Status
    print("\n2. Market Status:")
    is_open = client.is_market_open()
    print(f"   Market Open: {'Yes' if is_open else 'No'}")
    clock = client.get_market_hours()
    if clock:
        print(f"   Next Open: {clock.get('next_open', 'N/A')}")
        print(f"   Next Close: {clock.get('next_close', 'N/A')}")
        print("   ✅ Market status check successful")
    
    # Test 3: SPY Quote
    print("\n3. SPY Quote:")
    quote = client.get_stock_quote("SPY")
    if quote:
        bid = quote.get('bp', 0)
        ask = quote.get('ap', 0)
        print(f"   Bid: ${bid:.2f}")
        print(f"   Ask: ${ask:.2f}")
        print(f"   Mid: ${(bid + ask) / 2:.2f}")
        print("   ✅ Stock quote successful")
    else:
        print("   ❌ Failed to get SPY quote")
    
    # Test 4: Find 0DTE Options
    print("\n4. 0DTE Options:")
    today = datetime.now().strftime('%Y-%m-%d')
    contracts = client.get_option_contracts("SPY", expiration=today)
    if contracts:
        print(f"   Found {len(contracts)} contracts for today")
        
        # Find ATM options
        if quote:
            spy_price = (quote.get('bp', 0) + quote.get('ap', 0)) / 2
            call_strike = round(spy_price + 3)
            put_strike = round(spy_price - 3)
            
            call_found = False
            put_found = False
            
            for contract in contracts:
                strike = float(contract.get('strike_price', 0))
                if strike == call_strike and contract.get('type') == 'call':
                    print(f"   Call: {contract.get('symbol')} (${call_strike})")
                    call_found = True
                elif strike == put_strike and contract.get('type') == 'put':
                    print(f"   Put: {contract.get('symbol')} (${put_strike})")
                    put_found = True
            
            if call_found and put_found:
                print("   ✅ Found strangle strikes")
            else:
                print("   ⚠️ Could not find appropriate strikes")
    else:
        print("   ⚠️ No 0DTE options available (weekend or holiday?)")
    
    # Test 5: Positions
    print("\n5. Current Positions:")
    positions = client.get_positions()
    if positions:
        print(f"   Found {len(positions)} positions")
        for pos in positions[:3]:  # Show first 3
            print(f"   - {pos.get('symbol')}: {pos.get('qty')} @ ${pos.get('avg_entry_price')}")
    else:
        print("   No open positions")
    
    # Test 6: Orders
    print("\n6. Open Orders:")
    orders = client.get_orders()
    if orders:
        print(f"   Found {len(orders)} open orders")
        for order in orders[:3]:  # Show first 3
            print(f"   - {order.get('symbol')}: {order.get('side')} {order.get('qty')}")
    else:
        print("   No open orders")
    
    print("\n" + "=" * 70)
    print("✅ ALPACA INTEGRATION TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_alpaca()