#!/usr/bin/env python3
"""
Simplified Test Strategy - Focus on quick entry/exit testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient, OptionsManager, OrderManager
from datetime import datetime, timedelta
import time

class SimpleTestStrategy:
    """Simplified testing strategy"""
    
    def __init__(self):
        print("Initializing strategy...")
        self.client = TradierClient(env="sandbox")
        self.options_mgr = OptionsManager(self.client)
        self.order_mgr = OrderManager(self.client)
        
        self.position = None
        self.entry_time = None
        self.trades_executed = 0
        
    def place_test_strangle(self):
        """Place a test strangle"""
        print(f"\n{'='*60}")
        print(f"TRADE #{self.trades_executed + 1} - ATTEMPTING ENTRY")
        print(f"Time: {datetime.now().strftime('%I:%M:%S %p')}")
        
        # Check market
        if not self.client.is_market_open():
            print("Market closed")
            return False
        
        # Get SPY price
        print("Getting SPY quote...")
        quotes = self.client.get_quotes(['SPY'])
        if not quotes:
            print("No quote")
            return False
        
        quote = quotes['quotes'].get('quote', {})
        if isinstance(quote, list):
            quote = quote[0]
        spy_price = (quote.get('bid', 0) + quote.get('ask', 0)) / 2
        print(f"SPY: ${spy_price:.2f}")
        
        # Find strikes
        print("Finding strikes...")
        strikes = self.options_mgr.find_strangle_strikes('SPY', target_delta=0.10, dte=0)
        if not strikes:
            print("No strikes found")
            return False
        
        call_option, put_option = strikes
        print(f"Strikes: Call ${call_option['strike']}, Put ${put_option['strike']}")
        
        # Place order
        print(f"Placing strangle order...")
        result = self.order_mgr.place_strangle(
            call_option['symbol'],
            put_option['symbol'],
            quantity=1
        )
        
        if result:
            self.position = {
                'call': call_option['symbol'],
                'put': put_option['symbol'],
                'entry_spy': spy_price
            }
            self.entry_time = datetime.now()
            self.trades_executed += 1
            print("✅ STRANGLE PLACED!")
            return True
        else:
            print("❌ Order failed")
            return False
    
    def check_and_close(self):
        """Check position and close after time limit"""
        if not self.position:
            return False
        
        hold_time = (datetime.now() - self.entry_time).total_seconds()
        print(f"\rHolding for {hold_time:.0f}s...", end="")
        
        # Close after 2 minutes
        if hold_time >= 120:
            print(f"\n\n{'='*60}")
            print("CLOSING POSITION - 2 minute hold reached")
            
            # Get P&L
            positions = self.order_mgr.get_strangle_positions()
            if positions:
                total_pl = 0
                for call in positions.get('calls', []):
                    total_pl += call['unrealized_pl']
                for put in positions.get('puts', []):
                    total_pl += put['unrealized_pl']
                print(f"P&L: ${total_pl:.2f}")
            
            # Close position
            result = self.order_mgr.close_strangle(
                self.position['call'],
                self.position['put']
            )
            
            if result:
                print("✅ Position closed")
                self.position = None
                self.entry_time = None
                return True
            else:
                print("❌ Close failed")
                return False
        
        return False
    
    def run(self, max_trades=2):
        """Run the strategy"""
        print("="*60)
        print("SIMPLE TEST STRATEGY")
        print("="*60)
        print(f"Max trades: {max_trades}")
        print(f"Hold time: 2 minutes per trade")
        print("="*60)
        
        while self.trades_executed < max_trades:
            try:
                # Check market close
                if datetime.now().hour >= 16:
                    print("\nMarket closed")
                    break
                
                # If no position, try to enter
                if not self.position:
                    if self.trades_executed > 0:
                        print("\nWaiting 10 seconds before next trade...")
                        time.sleep(10)
                    
                    self.place_test_strangle()
                    
                    if self.position:
                        print("\nMonitoring position...")
                
                # If in position, check for exit
                else:
                    self.check_and_close()
                
                # Small delay
                time.sleep(2)
                
            except KeyboardInterrupt:
                print("\n\nStopped by user")
                if self.position:
                    print("Closing position...")
                    self.order_mgr.close_strangle(
                        self.position['call'],
                        self.position['put']
                    )
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(5)
        
        print(f"\n{'='*60}")
        print(f"COMPLETE - Executed {self.trades_executed} trades")
        print("="*60)

def main():
    strategy = SimpleTestStrategy()
    strategy.run(max_trades=2)

if __name__ == "__main__":
    main()