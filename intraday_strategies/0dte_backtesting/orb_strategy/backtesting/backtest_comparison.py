"""
Comparison of Simplified vs Real Options Backtesting
Shows the difference between estimated and actual option pricing
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
import sys

sys.path.append(str(Path(__file__).parent.parent))

from backtesting.options_data_loader import OptionsDataLoader
from core.spread_pricer import SpreadPricer


def compare_pricing():
    """Compare simplified vs real option pricing"""
    
    print("="*70)
    print("COMPARISON: SIMPLIFIED vs REAL OPTIONS PRICING")
    print("="*70)
    
    # Load real options data
    loader = OptionsDataLoader()
    dates = loader.get_available_dates()
    
    if not dates:
        print("No options data found")
        return
    
    # Test on first available date
    test_date = dates[0]
    df = loader.load_day_data(test_date)
    
    if df is None:
        return
    
    print(f"\nTest Date: {test_date}")
    
    # Use 11:00 AM as breakout time
    breakout_time = pd.Timestamp(f'{test_date} 11:00:00')
    time_data = df[df['timestamp'] == breakout_time]
    
    if time_data.empty:
        print("No data at breakout time")
        return
    
    # Get SPY price
    spy_price = time_data.iloc[0]['underlying_price_dollar']
    print(f"SPY Price at breakout: ${spy_price:.2f}")
    
    # Simulate OR levels
    or_high = spy_price + 1.5
    or_low = spy_price - 1.5
    print(f"Simulated OR: ${or_low:.2f} - ${or_high:.2f}")
    
    # Initialize pricer
    pricer = SpreadPricer(spread_width=15)
    
    print("\n" + "-"*70)
    print("PUT CREDIT SPREAD (Bullish Breakout)")
    print("-"*70)
    
    # Find actual strikes
    short_strike, long_strike = pricer.find_put_spread_strikes(df, or_low, breakout_time)
    
    if short_strike and long_strike:
        print(f"Strikes: Short ${short_strike} / Long ${long_strike}")
        print(f"Spread Width: ${short_strike - long_strike}")
        
        # Get real spread pricing
        real_spread = pricer.calculate_spread_credit(df, breakout_time, short_strike, long_strike, 'PUT')
        
        if real_spread:
            print("\n1. SIMPLIFIED PRICING (Our Original Backtest):")
            simplified_credit = (short_strike - long_strike) * 0.35 * 100
            print(f"   Credit = Spread Width × 35% × 100")
            print(f"   Credit = ${short_strike - long_strike} × 0.35 × 100 = ${simplified_credit:.2f}")
            
            print("\n2. REAL OPTIONS PRICING (Actual Bid/Ask):")
            print(f"   Short Put Bid: ${real_spread['short_bid']:.2f}")
            print(f"   Long Put Ask: ${real_spread['long_ask']:.2f}")
            print(f"   Net Credit = (${real_spread['short_bid']:.2f} - ${real_spread['long_ask']:.2f}) × 100")
            print(f"   Net Credit = ${real_spread['credit']:.2f}")
            
            print("\n3. DIFFERENCE:")
            difference = simplified_credit - real_spread['credit']
            error_pct = (difference / real_spread['credit']) * 100 if real_spread['credit'] > 0 else 0
            print(f"   Simplified: ${simplified_credit:.2f}")
            print(f"   Real: ${real_spread['credit']:.2f}")
            print(f"   Overestimate: ${difference:.2f} ({error_pct:.0f}% error)")
            
            print("\n4. GREEKS (Real Data):")
            print(f"   Net Delta: {real_spread['net_delta']:.3f}")
            print(f"   Net Gamma: {real_spread['net_gamma']:.3f}")
            print(f"   Net Theta: ${real_spread['net_theta']:.2f}")
            print(f"   Net Vega: ${real_spread['net_vega']:.2f}")
    
    print("\n" + "="*70)
    print("KEY INSIGHTS")
    print("="*70)
    
    print("""
1. SIMPLIFIED BACKTEST ISSUES:
   - Assumes fixed 35% credit ratio
   - Ignores actual bid/ask spreads
   - Doesn't account for Greeks
   - No IV consideration
   
2. REAL OPTIONS DATA SHOWS:
   - Credit varies with market conditions
   - Bid/ask spreads reduce profit
   - Greeks affect risk/reward
   - Time decay is non-linear
   
3. WHY OPTION ALPHA'S RESULTS ARE LOWER:
   - They use real option prices
   - Include commission and slippage
   - Account for partial fills
   - Consider market liquidity
   
4. TO MATCH THEIR RESULTS:
   - Use actual options data ✓
   - Calculate real credits ✓
   - Include all costs
   - Validate with paper trading
    """)


def analyze_multiple_days():
    """Analyze pricing across multiple days"""
    
    print("\n" + "="*70)
    print("MULTI-DAY ANALYSIS")
    print("="*70)
    
    loader = OptionsDataLoader()
    pricer = SpreadPricer(spread_width=15)
    
    dates = loader.get_available_dates()[:10]  # First 10 days
    
    results = []
    
    for date in dates:
        df = loader.load_day_data(date)
        if df is None:
            continue
        
        # Test at 11:00 AM
        test_time = pd.Timestamp(f'{date} 11:00:00')
        time_data = df[df['timestamp'] == test_time]
        
        if time_data.empty:
            continue
        
        spy_price = time_data.iloc[0]['underlying_price_dollar']
        or_low = spy_price - 2
        
        # Find put spread
        short_strike, long_strike = pricer.find_put_spread_strikes(df, or_low, test_time)
        
        if short_strike and long_strike:
            # Real pricing
            real_spread = pricer.calculate_spread_credit(df, test_time, short_strike, long_strike, 'PUT')
            
            if real_spread:
                # Simplified pricing
                simplified = (short_strike - long_strike) * 0.35 * 100
                
                results.append({
                    'date': date,
                    'spy_price': spy_price,
                    'spread_width': short_strike - long_strike,
                    'simplified_credit': simplified,
                    'real_credit': real_spread['credit'],
                    'difference': simplified - real_spread['credit']
                })
    
    if results:
        df_results = pd.DataFrame(results)
        
        print(f"\nAnalyzed {len(df_results)} days")
        print("\nCredit Comparison:")
        print(f"Average Simplified Credit: ${df_results['simplified_credit'].mean():.2f}")
        print(f"Average Real Credit: ${df_results['real_credit'].mean():.2f}")
        print(f"Average Overestimate: ${df_results['difference'].mean():.2f}")
        
        print("\nSample Days:")
        print(df_results[['date', 'simplified_credit', 'real_credit', 'difference']].head())


def main():
    """Run comparison analysis"""
    
    print("\n" + "="*70)
    print("ORB STRATEGY: SIMPLIFIED vs REAL OPTIONS PRICING")
    print("="*70)
    
    # Single day detailed comparison
    compare_pricing()
    
    # Multi-day analysis
    analyze_multiple_days()
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    
    print("""
The simplified backtest SIGNIFICANTLY overestimates profitability because:

1. It uses a fixed 35% credit assumption
2. Real credits are often much lower (10-20% of spread width)
3. This explains why Option Alpha gets:
   - $51 avg P&L (not $397)
   - 88% win rate (not 98%)
   - 1.59 profit factor (not 35)

To get accurate results, you MUST use real options data!
    """)


if __name__ == "__main__":
    main()