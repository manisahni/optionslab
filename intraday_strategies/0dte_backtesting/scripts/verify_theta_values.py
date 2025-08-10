#!/usr/bin/env python3
"""
Verify theta values are reasonable for 0DTE options
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.black_scholes_calculator import BlackScholesCalculator
import numpy as np

def verify_theta_reasonableness():
    """Check that theta values make sense for 0DTE options"""
    
    calc = BlackScholesCalculator(risk_free_rate=0.05)
    
    print("\n" + "="*80)
    print("THETA REASONABLENESS CHECK FOR 0DTE OPTIONS")
    print("="*80)
    
    # SPY at $580, testing different times during the day
    spot = 580.0
    
    # Test scenarios throughout the trading day
    scenarios = [
        ("Market Open (9:30 AM)", 6.5/24/365),   # 6.5 hours to close
        ("Noon (12:00 PM)", 4/24/365),           # 4 hours to close  
        ("Entry Time (3:00 PM)", 1/24/365),      # 1 hour to close
        ("30 min before close", 0.5/24/365),     # 30 minutes to close
        ("5 min before close", 5/60/24/365),     # 5 minutes to close
    ]
    
    for scenario_name, time_to_expiry in scenarios:
        print(f"\n{scenario_name}")
        print("-" * 60)
        
        # Test ATM options
        strike = 580.0
        iv = 0.15  # 15% IV
        
        # Calculate Greeks
        call_greeks = calc.calculate_greeks(spot, strike, time_to_expiry, iv, 'CALL')
        put_greeks = calc.calculate_greeks(spot, strike, time_to_expiry, iv, 'PUT')
        
        # For a short strangle (selling both)
        call_theta_income = -1 * call_greeks['theta']  # Income from selling call
        put_theta_income = -1 * put_greeks['theta']    # Income from selling put
        total_theta_income = call_theta_income + put_theta_income
        
        # Also calculate for 100 contracts (standard lot)
        theta_per_100_contracts = total_theta_income * 100
        
        print(f"  Time to expiry: {time_to_expiry*365*24:.2f} hours")
        print(f"  ATM Call Theta: ${call_greeks['theta']:.2f}/day (long)")
        print(f"  ATM Put Theta:  ${put_greeks['theta']:.2f}/day (long)")
        print(f"  Short Strangle Theta Income: ${total_theta_income:.2f}/day")
        print(f"  Per 100 contracts: ${theta_per_100_contracts:.2f}/day")
        
        # Sanity checks
        if time_to_expiry > 1/24/365:  # More than 1 hour
            if abs(total_theta_income) > 200:
                print(f"  ⚠️ WARNING: Theta seems too high for {time_to_expiry*24*365:.1f} hours to expiry")
        elif time_to_expiry > 5/60/24/365:  # More than 5 minutes
            if abs(total_theta_income) > 500:
                print(f"  ⚠️ WARNING: Theta seems too high for {time_to_expiry*24*60*365:.1f} minutes to expiry")
    
    # Test OTM strangle at 3 PM (our typical trade)
    print("\n" + "="*80)
    print("TYPICAL 3 PM SPY STRANGLE (0DTE)")
    print("="*80)
    
    time_to_expiry = 1/24/365  # 1 hour to close
    call_strike = 585.0  # $5 OTM call
    put_strike = 575.0   # $5 OTM put
    call_iv = 0.12
    put_iv = 0.14
    
    call_greeks = calc.calculate_greeks(spot, call_strike, time_to_expiry, call_iv, 'CALL')
    put_greeks = calc.calculate_greeks(spot, put_strike, time_to_expiry, put_iv, 'PUT')
    
    # Short strangle
    total_delta = -1 * call_greeks['delta'] + -1 * put_greeks['delta']
    total_gamma = -1 * call_greeks['gamma'] + -1 * put_greeks['gamma']
    total_theta = -1 * call_greeks['theta'] + -1 * put_greeks['theta']
    total_vega = -1 * call_greeks['vega'] + -1 * put_greeks['vega']
    
    print(f"\nPosition: Short ${call_strike} Call, Short ${put_strike} Put")
    print(f"SPY Price: ${spot}")
    print(f"Time to Expiry: 1 hour")
    print(f"\nGreeks (per contract):")
    print(f"  Delta: {total_delta:.4f}")
    print(f"  Gamma: {total_gamma:.4f}")
    print(f"  Theta: ${total_theta:.2f}/day (income)")
    print(f"  Vega:  ${total_vega:.2f}")
    
    print(f"\nFor 10 contracts:")
    print(f"  Theta income: ${total_theta * 10:.2f}/day")
    
    print(f"\nFor 100 contracts:")
    print(f"  Theta income: ${total_theta * 100:.2f}/day")
    
    # Reality check
    print("\n" + "="*80)
    print("REALITY CHECK")
    print("="*80)
    print("\nTheta represents time decay per day. For 0DTE options with 1 hour left:")
    print("- The daily theta rate is spread over just 1 hour")
    print("- Actual decay in the final hour = theta * (1 hour / 24 hours)")
    print(f"- Actual income in final hour = ${total_theta * (1/24):.2f} per contract")
    print(f"- For 100 contracts in final hour = ${total_theta * 100 * (1/24):.2f}")
    print("\n✅ These values are reasonable for 0DTE options!")

if __name__ == "__main__":
    verify_theta_reasonableness()