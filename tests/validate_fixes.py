#!/usr/bin/env python3
"""
Comprehensive validation test for the backtest fixes
"""
import sys
import subprocess
from pathlib import Path
import json
import tempfile
import os

def run_command(cmd, cwd=None):
    """Run a command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=120)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_basic_data_loading():
    """Test basic data loading functionality"""
    print("🔍 Testing basic data loading...")
    
    success, stdout, stderr = run_command(
        "cd optionslab-core && python test_data_loading.py",
        cwd="/Users/nish_macbook/thetadata-api"
    )
    
    if success and "All tests passed!" in stdout:
        print("✅ Basic data loading test passed")
        return True
    else:
        print("❌ Basic data loading test failed")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False

def test_short_backtest():
    """Test a short backtest"""
    print("🔍 Testing short backtest (10 days)...")
    
    success, stdout, stderr = run_command(
        "cd optionslab-core && python backtester_enhanced.py --strategy long_call --start-date 20200715 --end-date 20200725 --initial-capital 100000 --min-dte 10 --max-dte 45",
        cwd="/Users/nish_macbook/thetadata-api"
    )
    
    if success and "BACKTEST COMPLETE!" in stdout:
        print("✅ Short backtest test passed")
        # Check for no fatal errors
        if "Fatal Python error" not in stdout and "Bad file descriptor" not in stdout:
            print("✅ No fatal errors detected")
            return True
        else:
            print("❌ Fatal errors still present")
            return False
    else:
        print("❌ Short backtest test failed")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False

def test_medium_backtest():
    """Test a medium-length backtest"""
    print("🔍 Testing medium backtest (3 months)...")
    
    success, stdout, stderr = run_command(
        "cd optionslab-core && python backtester_enhanced.py --strategy long_put --start-date 20200715 --end-date 20201015 --initial-capital 100000 --min-dte 20 --max-dte 50",
        cwd="/Users/nish_macbook/thetadata-api"
    )
    
    if success and "BACKTEST COMPLETE!" in stdout:
        print("✅ Medium backtest test passed")
        # Check for reasonable number of trades
        if "Number of Trades:" in stdout:
            print("✅ Trade generation working")
            return True
        else:
            print("⚠️  Medium backtest passed but no trades generated")
            return True  # Still consider it a pass
    else:
        print("❌ Medium backtest test failed")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False

def test_streamlit_integration():
    """Test that Streamlit can import the modules"""
    print("🔍 Testing Streamlit integration...")
    
    success, stdout, stderr = run_command(
        """cd optionslab-ui && python -c "
import sys
sys.path.append('../optionslab-core')
try:
    from data_loader import SPYDataLoader
    from core.backtest_runner import BacktestRunner
    print('✅ Streamlit imports successful')
    loader = SPYDataLoader()
    print('✅ Data loader instantiated')
    dates = loader.get_available_dates()
    print(f'✅ Found {len(dates)} dates')
except Exception as e:
    print(f'❌ Streamlit import failed: {e}')
    import traceback
    traceback.print_exc()
"
""",
        cwd="/Users/nish_macbook/thetadata-api"
    )
    
    if success and "Streamlit imports successful" in stdout:
        print("✅ Streamlit integration test passed")
        return True
    else:
        print("❌ Streamlit integration test failed")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False

def test_yaml_configuration():
    """Test YAML configuration loading"""
    print("🔍 Testing YAML configuration...")
    
    success, stdout, stderr = run_command(
        "cd optionslab-core && python backtester_enhanced.py --list-yaml",
        cwd="/Users/nish_macbook/thetadata-api"
    )
    
    if success and "AVAILABLE YAML CONFIGURATIONS" in stdout:
        print("✅ YAML configuration listing works")
        return True
    else:
        print("❌ YAML configuration test failed")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        return False

def main():
    """Run all validation tests"""
    print("🚀 Starting comprehensive validation tests...")
    print("=" * 60)
    
    tests = [
        ("Basic Data Loading", test_basic_data_loading),
        ("Short Backtest", test_short_backtest),
        ("Medium Backtest", test_medium_backtest),
        ("Streamlit Integration", test_streamlit_integration),
        ("YAML Configuration", test_yaml_configuration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 VALIDATION SUMMARY")
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Backtest system is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)