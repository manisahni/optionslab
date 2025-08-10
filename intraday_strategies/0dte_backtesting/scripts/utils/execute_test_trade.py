#!/usr/bin/env python3
"""
Execute a REAL test trade - Buys 1 share of SPY
WARNING: This will place a REAL order in your paper account!
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
import pytz
import time

# Load environment variables
load_dotenv()

def execute_test_trade():
    """Execute a real test trade"""
    
    print("="*60)
    print("⚠️  REAL TRADE EXECUTION TEST")
    print("="*60)
    print("\nThis will place a REAL order in your paper account!")
    print("It will buy 1 share of SPY at market price.")
    
    # Confirm
    confirm = input("\n⚠️  Execute test trade? Type 'YES' to confirm: ").strip()
    
    if confirm != 'YES':
        print("❌ Trade cancelled")
        return
    
    # Initialize clients
    api_key = os.getenv('ALPACA_PAPER_API_KEY')
    secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY')
    
    trading_client = TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=True
    )
    
    data_client = StockHistoricalDataClient(
        api_key=api_key,
        secret_key=secret_key
    )
    
    # Check market status
    clock = trading_client.get_clock()
    if not clock.is_open:
        print("\n❌ Market is closed! Cannot place orders.")
        return
    
    # Get SPY quote
    print("\n📊 Getting SPY quote...")
    request = StockLatestQuoteRequest(symbol_or_symbols="SPY")
    quote = data_client.get_stock_latest_quote(request)
    spy_quote = quote["SPY"]
    
    print(f"Current SPY:")
    print(f"  Bid: ${spy_quote.bid_price:.2f}")
    print(f"  Ask: ${spy_quote.ask_price:.2f}")
    print(f"  Mid: ${(spy_quote.bid_price + spy_quote.ask_price)/2:.2f}")
    
    # Check account
    account = trading_client.get_account()
    print(f"\nAccount:")
    print(f"  Buying Power: ${float(account.buying_power):,.2f}")
    print(f"  Cash: ${float(account.cash):,.2f}")
    
    # Create order
    print("\n📝 Creating order...")
    
    # Option 1: Market Order (immediate fill)
    market_order = MarketOrderRequest(
        symbol="SPY",
        qty=1,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )
    
    print(f"Order Details:")
    print(f"  Symbol: SPY")
    print(f"  Quantity: 1 share")
    print(f"  Type: MARKET")
    print(f"  Side: BUY")
    print(f"  Est. Cost: ~${spy_quote.ask_price:.2f}")
    
    # Final confirmation
    final_confirm = input("\n🚀 Place order now? (yes/no): ").strip().lower()
    
    if final_confirm != 'yes':
        print("❌ Order cancelled")
        return
    
    # PLACE THE ORDER
    print("\n🚀 Placing order...")
    
    try:
        order = trading_client.submit_order(market_order)
        
        print(f"\n✅ ORDER PLACED SUCCESSFULLY!")
        print(f"Order ID: {order.id}")
        print(f"Status: {order.status}")
        print(f"Symbol: {order.symbol}")
        print(f"Quantity: {order.qty}")
        print(f"Side: {order.side}")
        print(f"Type: {order.order_type}")
        
        # Wait for fill
        print("\n⏳ Waiting for fill...")
        time.sleep(3)
        
        # Check order status
        filled_order = trading_client.get_order_by_id(order.id)
        
        print(f"\n📊 ORDER UPDATE:")
        print(f"Status: {filled_order.status}")
        
        if filled_order.filled_qty:
            print(f"Filled Quantity: {filled_order.filled_qty}")
            
        if filled_order.filled_avg_price:
            print(f"Fill Price: ${filled_order.filled_avg_price}")
            cost = float(filled_order.filled_avg_price) * float(filled_order.filled_qty)
            print(f"Total Cost: ${cost:.2f}")
        
        # Check position
        print("\n📈 Checking position...")
        positions = trading_client.get_all_positions()
        
        for pos in positions:
            if pos.symbol == "SPY":
                print(f"\nSPY Position:")
                print(f"  Quantity: {pos.qty}")
                print(f"  Avg Entry: ${pos.avg_entry_price}")
                print(f"  Current: ${pos.current_price or 'N/A'}")
                print(f"  P&L: ${pos.unrealized_pl or 0:+.2f}")
                break
        
        print("\n" + "="*60)
        print("✅ TEST TRADE COMPLETE!")
        print("="*60)
        print("\nYou successfully:")
        print("1. Connected to Alpaca")
        print("2. Retrieved real-time quotes")
        print("3. Placed a live order")
        print("4. Received order fill")
        print("5. Confirmed position")
        
        print("\n🎯 Your trading system is fully operational!")
        
        # Offer to close position
        close = input("\n💡 Close this position? (yes/no): ").strip().lower()
        
        if close == 'yes':
            print("\n🔄 Closing position...")
            trading_client.close_position("SPY")
            print("✅ Close order submitted")
            
            time.sleep(3)
            
            # Check if closed
            positions = trading_client.get_all_positions()
            spy_pos = [p for p in positions if p.symbol == "SPY"]
            
            if not spy_pos:
                print("✅ Position closed successfully")
            else:
                print("⏳ Position still closing...")
        
    except Exception as e:
        print(f"\n❌ Error placing order: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        execute_test_trade()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()