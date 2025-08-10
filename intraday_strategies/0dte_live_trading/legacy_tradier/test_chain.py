#!/usr/bin/env python3
import sys
sys.path.append("/Users/nish_macbook/0dte/tradier")
from core import TradierClient, OptionsManager
from datetime import date

client = TradierClient(env="sandbox")
options_mgr = OptionsManager(client)

# Try to get option chain
print("Getting 0DTE options...")
chain = client.get_option_chains("SPY", date.today().strftime("%Y-%m-%d"))

if chain and "options" in chain:
    options = chain["options"].get("option", [])
    print(f"Found {len(options)} options")
    
    # Try to find strikes
    print("\nFinding strangle strikes...")
    strikes = options_mgr.find_strangle_strikes("SPY", target_delta=0.10, dte=0)
    if strikes:
        call, put = strikes
        print(f"Call: {call['symbol']} at ${call['strike']}")
        print(f"Put: {put['symbol']} at ${put['strike']}")
        
        # Get quotes
        print("\nGetting quotes...")
        quotes = options_mgr.get_strangle_quotes(call['symbol'], put['symbol'])
        if quotes:
            print(f"Call bid/ask: ${quotes['call']['bid']:.2f}/${quotes['call']['ask']:.2f}")
            print(f"Put bid/ask: ${quotes['put']['bid']:.2f}/${quotes['put']['ask']:.2f}")
    else:
        print("No strikes found")
else:
    print("No chain found")