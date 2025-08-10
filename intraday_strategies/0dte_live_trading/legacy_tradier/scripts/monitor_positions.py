#!/usr/bin/env python3
"""
Monitor strangle positions on Tradier
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient, OrderManager
from datetime import datetime
import time
import json

def monitor_positions():
    """Monitor strangle positions"""
    
    print("="*60)
    print("📊 TRADIER POSITION MONITOR")
    print("="*60)
    
    try:
        # Initialize client
        client = TradierClient(env="sandbox")
        order_mgr = OrderManager(client)
        
        # Get current time
        now = datetime.now()
        print(f"\n📅 Time: {now.strftime('%I:%M %p ET')}")
        
        # Check market status
        if client.is_market_open():
            print("✅ Market is OPEN")
        else:
            print("⚠️  Market is CLOSED")
        
        # Get SPY quote
        quotes = client.get_quotes(['SPY'])
        if quotes and 'quotes' in quotes:
            quote = quotes['quotes'].get('quote', {})
            if isinstance(quote, list):
                quote = quote[0]
            
            spy_price = (quote.get('bid', 0) + quote.get('ask', 0)) / 2
            print(f"\n📈 SPY: ${spy_price:.2f}")
            print(f"   Bid: ${quote.get('bid', 0):.2f}")
            print(f"   Ask: ${quote.get('ask', 0):.2f}")
        
        # Get account balances
        print("\n💰 ACCOUNT STATUS:")
        print("-"*40)
        
        balances = client.get_balances()
        if balances and 'balances' in balances:
            bal = balances['balances']
            print(f"   Total Equity: ${bal.get('total_equity', 0):,.2f}")
            print(f"   Total Cash: ${bal.get('total_cash', 0):,.2f}")
            
            # Get margin data if available
            margin = bal.get('margin', {})
            if margin:
                print(f"   Option BP: ${margin.get('option_buying_power', 0):,.2f}")
                print(f"   Stock BP: ${margin.get('stock_buying_power', 0):,.2f}")
            else:
                print(f"   Cash Available: ${bal.get('cash_available', 0):,.2f}")
                print(f"   Option BP: ${bal.get('option_buying_power', 0):,.2f}")
            
            # P&L
            pl_day = bal.get('day_cost_basis', 0)
            if pl_day:
                print(f"   Day P&L: ${pl_day:+,.2f}")
        
        # Get positions
        print("\n📊 CURRENT POSITIONS:")
        print("-"*40)
        
        strangle_pos = order_mgr.get_strangle_positions()
        
        if strangle_pos:
            total_pl = 0
            
            # Show calls
            if strangle_pos['calls']:
                print("\n📈 CALLS:")
                for call in strangle_pos['calls']:
                    print(f"   {call['symbol']}:")
                    print(f"     Quantity: {call['quantity']}")
                    print(f"     Cost Basis: ${call['cost_basis']:.2f}")
                    print(f"     Current Value: ${call['current_value']:.2f}")
                    print(f"     P&L: ${call['unrealized_pl']:+.2f}")
                    total_pl += call['unrealized_pl']
            
            # Show puts
            if strangle_pos['puts']:
                print("\n📉 PUTS:")
                for put in strangle_pos['puts']:
                    print(f"   {put['symbol']}:")
                    print(f"     Quantity: {put['quantity']}")
                    print(f"     Cost Basis: ${put['cost_basis']:.2f}")
                    print(f"     Current Value: ${put['current_value']:.2f}")
                    print(f"     P&L: ${put['unrealized_pl']:+.2f}")
                    total_pl += put['unrealized_pl']
            
            print(f"\n💵 TOTAL P&L: ${total_pl:+.2f}")
            
            # Calculate risk metrics
            if strangle_pos['calls'] and strangle_pos['puts']:
                # Parse strikes from symbols like SPY250807C00636000
                call_symbol = strangle_pos['calls'][0]['symbol']
                put_symbol = strangle_pos['puts'][0]['symbol']
                
                # Extract strike - last 8 digits, first 5 are strike price
                # Format: SPY250807C00636000 -> strike is 636
                call_strike_full = call_symbol[-8:]  # Get last 8 chars: 00636000
                put_strike_full = put_symbol[-8:]    # Get last 8 chars: 00629000
                
                call_strike = float(call_strike_full[:5])  # First 5: 00636 -> 636
                put_strike = float(put_strike_full[:5])    # First 5: 00629 -> 629
                
                print(f"\n⚠️  RISK METRICS:")
                print(f"   Call Strike: ${call_strike}")
                print(f"   Put Strike: ${put_strike}")
                print(f"   SPY Distance to Call: ${spy_price - call_strike:+.2f}")
                print(f"   SPY Distance to Put: ${spy_price - put_strike:+.2f}")
                
                # Warning if getting close to strikes
                if spy_price > call_strike - 1:
                    print("   🚨 WARNING: SPY approaching CALL strike!")
                if spy_price < put_strike + 1:
                    print("   🚨 WARNING: SPY approaching PUT strike!")
        else:
            # Check for any positions at all
            positions = client.get_positions()
            if positions and 'positions' in positions:
                pos_list = positions['positions'].get('position', [])
                if not isinstance(pos_list, list):
                    pos_list = [pos_list] if pos_list else []
                
                if pos_list:
                    print("\nOther positions found:")
                    for pos in pos_list:
                        print(f"   {pos.get('symbol')}: {pos.get('quantity')} @ ${pos.get('cost_basis', 0):.2f}")
                else:
                    print("\n   No open positions")
            else:
                print("\n   No open positions")
        
        # Get open orders
        print("\n📋 OPEN ORDERS:")
        print("-"*40)
        
        open_orders = order_mgr.get_open_orders()
        
        if open_orders:
            for order in open_orders:
                print(f"\n   Order ID: {order.get('id')}")
                print(f"   Type: {order.get('class', 'single')}")
                print(f"   Status: {order.get('status')}")
                
                # Parse legs for multileg orders
                if order.get('class') == 'multileg':
                    legs = order.get('leg', [])
                    if not isinstance(legs, list):
                        legs = [legs]
                    for leg in legs:
                        print(f"   - {leg.get('option_symbol')}: {leg.get('side')} {leg.get('quantity')}")
        else:
            print("   No open orders")
        
        # Time until close
        print("\n⏰ TIME MANAGEMENT:")
        print("-"*40)
        
        close_time = now.replace(hour=15, minute=59, second=0)
        time_remaining = close_time - now
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        
        print(f"   Time until 3:59 PM: {hours}h {minutes}m")
        
        if hours == 0 and minutes <= 30:
            print("   ⚠️  CLOSING TIME APPROACHING!")
            print("   Consider closing positions soon")
        
        print("\n" + "="*60)
        print("📊 MONITOR COMPLETE")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run once or loop
    import argparse
    parser = argparse.ArgumentParser(description='Monitor Tradier positions')
    parser.add_argument('--loop', action='store_true', help='Loop continuously')
    parser.add_argument('--interval', type=int, default=30, help='Update interval in seconds')
    args = parser.parse_args()
    
    if args.loop:
        print(f"🔄 Monitoring every {args.interval} seconds (Ctrl+C to stop)")
        print()
        
        try:
            while True:
                monitor_positions()
                print(f"\n⏳ Next update in {args.interval} seconds...")
                time.sleep(args.interval)
                print("\n" + "="*60)
        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped")
    else:
        monitor_positions()