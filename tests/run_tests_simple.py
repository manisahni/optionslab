#!/usr/bin/env python3
"""
Simple test runner that works without pytest
"""

import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_test_function(func, module_name):
    """Run a single test function"""
    try:
        func()
        print(f"  ✅ {func.__name__}")
        return True
    except AssertionError as e:
        print(f"  ❌ {func.__name__}: Assertion failed - {e}")
        return False
    except Exception as e:
        print(f"  ❌ {func.__name__}: {type(e).__name__} - {e}")
        traceback.print_exc()
        return False

def run_module_tests(module_name, test_module):
    """Run all test functions in a module"""
    print(f"\n📦 Testing {module_name}")
    print("-" * 50)
    
    passed = 0
    failed = 0
    
    # Find all test functions
    test_functions = [
        (name, func) for name, func in vars(test_module).items()
        if name.startswith('test_') and callable(func)
    ]
    
    for name, func in test_functions:
        if run_test_function(func, module_name):
            passed += 1
        else:
            failed += 1
    
    return passed, failed

def main():
    """Run all tests"""
    print("🧪 Running OptionsLab Tests (No pytest)")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    # Import and run test modules
    test_modules = [
        ("Option Selector", "test_option_selector"),
        ("Greek Tracker", "test_greek_tracker"),
        ("Backtest Metrics", "test_backtest_metrics"),
        ("Data Loader", "test_data_loader"),
    ]
    
    for module_name, module_file in test_modules:
        try:
            test_module = __import__(f"tests.{module_file}", fromlist=[''])
            passed, failed = run_module_tests(module_name, test_module)
            total_passed += passed
            total_failed += failed
        except Exception as e:
            print(f"\n❌ Failed to import {module_file}: {e}")
            total_failed += 1
    
    print("\n" + "=" * 60)
    print(f"Total: {total_passed + total_failed} tests")
    print(f"Passed: {total_passed} ✅")
    print(f"Failed: {total_failed} ❌")
    
    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
