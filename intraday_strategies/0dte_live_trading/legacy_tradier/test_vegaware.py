#!/usr/bin/env python3
"""
Test VegaAware Strategy Components
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alpaca_vegaware_trader import AlpacaVegaAwareTrader
from datetime import datetime
import pytz

def test_vegaware():
    """Test VegaAware strategy components"""
    print("=" * 70)
    print("TESTING VEGAWARE STRATEGY COMPONENTS")
    print("=" * 70)
    
    # Initialize trader
    trader = AlpacaVegaAwareTrader(paper=True)
    ET = pytz.timezone('US/Eastern')
    
    print("\n1. Testing Entry Criteria Check:")
    print("-" * 40)
    criteria = trader.check_entry_criteria()
    
    print(f"Score: {criteria['score']:.0f}%")
    print(f"Can Trade: {'✅ Yes' if criteria['can_trade'] else '❌ No'}")
    
    print("\nCriteria Results:")
    for check, passed in criteria['checks'].items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check.replace('_', ' ').title()}")
    
    if 'details' in criteria:
        print("\nKey Metrics:")
        details = criteria['details']
        if 'spy_price' in details:
            print(f"  SPY Price: ${details['spy_price']:.2f}")
        if 'spy_spread' in details:
            print(f"  SPY Spread: ${details['spy_spread']:.3f}")
        if 'buying_power' in details:
            print(f"  Buying Power: ${details['buying_power']:,.2f}")
        if 'total_vega' in details:
            print(f"  Total Vega: {details['total_vega']:.2f}")
        if 'net_delta' in details:
            print(f"  Net Delta: {details['net_delta']:.3f}")
        if 'total_credit' in details:
            print(f"  Expected Credit: ${details['total_credit']:.2f}")
    
    print("\n2. Testing Delta-Based Strike Selection:")
    print("-" * 40)
    
    # Get SPY price
    spy_quote = trader.client.get_stock_quote("SPY")
    if spy_quote:
        spy_price = (spy_quote.get('bp', 0) + spy_quote.get('ap', 0)) / 2
        print(f"SPY Price: ${spy_price:.2f}")
        
        # Test strike finding
        strikes = trader.find_delta_strikes(spy_price)
        if strikes:
            call_symbol, put_symbol, call_strike, put_strike = strikes
            print(f"✅ Found strikes:")
            print(f"  Call: {call_symbol} (${call_strike:.0f})")
            print(f"  Put: {put_symbol} (${put_strike:.0f})")
            print(f"  Width: ${call_strike - spy_price:.2f} / ${spy_price - put_strike:.2f}")
        else:
            print("❌ No strikes available (market closed or no 0DTE)")
    
    print("\n3. Strategy Parameters:")
    print("-" * 40)
    print(f"Target Delta: {trader.TARGET_DELTA}")
    print(f"Max Vega: {trader.MAX_VEGA}")
    print(f"Min Premium: ${trader.MIN_PREMIUM}")
    print(f"Stop Loss: {trader.STOP_LOSS_MULTIPLIER}x credit")
    print(f"Profit Target: {trader.PROFIT_TARGET_PCT}%")
    print(f"Entry Score Required: {trader.ENTRY_SCORE_THRESHOLD}%")
    
    print("\n4. Time Windows:")
    print("-" * 40)
    now = datetime.now(ET)
    current_time = now.time()
    print(f"Current Time: {current_time.strftime('%I:%M %p')} ET")
    print(f"Entry Window: {trader.ENTRY_START.strftime('%I:%M %p')}-{trader.ENTRY_END.strftime('%I:%M %p')} ET")
    print(f"Optimal Entry: {trader.OPTIMAL_ENTRY.strftime('%I:%M %p')} ET")
    print(f"Recommended Exit: {trader.RECOMMENDED_EXIT.strftime('%I:%M %p')} ET")
    print(f"Final Exit: {trader.FINAL_EXIT.strftime('%I:%M %p')} ET")
    
    in_window = trader.ENTRY_START <= current_time <= trader.ENTRY_END
    print(f"In Entry Window: {'✅ Yes' if in_window else '❌ No'}")
    
    print("\n5. Risk Checks:")
    print("-" * 40)
    
    # Example position monitoring (mock data)
    print("Mock Position Monitoring:")
    print("  If P&L < -2x credit → STOP LOSS")
    print("  If P&L > 50% credit → PROFIT TARGET")
    print("  If SPY near strikes → STRIKE BREACH")
    print("  If Vega > 3.0 → VEGA EXPLOSION")
    print("  If Time > 3:55 PM → TIME EXIT")
    
    print("\n" + "=" * 70)
    print("✅ VEGAWARE STRATEGY TEST COMPLETE")
    print("=" * 70)
    
    # Show recommendations
    print("\nRecommendations:")
    if criteria['score'] < 80:
        print("⚠️ Entry score too low - wait for better conditions")
    elif not criteria['checks'].get('market_open', False):
        print("⚠️ Market is closed - wait for market hours")
    elif not in_window:
        print("⚠️ Outside entry window - wait for 2:30-3:30 PM ET")
    else:
        print("✅ All systems ready for trading!")

if __name__ == "__main__":
    test_vegaware()