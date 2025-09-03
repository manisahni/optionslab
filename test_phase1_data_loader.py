#!/usr/bin/env python3
"""
Phase 1.1 Test: Data Loader Verification
=======================================
Interactive test of enhanced data_loader.py functionality.
Tests single day data loading with detailed validation.
"""

import sys
import pandas as pd
from datetime import datetime
import traceback

print("=" * 60)
print("PHASE 1.1: DATA LOADER VERIFICATION TEST")
print("=" * 60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test results tracker
test_results = {
    'import_test': False,
    'file_loading': False, 
    'dte_calculation': False,
    'date_conversion': False,
    'strike_conversion': False
}

try:
    # TEST 1: Import Test
    print("🧪 TEST 1: Testing Import of Enhanced Data Loader")
    print("-" * 50)
    
    try:
        from optionslab.data_loader import load_data
        print("✅ PASS: Successfully imported enhanced data_loader")
        test_results['import_test'] = True
    except ImportError as e:
        print(f"❌ FAIL: Import error - {e}")
        print("🔧 This suggests path issues or missing files")
        raise
    
    print()
    
    # TEST 2: File Loading Test
    print("🧪 TEST 2: Testing Single Day Data Loading")
    print("-" * 50)
    
    # Test parameters
    TEST_DATE_START = "2024-01-02"
    TEST_DATE_END = "2024-01-02"  
    DATA_FILE = "/Users/nish_macbook/trading/daily-optionslab/data/spy_options/SPY_OPTIONS_2024_COMPLETE.parquet"
    
    print(f"📁 Loading: {DATA_FILE}")
    print(f"📅 Date range: {TEST_DATE_START} to {TEST_DATE_END}")
    
    try:
        data = load_data(DATA_FILE, TEST_DATE_START, TEST_DATE_END)
        
        if data is not None and len(data) > 0:
            print(f"✅ PASS: Data loaded successfully - {len(data):,} records")
            test_results['file_loading'] = True
        else:
            print("❌ FAIL: Data is None or empty")
            raise ValueError("No data returned from load_data")
            
    except Exception as e:
        print(f"❌ FAIL: Error loading data - {e}")
        print("🔧 This suggests file path or data format issues")
        raise
    
    print()
    
    # TEST 3: DTE Calculation Test
    print("🧪 TEST 3: Testing DTE (Days to Expiration) Calculation")
    print("-" * 50)
    
    try:
        if 'dte' in data.columns:
            dte_min = data['dte'].min()
            dte_max = data['dte'].max()
            dte_sample = data['dte'].head(10).tolist()
            
            print(f"📊 DTE column found: YES")
            print(f"📊 DTE range: {dte_min} to {dte_max} days")
            print(f"📊 DTE sample values: {dte_sample}")
            
            # Validation: DTE should be reasonable (LEAPs can go up to 3 years = ~1095 days)
            if dte_min >= -1 and dte_max <= 1100:  # Allow -1 for expired options, up to 1100 for long LEAPs
                print("✅ PASS: DTE values are in reasonable range")
                test_results['dte_calculation'] = True
            else:
                print("❌ FAIL: DTE values are unreasonable")
                print(f"🔧 Expected: -1 to 1100 days, Got: {dte_min} to {dte_max}")
        else:
            print("❌ FAIL: DTE column not found in data")
            print("🔧 Enhanced data_loader should automatically create DTE column")
            
    except Exception as e:
        print(f"❌ FAIL: Error checking DTE calculation - {e}")
        raise
    
    print()
    
    # TEST 4: Date Conversion Test
    print("🧪 TEST 4: Testing Date Conversion")
    print("-" * 50)
    
    try:
        date_type = str(data['date'].dtype)
        exp_type = str(data['expiration'].dtype) if 'expiration' in data.columns else "MISSING"
        
        print(f"📊 'date' column type: {date_type}")
        print(f"📊 'expiration' column type: {exp_type}")
        
        # Show sample dates
        if len(data) > 0:
            sample_date = data['date'].iloc[0]
            sample_exp = data['expiration'].iloc[0] if 'expiration' in data.columns else "MISSING"
            print(f"📊 Sample date: {sample_date}")
            print(f"📊 Sample expiration: {sample_exp}")
        
        # Validation: Should be datetime64[ns]
        if 'datetime64' in date_type and 'datetime64' in exp_type:
            print("✅ PASS: Date columns are properly converted to datetime")
            test_results['date_conversion'] = True
        else:
            print("❌ FAIL: Date columns are not datetime type")
            print(f"🔧 Expected: datetime64[ns], Got: date={date_type}, expiration={exp_type}")
            
    except Exception as e:
        print(f"❌ FAIL: Error checking date conversion - {e}")
        raise
    
    print()
    
    # TEST 5: Strike Conversion Test
    print("🧪 TEST 5: Testing Strike Price Conversion")
    print("-" * 50)
    
    try:
        if 'strike' in data.columns:
            strike_min = data['strike'].min()
            strike_max = data['strike'].max()
            strike_sample = data['strike'].head(10).tolist()
            
            print(f"📊 Strike range: ${strike_min:.2f} to ${strike_max:.2f}")
            print(f"📊 Sample strikes: {[f'${s:.2f}' for s in strike_sample[:5]]}")
            
            # Validation: SPY strikes should be in reasonable dollar range ($200-$700 typical)
            if 100 <= strike_min <= 1000 and 100 <= strike_max <= 1000:
                print("✅ PASS: Strike prices are in reasonable dollar range")
                test_results['strike_conversion'] = True
            else:
                print("❌ FAIL: Strike prices appear to be unconverted (still in cents?)")
                print(f"🔧 Expected: $100-$1000 range, Got: ${strike_min:.2f}-${strike_max:.2f}")
        else:
            print("❌ FAIL: Strike column not found")
            
    except Exception as e:
        print(f"❌ FAIL: Error checking strike conversion - {e}")
        raise
    
    print()
    
    # SUMMARY SECTION
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"✅ Tests Passed: {passed_tests}/{total_tests}")
    print()
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")
    
    print()
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Data loader is working correctly.")
        print("🚀 Ready to proceed to Phase 1.2 (Date Range Loading Test)")
    else:
        print("⚠️  SOME TESTS FAILED - Issues need to be fixed before proceeding")
        
    print()
    
    # DATA SAMPLE for Visual Verification
    print("📊 DATA SAMPLE (First 5 records for visual verification)")
    print("-" * 70)
    
    if len(data) > 0:
        sample_cols = ['date', 'expiration', 'strike', 'right', 'dte', 'close', 'delta']
        available_cols = [col for col in sample_cols if col in data.columns]
        sample_data = data[available_cols].head()
        
        print(sample_data.to_string())
    else:
        print("No data to display")
    
except Exception as e:
    print(f"💥 CRITICAL ERROR: {e}")
    print("\n🔧 Full traceback:")
    traceback.print_exc()
    print(f"\n⚠️  Test failed at step. Cannot proceed until this is resolved.")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")