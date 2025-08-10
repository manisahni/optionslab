#!/usr/bin/env python3
"""
Place a test strangle automatically (no user input)
WARNING: This will place REAL orders on your paper account
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, OptionLatestQuoteRequest
import pytz

# Load environment variables
load_dotenv('config/.env')

def place_test_strangle():
    """Place a small test strangle automatically"""
    
    print("="*60)
    print("🎯 AUTOMATIC TEST STRANGLE PLACEMENT")
    print("="*60)
    
    # Get credentials
    api_key = os.getenv('ALPACA_PAPER_API_KEY')
    secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ Missing API credentials")
        return False
    
    # Initialize clients
    trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
    data_client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
    option_client = OptionHistoricalDataClient(api_key=api_key, secret_key=secret_key)
    
    # Get current time
    et = pytz.timezone('America/New_York')
    now_et = datetime.now(et)
    print(f"\n📅 Time: {now_et.strftime('%I:%M %p ET')}")
    
    # Check market status
    clock = trading_client.get_clock()
    if not clock.is_open:
        print("\n❌ Market is closed!")
        print(f"   Next open: {clock.next_open}")
        return False
    
    print("✅ Market is OPEN")
    
    # Get SPY price
    print("\n📊 Getting SPY price...")
    request = StockLatestQuoteRequest(symbol_or_symbols="SPY")
    quote = data_client.get_stock_latest_quote(request)
    spy_quote = quote["SPY"]
    
    spy_price = (spy_quote.bid_price + spy_quote.ask_price) / 2
    print(f"   SPY: ${spy_price:.2f}")
    print(f"   Bid: ${spy_quote.bid_price:.2f}")
    print(f"   Ask: ${spy_quote.ask_price:.2f}")
    
    # Calculate strikes (3-4 points OTM)
    call_strike = round(spy_price + 3)
    put_strike = round(spy_price - 3)
    
    # Get today's expiration
    exp_date = now_et.strftime('%y%m%d')
    
    # Build option symbols
    call_symbol = f"SPY{exp_date}C{call_strike:05d}000"
    put_symbol = f"SPY{exp_date}P{put_strike:05d}000"
    
    print(f"\n🎯 STRANGLE SETUP:")
    print(f"   Call: {call_symbol} (${call_strike})")
    print(f"   Put: {put_symbol} (${put_strike})")
    
    # Get option quotes
    try:
        print("\n💰 Getting option prices...")
        
        # Try to get quotes
        call_quote_req = OptionLatestQuoteRequest(symbol_or_symbols=call_symbol)
        put_quote_req = OptionLatestQuoteRequest(symbol_or_symbols=put_symbol)
        
        call_quotes = option_client.get_option_latest_quote(call_quote_req)
        put_quotes = option_client.get_option_latest_quote(put_quote_req)
        
        call_mid = 0
        put_mid = 0
        
        if call_symbol in call_quotes:
            call_quote = call_quotes[call_symbol]
            print(f"\n   CALL ({call_symbol}):")
            print(f"     Bid: ${call_quote.bid_price:.2f} x {call_quote.bid_size}")
            print(f"     Ask: ${call_quote.ask_price:.2f} x {call_quote.ask_size}")
            call_mid = (call_quote.bid_price + call_quote.ask_price) / 2
            print(f"     Mid: ${call_mid:.2f}")
        
        if put_symbol in put_quotes:
            put_quote = put_quotes[put_symbol]
            print(f"\n   PUT ({put_symbol}):")
            print(f"     Bid: ${put_quote.bid_price:.2f} x {put_quote.bid_size}")
            print(f"     Ask: ${put_quote.ask_price:.2f} x {put_quote.ask_size}")
            put_mid = (put_quote.bid_price + put_quote.ask_price) / 2
            print(f"     Mid: ${put_mid:.2f}")
        
        total_credit = call_mid + put_mid
        print(f"\n   Estimated Total Credit: ${total_credit*100:.0f}")
        
    except Exception as e:
        print(f"⚠️  Could not get option quotes: {e}")
        print("   Proceeding with market orders...")
    
    # Place the orders automatically
    print("\n" + "="*60)
    print("📝 PLACING ORDERS AUTOMATICALLY")
    print("="*60)
    
    try:
        # Place CALL order (sell to open)
        call_order = MarketOrderRequest(
            symbol=call_symbol,
            qty=1,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        print(f"\n   Placing CALL order (SELL 1 contract)...")
        call_result = trading_client.submit_order(call_order)
        print(f"   ✅ CALL order placed!")
        print(f"      Order ID: {call_result.id}")
        print(f"      Status: {call_result.status}")
        
        # Place PUT order (sell to open)
        put_order = MarketOrderRequest(
            symbol=put_symbol,
            qty=1,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        print(f"\n   Placing PUT order (SELL 1 contract)...")
        put_result = trading_client.submit_order(put_order)
        print(f"   ✅ PUT order placed!")
        print(f"      Order ID: {put_result.id}")
        print(f"      Status: {put_result.status}")
        
        print("\n" + "="*60)
        print("✅ STRANGLE ORDERS PLACED SUCCESSFULLY!")
        print("="*60)
        
        # Save order info for monitoring
        order_info = {
            'timestamp': now_et.isoformat(),
            'spy_price': spy_price,
            'call_symbol': call_symbol,
            'call_strike': call_strike,
            'call_order_id': call_result.id,
            'put_symbol': put_symbol,
            'put_strike': put_strike,
            'put_order_id': put_result.id
        }
        
        # Save to file for monitoring
        import json
        with open('test_strangle_orders.json', 'w') as f:
            json.dump(order_info, f, indent=2)
        
        print("\n📋 Order Summary:")
        print(f"   SPY Price: ${spy_price:.2f}")
        print(f"   Call Strike: ${call_strike} ({call_symbol})")
        print(f"   Put Strike: ${put_strike} ({put_symbol})")
        print(f"   Estimated Credit: ${total_credit*100:.0f}")
        
        print("\n💡 Next Steps:")
        print("   1. Monitor positions: python scripts/utils/monitor_strangle.py")
        print("   2. Check Alpaca dashboard for fills")
        print("   3. Close before market close (3:59 PM ET)")
        
        print("\n⚠️  IMPORTANT:")
        print("   - This is a SHORT strangle (unlimited risk)")
        print("   - Monitor closely for adverse moves")
        print("   - Close if SPY moves ±$5 from current price")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error placing orders: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        if place_test_strangle():
            print("\n✅ Test strangle placement complete!")
            print("\n📊 Order details saved to: test_strangle_orders.json")
        else:
            print("\n❌ Test strangle placement failed")
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()