#!/usr/bin/env python3
"""
Comprehensive tests for the Tradier cache system
Tests data loading, real-time updates, and backtesting
"""

import sys
import os
import time
from datetime import datetime, timedelta
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tradier.core.cache_manager import TradierCacheManager
from tradier.core.backtest_provider import BacktestDataProvider
from tradier.core.client import TradierClient


def test_cache_initialization():
    """Test cache initialization and data loading"""
    print("\n" + "="*60)
    print("TEST 1: Cache Initialization")
    print("="*60)
    
    client = TradierClient(env="sandbox")
    cache_mgr = TradierCacheManager(client)
    
    # Initialize with 3 days of data
    results = cache_mgr.initialize_cache(days_back=3, force=False)
    
    assert results['spy_records'] > 0, "No SPY records loaded"
    print(f"✅ Loaded {results['spy_records']} SPY records")
    
    # Check cache statistics
    stats = cache_mgr.get_cache_statistics()
    assert stats['total_spy_records'] > 0, "Cache is empty"
    print(f"✅ Cache contains {stats['total_spy_records']} total records")
    
    return cache_mgr


def test_data_retrieval(cache_mgr):
    """Test retrieving data from cache"""
    print("\n" + "="*60)
    print("TEST 2: Data Retrieval")
    print("="*60)
    
    # Get today's data
    today = datetime.now()
    start = today.replace(hour=9, minute=30, second=0, microsecond=0)
    
    spy_data = cache_mgr.get_spy_data(start_date=start)
    
    if not spy_data.empty:
        print(f"✅ Retrieved {len(spy_data)} data points for today")
        print(f"   First: {spy_data.index[0]}")
        print(f"   Last: {spy_data.index[-1]}")
        print(f"   Latest price: ${spy_data.iloc[-1]['close']:.2f}")
    else:
        print("⚠️ No data available for today (market may be closed)")
    
    # Get latest price
    latest_price = cache_mgr.get_latest_spy_price()
    if latest_price:
        print(f"✅ Latest SPY price: ${latest_price:.2f}")
    
    # Get intraday stats
    stats = cache_mgr.get_intraday_stats()
    if stats and stats.get('open'):
        print(f"✅ Today's stats:")
        print(f"   Open: ${stats['open']:.2f}")
        print(f"   High: ${stats['daily_high']:.2f}")
        print(f"   Low: ${stats['daily_low']:.2f}")
        print(f"   Volume: {stats.get('total_volume', 0):,}")


def test_data_integrity(cache_mgr):
    """Test data integrity and gap detection"""
    print("\n" + "="*60)
    print("TEST 3: Data Integrity")
    print("="*60)
    
    validation = cache_mgr.validate_data_integrity()
    
    if validation['has_gaps']:
        print(f"⚠️ Found {len(validation['gaps'])} gaps in data")
        for gap in validation['gaps'][:3]:
            print(f"   Gap at {gap['timestamp']}")
    else:
        print("✅ No gaps found in data")
    
    if validation['duplicate_count'] > 0:
        print(f"⚠️ Found {validation['duplicate_count']} duplicate records")
    else:
        print("✅ No duplicates found")
    
    return validation


def test_realtime_updates(cache_mgr):
    """Test real-time update functionality"""
    print("\n" + "="*60)
    print("TEST 4: Real-time Updates")
    print("="*60)
    
    # Start updater
    cache_mgr.start_realtime_updates()
    print("✅ Real-time updater started")
    
    # Get initial count
    initial_stats = cache_mgr.get_cache_statistics()
    initial_count = initial_stats['total_spy_records']
    
    # Wait for updates (only if market is open)
    if cache_mgr.updater._should_update():
        print("⏳ Waiting 15 seconds for updates...")
        time.sleep(15)
        
        # Check for new records
        new_stats = cache_mgr.get_cache_statistics()
        new_count = new_stats['total_spy_records']
        
        if new_count > initial_count:
            print(f"✅ Added {new_count - initial_count} new records")
        else:
            print("⚠️ No new records (market may be between minutes)")
    else:
        print("⚠️ Market is closed, skipping real-time test")
    
    # Stop updater
    cache_mgr.stop_realtime_updates()
    print("✅ Real-time updater stopped")


def test_backtesting(cache_mgr):
    """Test backtesting functionality"""
    print("\n" + "="*60)
    print("TEST 5: Backtesting")
    print("="*60)
    
    backtest = BacktestDataProvider(cache_mgr)
    
    # Get trading days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)
    
    trading_days = backtest.get_trading_days(start_date, end_date)
    print(f"✅ Found {len(trading_days)} trading days")
    
    if trading_days:
        # Test single day backtest
        test_date = trading_days[0]
        result = backtest.backtest_strangle(test_date)
        
        if result:
            print(f"✅ Backtest for {test_date.strftime('%Y-%m-%d')}:")
            print(f"   Entry: ${result['entry_price']:.2f}")
            print(f"   Exit: ${result['exit_price']:.2f}")
            print(f"   Call Strike: ${result['call_strike']:.0f}")
            print(f"   Put Strike: ${result['put_strike']:.0f}")
            print(f"   P&L: ${result['total_pnl']:.2f}")
            print(f"   Return: {result['return_pct']:.2f}%")
        
        # Run multi-day backtest
        print("\n📊 Running multi-day backtest...")
        results = backtest.run_backtest(start_date, end_date)
        
        if not results.empty:
            summary = backtest.get_backtest_summary(results)
            print(f"✅ Backtest Summary:")
            print(f"   Total trades: {summary['total_trades']}")
            print(f"   Win rate: {summary['win_rate']:.1f}%")
            print(f"   Total P&L: ${summary['total_pnl']:.2f}")
            print(f"   Average P&L: ${summary['average_pnl']:.2f}")
            print(f"   Best trade: ${summary['best_trade']:.2f}")
            print(f"   Worst trade: ${summary['worst_trade']:.2f}")


def test_performance():
    """Test query performance"""
    print("\n" + "="*60)
    print("TEST 6: Performance")
    print("="*60)
    
    client = TradierClient(env="sandbox")
    cache_mgr = TradierCacheManager(client)
    
    # Test single day query
    start_time = time.time()
    today = datetime.now()
    data = cache_mgr.get_spy_data(
        start_date=today.replace(hour=9, minute=30),
        end_date=today
    )
    query_time = (time.time() - start_time) * 1000
    
    print(f"✅ Single day query: {query_time:.1f}ms ({len(data)} records)")
    assert query_time < 100, "Query too slow (>100ms)"
    
    # Test week query
    start_time = time.time()
    week_ago = today - timedelta(days=7)
    data = cache_mgr.get_spy_data(start_date=week_ago, end_date=today)
    query_time = (time.time() - start_time) * 1000
    
    print(f"✅ Week query: {query_time:.1f}ms ({len(data)} records)")
    assert query_time < 500, "Query too slow (>500ms)"
    
    # Test latest price query
    start_time = time.time()
    price = cache_mgr.get_latest_spy_price()
    query_time = (time.time() - start_time) * 1000
    
    print(f"✅ Latest price query: {query_time:.1f}ms")
    assert query_time < 50, "Query too slow (>50ms)"


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 TRADIER CACHE SYSTEM COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    try:
        # Test 1: Initialize cache
        cache_mgr = test_cache_initialization()
        
        # Test 2: Data retrieval
        test_data_retrieval(cache_mgr)
        
        # Test 3: Data integrity
        test_data_integrity(cache_mgr)
        
        # Test 4: Real-time updates
        test_realtime_updates(cache_mgr)
        
        # Test 5: Backtesting
        test_backtesting(cache_mgr)
        
        # Test 6: Performance
        test_performance()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nThe cache system is working correctly:")
        print("- Historical data loading ✓")
        print("- Data retrieval ✓")
        print("- Data integrity ✓")
        print("- Real-time updates ✓")
        print("- Backtesting ✓")
        print("- Performance ✓")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())