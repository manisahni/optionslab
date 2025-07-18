#!/usr/bin/env python3
"""
Simple test script to validate data loading functionality
"""
import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def test_data_loader_basic():
    """Test basic data loader functionality"""
    print("🔍 Testing SPYDataLoader basic functionality...")
    
    try:
        from data_loader import SPYDataLoader
        print("✅ Successfully imported SPYDataLoader")
    except ImportError as e:
        print(f"❌ Failed to import SPYDataLoader: {e}")
        return False
    
    try:
        loader = SPYDataLoader()
        print("✅ Successfully created SPYDataLoader instance")
    except Exception as e:
        print(f"❌ Failed to create SPYDataLoader: {e}")
        return False
    
    try:
        dates = loader.get_available_dates()
        print(f"✅ Found {len(dates)} available dates from {dates[0]} to {dates[-1]}")
    except Exception as e:
        print(f"❌ Failed to get available dates: {e}")
        return False
    
    if not dates:
        print("❌ No dates available")
        return False
    
    # Test loading a single date
    test_date = dates[0]
    print(f"🔍 Testing data load for {test_date}...")
    
    try:
        df = loader.load_date(test_date)
        print(f"✅ Successfully loaded data for {test_date}")
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   DTE range: {df['dte'].min()} to {df['dte'].max()}")
        print(f"   Underlying price: ${df['underlying_price'].iloc[0]:.2f}")
    except Exception as e:
        print(f"❌ Failed to load data for {test_date}: {e}")
        return False
    
    # Test finding options by delta
    print(f"🔍 Testing delta-based option selection...")
    
    try:
        call_option = loader.find_option_by_delta(test_date, 0.30, 'C', 10, 45)
        if call_option is not None:
            print(f"✅ Found 30-delta call option:")
            print(f"   Strike: ${call_option['strike']:.0f}")
            print(f"   Delta: {call_option['delta']:.3f}")
            print(f"   DTE: {call_option['dte']}")
            print(f"   Mid price: ${call_option['mid_price']:.2f}")
        else:
            print("⚠️  No 30-delta call option found")
    except Exception as e:
        print(f"❌ Failed to find option by delta: {e}")
        return False
    
    print("✅ All basic data loading tests passed!")
    return True

def test_import_paths():
    """Test that all required modules can be imported"""
    print("🔍 Testing import paths...")
    
    modules_to_test = [
        'data_loader',
        'portfolio_manager',
        'strategy_base',
        'strategies.simple_strategies',
        'config',
        'cli_utils',
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ Successfully imported {module_name}")
        except ImportError as e:
            print(f"❌ Failed to import {module_name}: {e}")
            return False
    
    print("✅ All import tests passed!")
    return True

def main():
    """Run all tests"""
    print("🚀 Starting diagnostic tests...")
    print("=" * 50)
    
    success = True
    
    # Test 1: Import paths
    if not test_import_paths():
        success = False
    
    print()
    
    # Test 2: Data loading
    if not test_data_loader_basic():
        success = False
    
    print()
    print("=" * 50)
    
    if success:
        print("🎉 All tests passed! The system should be ready for backtesting.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)