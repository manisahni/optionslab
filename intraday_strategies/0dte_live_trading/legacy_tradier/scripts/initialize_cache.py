#!/usr/bin/env python3
"""
Initialize Tradier Market Data Cache
Downloads historical data and sets up the cache database
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tradier.core.cache_manager import TradierCacheManager
from tradier.core.client import TradierClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Initialize Tradier market data cache')
    parser.add_argument('--days', type=int, default=20, 
                       help='Number of days of history to load (default: 20)')
    parser.add_argument('--force', action='store_true',
                       help='Force reload even if cache exists')
    parser.add_argument('--env', choices=['sandbox', 'production'], default='sandbox',
                       help='Tradier environment (default: sandbox)')
    parser.add_argument('--start-updater', action='store_true',
                       help='Start real-time updater after initialization')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 TRADIER MARKET DATA CACHE INITIALIZATION")
    print("="*60)
    print(f"Environment: {args.env}")
    print(f"Days of history: {args.days}")
    print(f"Force reload: {args.force}")
    print()
    
    # Create client and cache manager
    client = TradierClient(env=args.env)
    cache_manager = TradierCacheManager(client)
    
    # Initialize cache
    print("Initializing cache...")
    results = cache_manager.initialize_cache(days_back=args.days, force=args.force)
    
    print("\n✅ Cache Initialization Results:")
    print(f"  - SPY records loaded: {results['spy_records']:,}")
    print(f"  - Date range: {results['loaded_from']} to {results['loaded_to']}")
    print(f"  - Cache existed: {results['cache_exists']}")
    
    # Validate data integrity
    print("\n🔍 Validating data integrity...")
    validation = cache_manager.validate_data_integrity()
    
    if validation['has_gaps']:
        print(f"  ⚠️ Found {len(validation['gaps'])} gaps in data")
        for gap in validation['gaps'][:5]:  # Show first 5 gaps
            print(f"    - Gap at {gap['timestamp']}")
    else:
        print("  ✅ No gaps found in data")
    
    if validation['duplicate_count'] > 0:
        print(f"  ⚠️ Found {validation['duplicate_count']} duplicate records")
    else:
        print("  ✅ No duplicates found")
    
    # Get cache statistics
    print("\n📊 Cache Statistics:")
    stats = cache_manager.get_cache_statistics()
    print(f"  - Total SPY records: {stats.get('total_spy_records', 0):,}")
    print(f"  - Total options records: {stats.get('total_options_records', 0):,}")
    print(f"  - Trading days cached: {stats.get('trading_days', 0)}")
    
    if stats.get('data_age_seconds'):
        age_minutes = stats['data_age_seconds'] / 60
        freshness = "✅ FRESH" if stats.get('data_fresh') else "⚠️ STALE"
        print(f"  - Data age: {age_minutes:.1f} minutes ({freshness})")
    
    # Get today's stats
    print("\n📈 Today's Market Data:")
    today_stats = cache_manager.get_intraday_stats()
    if today_stats and today_stats.get('open'):
        print(f"  - Open: ${today_stats['open']:.2f}")
        print(f"  - Last: ${today_stats.get('last', 0):.2f}")
        print(f"  - High: ${today_stats['daily_high']:.2f}")
        print(f"  - Low: ${today_stats['daily_low']:.2f}")
        if 'change_pct' in today_stats:
            print(f"  - Change: {today_stats['change']:.2f} ({today_stats['change_pct']:.2f}%)")
        print(f"  - Volume: {today_stats.get('total_volume', 0):,}")
        print(f"  - Bars: {today_stats['bar_count']}")
    else:
        print("  No data available for today")
    
    # Start real-time updater if requested
    if args.start_updater:
        print("\n🔄 Starting real-time updater...")
        cache_manager.start_realtime_updates()
        print("Real-time updates started (10-second intervals)")
        print("\nPress Ctrl+C to stop...")
        
        try:
            import time
            while True:
                time.sleep(60)
                # Print status every minute
                status = cache_manager.updater.get_status()
                if status['last_update']:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Last update: {status['last_update']}")
        except KeyboardInterrupt:
            print("\nStopping updater...")
            cache_manager.stop_realtime_updates()
    
    print("\n✅ Cache initialization complete!")
    print("Database location: tradier/database/market_data.db")


if __name__ == "__main__":
    main()