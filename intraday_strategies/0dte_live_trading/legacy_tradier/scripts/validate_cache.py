#!/usr/bin/env python3
"""
Validate Tradier Cache System
Quick validation that everything is working
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tradier.core.cache_manager import TradierCacheManager
from tradier.core.client import TradierClient


def main():
    print("="*60)
    print("🔍 TRADIER CACHE SYSTEM VALIDATION")
    print("="*60)
    
    # Initialize cache
    print("\n1. Initializing cache system...")
    client = TradierClient(env="sandbox")
    cache_mgr = TradierCacheManager(client)
    
    # Check if cache exists
    stats = cache_mgr.get_cache_statistics()
    print(f"   ✓ Cache contains {stats.get('total_spy_records', 0):,} SPY records")
    
    # Get today's data
    print("\n2. Retrieving today's data...")
    today = datetime.now()
    start = today.replace(hour=9, minute=30, second=0, microsecond=0)
    spy_data = cache_mgr.get_spy_data(start_date=start, session_type='regular')
    
    if not spy_data.empty:
        print(f"   ✓ Retrieved {len(spy_data)} bars for today")
        print(f"   ✓ Latest price: ${spy_data.iloc[-1]['close']:.2f}")
        print(f"   ✓ Today's range: ${spy_data['low'].min():.2f} - ${spy_data['high'].max():.2f}")
    else:
        print("   ⚠️ No data for today (market may be closed)")
    
    # Check data freshness
    print("\n3. Checking data freshness...")
    if stats.get('data_age_seconds'):
        age_minutes = stats['data_age_seconds'] / 60
        if stats.get('data_fresh'):
            print(f"   ✓ Data is FRESH (age: {abs(age_minutes):.1f} minutes)")
        else:
            print(f"   ⚠️ Data is STALE (age: {abs(age_minutes):.1f} minutes)")
    
    # Test query performance
    print("\n4. Testing query performance...")
    import time
    
    start_time = time.time()
    latest_price = cache_mgr.get_latest_spy_price()
    query_time = (time.time() - start_time) * 1000
    
    print(f"   ✓ Latest price query: {query_time:.1f}ms")
    
    start_time = time.time()
    week_data = cache_mgr.get_spy_data(
        start_date=today - timedelta(days=7),
        end_date=today
    )
    query_time = (time.time() - start_time) * 1000
    
    print(f"   ✓ Week data query: {query_time:.1f}ms ({len(week_data)} records)")
    
    # Validate data integrity
    print("\n5. Validating data integrity...")
    validation = cache_mgr.validate_data_integrity()
    
    if validation['has_gaps']:
        print(f"   ⚠️ Found {len(validation['gaps'])} gaps")
    else:
        print("   ✓ No gaps in data")
    
    if validation['duplicate_count'] > 0:
        print(f"   ⚠️ Found {validation['duplicate_count']} duplicates")
    else:
        print("   ✓ No duplicate records")
    
    # Summary
    print("\n" + "="*60)
    print("✅ VALIDATION COMPLETE")
    print("="*60)
    print("\nCache System Status:")
    print(f"  • Total Records: {stats.get('total_spy_records', 0):,}")
    print(f"  • Trading Days: {stats.get('trading_days', 0)}")
    print(f"  • Date Range: {stats.get('earliest_data', 'N/A')} to {stats.get('latest_data', 'N/A')}")
    print(f"  • Database: tradier/database/market_data.db")
    
    print("\nNext Steps:")
    print("  1. Start real-time updater: python tradier/scripts/initialize_cache.py --start-updater")
    print("  2. Run dashboard: python tradier/dashboard/gradio_dashboard.py")
    print("  3. Monitor positions: python tradier/scripts/live_monitor.py")


if __name__ == "__main__":
    main()