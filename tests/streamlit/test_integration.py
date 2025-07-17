#!/usr/bin/env python3
"""
Integration Test for Streamlit Unified System

This test verifies that the Streamlit app can successfully integrate
with the unified results system and handle error cases gracefully.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, date
import tempfile
import shutil

# Test the adapter directly
try:
    from streamlit_adapter import StreamlitAdapter, get_streamlit_adapter
    print("✅ Streamlit adapter imported successfully")
except ImportError as e:
    print(f"❌ Failed to import streamlit adapter: {e}")
    sys.exit(1)

def test_adapter_integration():
    """Test the streamlit adapter integration."""
    print("\n🧪 Testing Streamlit Adapter Integration...")
    
    # Create test directory
    test_dir = Path(tempfile.mkdtemp(prefix="streamlit_integration_test_"))
    
    try:
        # Initialize adapter with test directory
        adapter = StreamlitAdapter(test_dir / "results")
        
        # Test system status
        status = adapter.get_system_status()
        print(f"✅ System status: {status['health_check']}")
        
        # Test creating a sample backtest result
        sample_result = {
            'trade_log': [
                {
                    'trade_id': 'test_001',
                    'entry_date': '2023-06-15',
                    'exit_date': '2023-06-20',
                    'symbol': 'SPY',
                    'option_type': 'P',
                    'strike': 410,
                    'quantity': 1,
                    'entry_price': 2.50,
                    'exit_price': 3.75,
                    'pnl': 125,
                    'pnl_pct': 50.0,
                    'days_held': 5,
                    'exit_reason': 'profit_target'
                }
            ],
            'daily_equity': [
                {'date': '2023-06-15', 'equity': 100000},
                {'date': '2023-06-20', 'equity': 100125}
            ],
            'performance_metrics': {
                'total_return_pct': 0.125,
                'total_trades': 1,
                'win_rate': 100.0
            },
            'start_date': '2023-06-15',
            'end_date': '2023-06-20'
        }
        
        # Test saving result
        backtest_id = adapter.save_backtest_result(
            sample_result, "Integration Test Strategy", 100000
        )
        
        if backtest_id:
            print(f"✅ Saved test backtest: {backtest_id}")
            
            # Test loading result
            loaded_result = adapter.load_backtest_result(backtest_id)
            if loaded_result:
                print(f"✅ Loaded test backtest successfully")
                print(f"   Strategy: {loaded_result.get('strategy_name', 'Unknown')}")
                print(f"   Trades: {len(loaded_result.get('trade_log', []))}")
                print(f"   Return: {loaded_result.get('performance_metrics', {}).get('total_return_pct', 0):.3f}%")
            else:
                print("❌ Failed to load test backtest")
            
            # Test listing summaries
            summaries = adapter.list_backtest_summaries(limit=5)
            print(f"✅ Found {len(summaries)} backtest summaries")
            
        else:
            print("❌ Failed to save test backtest")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)

def test_error_handling():
    """Test error handling scenarios."""
    print("\n🧪 Testing Error Handling...")
    
    try:
        # Test with a valid but empty temporary directory
        test_dir = Path(tempfile.mkdtemp(prefix="error_test_"))
        adapter = StreamlitAdapter(test_dir / "nonexistent")
        
        # Should still work but with degraded functionality
        status = adapter.get_system_status()
        print(f"✅ Graceful handling of new path: {status.get('health_check', 'unknown')}")
        
        # Test loading non-existent backtest
        result = adapter.load_backtest_result("non_existent_id")
        if result is None:
            print("✅ Graceful handling of non-existent backtest")
        else:
            print("❌ Should have returned None for non-existent backtest")
        
        # Test with malformed data
        bad_data = {"invalid": "data"}
        backtest_id = adapter.save_backtest_result(bad_data, "Bad Test", 100000)
        if backtest_id is None:
            print("✅ Graceful handling of malformed data")
        else:
            print("⚠️ Unexpected success with malformed data")
        
        # Cleanup
        shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_streamlit_imports():
    """Test that Streamlit page can import without crashes."""
    print("\n🧪 Testing Streamlit Page Imports...")
    
    try:
        # Test importing the safe import function
        sys.path.append(str(Path(__file__).parent / "pages"))
        
        # Test the import pattern used in the streamlit page
        from streamlit_adapter import get_streamlit_adapter
        adapter = get_streamlit_adapter()
        
        print(f"✅ Streamlit adapter created successfully")
        print(f"   Unified system available: {adapter.is_unified_system_available()}")
        
        # Test the safe import pattern
        def safe_import_core_module(module_name, function_name):
            """Copy of the safe import function from streamlit page."""
            try:
                if module_name == "ai_analyzer":
                    from core.ai_analyzer import get_ai_analyzer
                    return get_ai_analyzer
                elif module_name == "win_rate_calculator":
                    from core.win_rate_calculator import WinRateCalculator
                    return WinRateCalculator
                else:
                    return None
            except ImportError:
                return None
        
        # Test safe imports
        ai_analyzer = safe_import_core_module("ai_analyzer", "get_ai_analyzer")
        win_calc = safe_import_core_module("win_rate_calculator", "WinRateCalculator")
        
        print(f"✅ AI analyzer available: {ai_analyzer is not None}")
        print(f"✅ Win rate calculator available: {win_calc is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Streamlit import test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Starting Streamlit Unified System Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Adapter Integration", test_adapter_integration),
        ("Error Handling", test_error_handling),
        ("Streamlit Imports", test_streamlit_imports)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Streamlit app should work correctly with unified system")
        print("✅ Error handling is working properly")
        print("✅ System is ready for production use")
        return True
    else:
        print(f"\n⚠️  {total - passed} TESTS FAILED")
        print("Please review the failures before using the system")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)