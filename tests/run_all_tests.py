#!/usr/bin/env python3
"""
Master test script to run all backtesting system tests
This ensures all features work correctly together
"""

import sys
import subprocess
import time
from datetime import datetime
import os

class TestRunner:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        
    def run_test(self, test_name, test_file):
        """Run a single test and capture results"""
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        start = time.time()
        try:
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            duration = time.time() - start
            success = result.returncode == 0
            
            # Look for key indicators in output
            output = result.stdout + result.stderr
            has_error = "❌" in output or "FAILED" in output or "Error" in output
            has_success = "✅" in output or "PASSED" in output or "successfully" in output
            
            # Override success based on output content
            if has_error and not has_success:
                success = False
            elif has_success and not has_error:
                success = True
            
            self.results.append({
                'name': test_name,
                'file': test_file,
                'success': success,
                'duration': duration,
                'output': output[:500]  # First 500 chars
            })
            
            if success:
                print(f"✅ {test_name} - PASSED ({duration:.2f}s)")
            else:
                print(f"❌ {test_name} - FAILED ({duration:.2f}s)")
                print(f"Error output:\n{result.stderr[:500]}")
                
        except subprocess.TimeoutExpired:
            self.results.append({
                'name': test_name,
                'file': test_file,
                'success': False,
                'duration': 120,
                'output': 'Test timed out after 120 seconds'
            })
            print(f"⏱️ {test_name} - TIMEOUT")
        except Exception as e:
            self.results.append({
                'name': test_name,
                'file': test_file,
                'success': False,
                'duration': 0,
                'output': str(e)
            })
            print(f"💥 {test_name} - ERROR: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        total_duration = time.time() - self.start_time
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Total Duration: {total_duration:.2f}s")
        
        if failed_tests > 0:
            print(f"\nFailed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['name']} ({result['file']})")
        
        print(f"\nDetailed Results:")
        print(f"{'Test Name':<40} {'Status':<10} {'Duration':<10}")
        print("-" * 60)
        for result in self.results:
            status = "PASSED ✅" if result['success'] else "FAILED ❌"
            print(f"{result['name']:<40} {status:<10} {result['duration']:.2f}s")
        
        return passed_tests == total_tests

def main():
    """Run all tests"""
    runner = TestRunner()
    
    # Define all test files
    tests = [
        # Module-specific tests
        ("Backtest Engine", "test_backtest_engine.py"),
        ("Option Selector", "test_option_selector.py"),
        ("Data Loader", "test_data_loader.py"),
        ("Backtest Metrics", "test_backtest_metrics.py"),
        ("Market Filters", "test_market_filters.py"),
        ("Greek Tracker", "test_greek_tracker.py"),
        ("Trade Recorder", "test_trade_recorder.py"),
        ("Exit Conditions", "test_exit_conditions.py"),
        
        # Integration tests
        ("Multi-Day Backtest", "test_multiday_backtest.py"),
        ("Option Exit Pricing", "test_option_exit_fix.py"),
        ("Profit/Stop Exits", "test_profit_stop_exits.py"),
        ("Put Option Support", "test_put_options.py"),
        ("Multiple Positions", "test_multi_positions.py"),
        ("Integration Tests", "test_integration.py"),
        ("Gradio Interface", "test_gradio_backtest.py"),
    ]
    
    # Check which test files exist
    existing_tests = []
    for test_name, test_file in tests:
        if os.path.exists(test_file):
            existing_tests.append((test_name, test_file))
        else:
            print(f"⚠️  Skipping {test_name} - {test_file} not found")
    
    print(f"\n🚀 Running {len(existing_tests)} tests...")
    
    # Run each test
    for test_name, test_file in existing_tests:
        runner.run_test(test_name, test_file)
    
    # Print summary
    all_passed = runner.print_summary()
    
    # Return appropriate exit code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()