#!/usr/bin/env python3
"""
Refresh Today's Market Data
Manually fetch and store today's SPY data including pre-market
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import logging
from core import TradierClient
from core.cache_manager import TradierCacheManager
from database import get_db_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def refresh_today():
    """Refresh today's market data"""
    
    print("\n" + "="*60)
    print("REFRESHING TODAY'S MARKET DATA")
    print("="*60)
    
    # Get current time
    now = datetime.now()
    print(f"\nCurrent time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if it's a market day
    if now.weekday() >= 5:
        print("\n⚠️  It's the weekend. No market data available.")
        return
    
    # Initialize client and cache manager
    print("\nInitializing Tradier client...")
    client = TradierClient(env="sandbox")
    cache_mgr = TradierCacheManager(client)
    db = get_db_manager()
    
    # Check existing data for today
    today_str = now.strftime('%Y-%m-%d')
    existing_query = """
        SELECT COUNT(*) as count, MIN(timestamp) as earliest, MAX(timestamp) as latest
        FROM spy_prices
        WHERE date(timestamp) = ?
    """
    result = db.execute_query(existing_query, (today_str,))
    
    if result and result[0]['count'] > 0:
        print(f"\nExisting data: {result[0]['count']} records")
        print(f"  Earliest: {result[0]['earliest']}")
        print(f"  Latest: {result[0]['latest']}")
    else:
        print("\nNo existing data for today")
    
    # Load today's data
    print("\n🔄 Fetching latest market data...")
    try:
        new_records = cache_mgr.loader.load_today_data()
        print(f"✅ Successfully loaded {new_records} new records")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Check updated data
    result = db.execute_query(existing_query, (today_str,))
    if result and result[0]['count'] > 0:
        print(f"\nUpdated data: {result[0]['count']} total records")
        print(f"  Earliest: {result[0]['earliest']}")
        print(f"  Latest: {result[0]['latest']}")
    
    # Show recent prices
    recent_query = """
        SELECT timestamp, open, high, low, close, volume
        FROM spy_prices
        WHERE date(timestamp) = ?
        ORDER BY timestamp DESC
        LIMIT 5
    """
    recent = db.execute_query(recent_query, (today_str,))
    
    if recent:
        print("\nMost recent prices:")
        print("Time                 | Open    | High    | Low     | Close   | Volume")
        print("-" * 75)
        for row in recent:
            time_str = row['timestamp'].split(' ')[1] if ' ' in row['timestamp'] else row['timestamp']
            print(f"{time_str:20} | {row['open']:7.2f} | {row['high']:7.2f} | {row['low']:7.2f} | {row['close']:7.2f} | {row['volume']:,}")
    
    # Start real-time updates
    print("\n🔄 Starting real-time updates (every 10 seconds)...")
    try:
        cache_mgr.start_realtime_updates()
        print("✅ Real-time updates started")
        print("\nDashboard should now show today's data!")
        print("Press Ctrl+C to stop real-time updates")
        
        # Keep running for real-time updates
        import time
        while True:
            time.sleep(10)
            # Get latest price
            latest = db.execute_query(
                "SELECT timestamp, close FROM spy_prices ORDER BY timestamp DESC LIMIT 1"
            )
            if latest:
                print(f"\rLatest: {latest[0]['timestamp']} - SPY: ${latest[0]['close']:.2f}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\nStopping real-time updates...")
        cache_mgr.stop_realtime_updates()
    except Exception as e:
        print(f"\nError with real-time updates: {e}")
    
    print("\n" + "="*60)
    print("Data refresh complete!")
    print("="*60)

if __name__ == "__main__":
    refresh_today()