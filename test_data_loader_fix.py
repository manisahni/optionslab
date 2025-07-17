#!/usr/bin/env python3
"""
Test the fixed data loader to verify it can load parquet files
"""

import sys
sys.path.append('spy_backtester')

from data_loader import SPYDataLoader
from pathlib import Path

def test_data_loader():
    """Test if the data loader can now successfully load files"""
    print("🧪 Testing Fixed Data Loader")
    print("=" * 40)
    
    # Initialize data loader
    data_dir = Path("spy_options_downloader/spy_options_parquet")
    loader = SPYDataLoader(data_dir)
    
    # Get available dates
    dates = loader.get_available_dates()
    print(f"📅 Found {len(dates)} available dates")
    
    if not dates:
        print("❌ No dates available")
        return False
    
    # Test loading a few sample dates
    test_dates = dates[:3]  # Test first 3 dates
    
    success_count = 0
    
    for date in test_dates:
        print(f"\n🔍 Testing date: {date}")
        try:
            df = loader.load_date(date)
            print(f"✅ Success! Loaded {len(df)} rows, {len(df.columns)} columns")
            print(f"   Date range: DTE {df['dte'].min()}-{df['dte'].max()}")
            print(f"   Strike range: ${df['strike'].min():.0f}-${df['strike'].max():.0f}")
            print(f"   Underlying: ${df['underlying_price'].iloc[0]:.2f}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Failed: {e}")
            continue
    
    print(f"\n📊 Results: {success_count}/{len(test_dates)} successful")
    
    if success_count > 0:
        print("🎉 Data loader is working!")
        
        # Test finding options by delta
        print(f"\n🎯 Testing delta-based option selection for {test_dates[0]}")
        try:
            option = loader.find_option_by_delta(test_dates[0], 0.30, 'P', 10, 45)
            if option is not None:
                print(f"✅ Found 30-delta put:")
                print(f"   Strike: ${option['strike']:.0f}")
                print(f"   Delta: {option['delta']:.3f}")
                print(f"   DTE: {option['dte']}")
                print(f"   Mid Price: ${option['mid_price']:.2f}")
            else:
                print("⚠️ No suitable option found")
        except Exception as e:
            print(f"❌ Delta search failed: {e}")
        
        return True
    else:
        print("❌ Data loader still not working")
        return False

if __name__ == "__main__":
    success = test_data_loader()
    exit(0 if success else 1)