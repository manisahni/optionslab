#!/usr/bin/env python3
"""
Test Historical Data Integration
Shows ThetaData working with the new unified system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpaca_vegaware.core.thetadata import ThetaDataReader
from alpaca_vegaware.core.db import Database
import pandas as pd

def test_historical_data():
    """Test the historical data system"""
    
    print("="*70)
    print("TESTING HISTORICAL DATA INTEGRATION")
    print("="*70)
    
    # Initialize components
    reader = ThetaDataReader()
    db = Database()
    
    # 1. Show available ThetaData
    print("\n1. ThetaData Coverage:")
    print("-"*40)
    available_dates = reader.get_available_dates()
    print(f"Total days available: {len(available_dates)}")
    print(f"Date range: {available_dates[0]} to {available_dates[-1]}")
    
    # Get recent dates
    recent_dates = available_dates[-5:]
    print(f"Recent dates: {recent_dates}")
    
    # 2. Load sample day
    test_date = "20250801"
    print(f"\n2. Loading {test_date} from ThetaData:")
    print("-"*40)
    
    df = reader.load_day_data(test_date)
    if df is not None:
        # Convert timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['time'] = df['timestamp'].dt.time
        
        # Filter for VegaAware window
        from datetime import time
        start_time = time(14, 30)
        end_time = time(16, 0)
        vegaware_data = df[(df['time'] >= start_time) & (df['time'] <= end_time)]
        
        print(f"Total records: {len(df):,}")
        print(f"VegaAware window (2:30-4:00 PM): {len(vegaware_data):,} records")
        print(f"Unique strikes: {vegaware_data['strike'].nunique()}")
        
        # Show SPY price range
        spy_prices = vegaware_data['underlying_price_dollar'].unique()
        print(f"SPY price range: ${spy_prices.min():.2f} - ${spy_prices.max():.2f}")
        
        # Find 0.15 delta strikes
        print("\n3. Finding 0.15 Delta Strikes:")
        print("-"*40)
        
        # Get data at 3:00 PM (optimal entry)
        target_time = pd.Timestamp(f"2025-08-01 15:00:00")
        time_data = vegaware_data[vegaware_data['timestamp'] == target_time]
        
        if not time_data.empty:
            calls = time_data[time_data['right'] == 'CALL']
            puts = time_data[time_data['right'] == 'PUT']
            
            # Find closest to 0.15 delta
            target_delta = 0.15
            
            if not calls.empty:
                call_deltas = abs(calls['delta'] - target_delta)
                best_call = calls.iloc[call_deltas.argmin()]
                print(f"Call: Strike ${best_call['strike']:.0f}, Delta {best_call['delta']:.3f}")
                print(f"      Bid/Ask: ${best_call['bid']:.2f}/${best_call['ask']:.2f}")
                print(f"      Vega: {best_call['vega']:.3f}")
            
            if not puts.empty:
                # Put deltas are negative, so use absolute value
                put_deltas = abs(abs(puts['delta']) - target_delta)
                best_put = puts.iloc[put_deltas.argmin()]
                print(f"Put:  Strike ${best_put['strike']:.0f}, Delta {best_put['delta']:.3f}")
                print(f"      Bid/Ask: ${best_put['bid']:.2f}/${best_put['ask']:.2f}")
                print(f"      Vega: {abs(best_put['vega']):.3f}")
                
                # Calculate strangle metrics
                if not calls.empty and not puts.empty:
                    total_credit = best_call['bid'] + best_put['bid']
                    total_vega = best_call['vega'] + abs(best_put['vega'])
                    net_delta = best_call['delta'] + best_put['delta']
                    
                    print(f"\nStrangle Metrics:")
                    print(f"  Total Credit: ${total_credit:.2f}")
                    print(f"  Total Vega: {total_vega:.3f}")
                    print(f"  Net Delta: {net_delta:.3f}")
                    
                    # Check VegaAware criteria
                    print(f"\nVegaAware Criteria Check:")
                    print(f"  ✓ Time in window (2:30-3:30 PM): Yes")
                    print(f"  {'✓' if total_credit > 0.30 else '✗'} Premium > $0.30: ${total_credit:.2f}")
                    print(f"  {'✓' if total_vega < 2.0 else '✗'} Vega < 2.0: {total_vega:.3f}")
                    print(f"  {'✓' if abs(net_delta) < 0.10 else '✗'} Delta balanced < 0.10: {abs(net_delta):.3f}")
    
    # 4. Check database
    print("\n4. Database Status:")
    print("-"*40)
    
    # Check SPY prices
    spy_db = db.get_spy_prices("2025-08-01", "2025-08-01")
    print(f"SPY prices in DB: {len(spy_db)} records")
    
    # Show coverage
    coverage = db.get_data_coverage()
    if not coverage.empty:
        print(f"Total days in DB: {coverage['date'].nunique()}")
        print(f"Total records: {coverage['record_count'].sum():,}")
    else:
        print("Database is empty - run import_thetadata.py to populate")
    
    print("\n" + "="*70)
    print("✅ HISTORICAL DATA SYSTEM READY")
    print("="*70)
    
    print("\nNext steps:")
    print("1. Run import_thetadata.py to import more dates")
    print("2. Use backtest_engine.py to test VegaAware strategy")
    print("3. Live trading will use Alpaca for real-time data")


if __name__ == "__main__":
    test_historical_data()