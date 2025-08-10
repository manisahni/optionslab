#!/usr/bin/env python3
"""
Comprehensive Cache Initialization for Dashboard
Downloads 21 days of SPY data, fills gaps, and generates Greeks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta, time as dt_time
import time
from typing import Dict, List, Tuple
import json
import pytz

from core import TradierClient
from core.cache_manager import TradierCacheManager
from core.greeks_calculator import GreeksCalculator
from core.historical_loader import HistoricalDataLoader
from database import get_db_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveCacheInitializer:
    """Initialize complete market data cache with progress tracking"""
    
    def __init__(self, client: TradierClient = None, days_back: int = 21):
        """Initialize the cache initializer
        
        Args:
            client: Tradier API client
            days_back: Number of days of history to load (default: 21)
        """
        self.client = client or TradierClient(env="sandbox")
        self.days_back = days_back
        self.db = get_db_manager()
        self.cache_mgr = TradierCacheManager(self.client)
        self.greeks_calc = GreeksCalculator()
        self.loader = HistoricalDataLoader(self.client)
        
        # Market operates in Eastern Time
        self.ET = pytz.timezone('US/Eastern')
        
        # Progress tracking
        self.progress = {
            'spy_data': {'status': 'pending', 'records': 0, 'gaps_filled': 0},
            'greeks_data': {'status': 'pending', 'records': 0},
            'options_data': {'status': 'pending', 'records': 0},
            'total_time': 0
        }
    
    def initialize_all(self) -> Dict:
        """Run complete initialization process
        
        Returns:
            Dictionary with initialization results
        """
        start_time = time.time()
        
        print("="*70)
        print("🚀 COMPREHENSIVE DASHBOARD DATA INITIALIZATION")
        print("="*70)
        print(f"Loading {self.days_back} days of market data...")
        print()
        
        # Step 1: Initialize SPY data
        self._initialize_spy_data()
        
        # Step 2: Fill any gaps
        self._fill_data_gaps()
        
        # Step 3: Generate Greeks data
        self._generate_greeks_data()
        
        # Step 4: Validate data integrity
        self._validate_data()
        
        self.progress['total_time'] = time.time() - start_time
        
        # Print summary
        self._print_summary()
        
        return self.progress
    
    def _initialize_spy_data(self):
        """Initialize SPY price data"""
        print("📊 Step 1: Loading SPY data...")
        self.progress['spy_data']['status'] = 'in_progress'
        
        # Check existing data
        existing_stats = self.db.execute_query(
            "SELECT COUNT(*) as count, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM spy_prices"
        )[0]
        
        if existing_stats['count'] > 0:
            earliest = datetime.fromisoformat(existing_stats['earliest'])
            latest = datetime.fromisoformat(existing_stats['latest'])
            days_loaded = (latest.date() - earliest.date()).days
            
            print(f"  Found {existing_stats['count']:,} existing records")
            print(f"  Date range: {earliest.date()} to {latest.date()} ({days_loaded} days)")
            
            # Check if we need more historical data
            target_start = datetime.now() - timedelta(days=self.days_back)
            if earliest.date() > target_start.date():
                print(f"  Loading additional history back to {target_start.date()}...")
                # Load more history
                self.cache_mgr.initialize_cache(days_back=self.days_back, force=False)
        else:
            print(f"  No existing data found. Loading {self.days_back} days...")
            self.cache_mgr.initialize_cache(days_back=self.days_back, force=True)
        
        # Get final count
        final_count = self.db.execute_query("SELECT COUNT(*) as count FROM spy_prices")[0]['count']
        self.progress['spy_data']['records'] = final_count
        self.progress['spy_data']['status'] = 'completed'
        print(f"  ✅ Loaded {final_count:,} SPY records")
    
    def _fill_data_gaps(self):
        """Fill any gaps in regular trading hours"""
        print("\n🔧 Step 2: Filling data gaps...")
        self.progress['spy_data']['status'] = 'filling_gaps'
        
        gaps_filled = 0
        
        # Get date range to check
        date_range = self.db.execute_query(
            "SELECT DISTINCT date(timestamp) as trading_date FROM spy_prices ORDER BY trading_date"
        )
        
        for row in date_range:
            trading_date = datetime.fromisoformat(row['trading_date'])
            
            # Skip weekends
            if trading_date.weekday() >= 5:
                continue
            
            # Check for gaps in regular hours (9:30 AM - 4:00 PM)
            market_open = trading_date.replace(hour=9, minute=30, second=0)
            market_close = trading_date.replace(hour=16, minute=0, second=0)
            
            # Get existing timestamps for this day
            existing = self.db.execute_query(
                """SELECT timestamp FROM spy_prices 
                   WHERE date(timestamp) = ? 
                   AND time(timestamp) >= '09:30:00' 
                   AND time(timestamp) <= '16:00:00'
                   ORDER BY timestamp""",
                (row['trading_date'],)
            )
            
            existing_times = set(row['timestamp'] for row in existing)
            
            # Generate expected timestamps (1-minute bars)
            expected_times = []
            current = market_open
            while current <= market_close:
                expected_times.append(current.strftime('%Y-%m-%d %H:%M:00'))
                current += timedelta(minutes=1)
            
            # Find missing timestamps
            missing = [ts for ts in expected_times if ts not in existing_times]
            
            if missing:
                print(f"  Found {len(missing)} gaps on {trading_date.date()}")
                gaps_filled += self._fetch_missing_data(missing)
        
        self.progress['spy_data']['gaps_filled'] = gaps_filled
        self.progress['spy_data']['status'] = 'completed'
        print(f"  ✅ Filled {gaps_filled} gaps in SPY data")
    
    def _fetch_missing_data(self, missing_timestamps: List[str]) -> int:
        """Fetch missing data from API
        
        Args:
            missing_timestamps: List of missing timestamp strings
            
        Returns:
            Number of records added
        """
        if not missing_timestamps:
            return 0
        
        # Convert to datetime objects and find ranges
        missing_dt = [datetime.fromisoformat(ts) for ts in missing_timestamps]
        missing_dt.sort()
        
        # Group into continuous ranges
        ranges = []
        start = missing_dt[0]
        end = missing_dt[0]
        
        for dt in missing_dt[1:]:
            if (dt - end).total_seconds() <= 120:  # Within 2 minutes
                end = dt
            else:
                ranges.append((start, end))
                start = dt
                end = dt
        ranges.append((start, end))
        
        records_added = 0
        
        for start, end in ranges:
            # Fetch from API
            response = self.client.get_timesales(
                symbol="SPY",
                interval="1min",
                start=start.strftime("%Y-%m-%d %H:%M"),
                end=end.strftime("%Y-%m-%d %H:%M"),
                session_filter="all"
            )
            
            if response and isinstance(response, dict) and 'series' in response:
                if 'data' in response.get('series', {}):
                    data = response['series']['data']
                    records = []
                    
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        
                        time_str = item.get('time', '')
                        if not time_str:
                            continue
                        
                        timestamp = datetime.fromisoformat(time_str.replace('T', ' ').replace('Z', ''))
                        hour = timestamp.hour
                        minute = timestamp.minute
                        session_type = 'regular' if (9 <= hour < 16 or (hour == 9 and minute >= 30)) else 'extended'
                        
                        records.append((
                            timestamp,
                            item.get('open', 0),
                            item.get('high', 0),
                            item.get('low', 0),
                            item.get('close', 0),
                            item.get('volume', 0),
                            item.get('vwap'),
                            session_type
                        ))
                    
                    if records:
                        query = """
                            INSERT OR IGNORE INTO spy_prices 
                            (timestamp, open, high, low, close, volume, vwap, session_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        self.db.execute_many(query, records)
                        records_added += len(records)
        
        return records_added
    
    def _generate_greeks_data(self):
        """Generate Greeks data for all trading days"""
        print("\n📈 Step 3: Generating Greeks data...")
        self.progress['greeks_data']['status'] = 'in_progress'
        
        # Get all trading days
        trading_days = self.db.execute_query(
            """SELECT DISTINCT date(timestamp) as trading_date 
               FROM spy_prices 
               WHERE session_type = 'regular'
               ORDER BY trading_date DESC
               LIMIT ?""",
            (self.days_back,)
        )
        
        total_greeks = 0
        
        for row in trading_days:
            trading_date = row['trading_date']
            print(f"  Generating Greeks for {trading_date}...")
            
            # Get SPY prices for this day
            prices = self.db.execute_query(
                """SELECT timestamp, close FROM spy_prices 
                   WHERE date(timestamp) = ? 
                   AND session_type = 'regular'
                   ORDER BY timestamp""",
                (trading_date,)
            )
            
            if not prices:
                continue
            
            # Generate Greeks for a simulated strangle
            day_greeks = self._calculate_day_greeks(prices, trading_date)
            total_greeks += len(day_greeks)
            
            # Store in database
            self._store_greeks_history(day_greeks)
        
        self.progress['greeks_data']['records'] = total_greeks
        self.progress['greeks_data']['status'] = 'completed'
        print(f"  ✅ Generated {total_greeks:,} Greeks data points")
    
    def _calculate_day_greeks(self, prices: List[Dict], trading_date: str) -> List[Dict]:
        """Calculate Greeks for one trading day
        
        Args:
            prices: List of price data for the day
            trading_date: Date string
            
        Returns:
            List of Greeks data points
        """
        greeks_data = []
        
        # Get opening price to determine strikes
        opening_price = prices[0]['close'] if prices else 630
        
        # Set strikes for strangle (slightly OTM)
        call_strike = round(opening_price + 2)
        put_strike = round(opening_price - 2)
        
        # Parse expiry date and set to 4 PM ET
        expiry_date = datetime.fromisoformat(trading_date).date()
        expiry = self.ET.localize(datetime.combine(expiry_date, dt_time(16, 0)))  # 4 PM ET
        
        for price_point in prices:
            timestamp = datetime.fromisoformat(price_point['timestamp'])
            # Localize timestamp to ET for proper calculation
            timestamp_et = self.ET.localize(timestamp)
            spot = price_point['close']
            
            # Calculate time to expiry
            tte = max((expiry - timestamp_et).total_seconds() / (365 * 24 * 3600), 1e-6)
            
            # Estimate IV based on time of day
            hour = timestamp.hour
            base_iv = 0.12  # 12% base IV for SPY
            if hour < 10:
                iv = base_iv * 1.3
            elif hour < 12:
                iv = base_iv * 1.1  
            elif hour < 14:
                iv = base_iv
            else:
                iv = base_iv * 0.9
            
            # Calculate Greeks for both legs
            call_greeks = self.greeks_calc.calculate_greeks(
                spot=spot,
                strike=call_strike,
                time_to_expiry=tte,
                volatility=iv,
                option_type='call'
            )
            
            put_greeks = self.greeks_calc.calculate_greeks(
                spot=spot,
                strike=put_strike,
                time_to_expiry=tte,
                volatility=iv,
                option_type='put'
            )
            
            # Combine for strangle position
            greeks_data.append({
                'timestamp': timestamp,
                'position_type': 'strangle',
                'underlying': 'SPY',
                'call_strike': call_strike,
                'put_strike': put_strike,
                'expiry': expiry.date(),
                'total_delta': call_greeks['delta'] + put_greeks['delta'],
                'total_gamma': call_greeks['gamma'] + put_greeks['gamma'],
                'total_theta': call_greeks['theta'] + put_greeks['theta'],
                'total_vega': call_greeks['vega'] + put_greeks['vega'],
                'total_rho': call_greeks.get('rho', 0) + put_greeks.get('rho', 0),
                'underlying_price': spot,
                'call_iv': iv,
                'put_iv': iv,
                'call_price': call_greeks.get('price', 1.0),
                'put_price': put_greeks.get('price', 1.0),
                'pnl': 0  # Would be calculated from entry prices
            })
        
        return greeks_data
    
    def _store_greeks_history(self, greeks_data: List[Dict]):
        """Store Greeks data in database
        
        Args:
            greeks_data: List of Greeks data points
        """
        if not greeks_data:
            return
        
        query = """
            INSERT OR REPLACE INTO greeks_history 
            (timestamp, position_type, underlying, call_strike, put_strike, expiry,
             total_delta, total_gamma, total_theta, total_vega, total_rho,
             underlying_price, call_iv, put_iv, call_price, put_price, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        records = [
            (
                d['timestamp'], d['position_type'], d['underlying'],
                d['call_strike'], d['put_strike'], d['expiry'],
                d['total_delta'], d['total_gamma'], d['total_theta'],
                d['total_vega'], d['total_rho'], d['underlying_price'],
                d['call_iv'], d['put_iv'], d['call_price'], d['put_price'], d['pnl']
            )
            for d in greeks_data
        ]
        
        self.db.execute_many(query, records)
    
    def _validate_data(self):
        """Validate data integrity"""
        print("\n🔍 Step 4: Validating data integrity...")
        
        # Check for gaps
        validation = self.cache_mgr.validate_data_integrity()
        
        if validation['has_gaps']:
            print(f"  ⚠️ Found {len(validation['gaps'])} remaining gaps")
        else:
            print("  ✅ No gaps in data")
        
        if validation['duplicate_count'] > 0:
            print(f"  ⚠️ Found {validation['duplicate_count']} duplicate records")
        else:
            print("  ✅ No duplicates found")
        
        # Check Greeks data
        greeks_count = self.db.execute_query(
            "SELECT COUNT(*) as count FROM greeks_history"
        )[0]['count']
        print(f"  ✅ {greeks_count:,} Greeks history records")
    
    def _print_summary(self):
        """Print initialization summary"""
        print("\n" + "="*70)
        print("✅ INITIALIZATION COMPLETE")
        print("="*70)
        
        # SPY data summary
        spy_stats = self.db.execute_query(
            """SELECT COUNT(*) as count, 
                      MIN(timestamp) as earliest,
                      MAX(timestamp) as latest,
                      COUNT(DISTINCT date(timestamp)) as days
               FROM spy_prices"""
        )[0]
        
        print(f"\n📊 SPY Data:")
        print(f"  Total records: {spy_stats['count']:,}")
        print(f"  Date range: {spy_stats['earliest'][:10]} to {spy_stats['latest'][:10]}")
        print(f"  Trading days: {spy_stats['days']}")
        print(f"  Gaps filled: {self.progress['spy_data']['gaps_filled']}")
        
        # Greeks data summary
        greeks_stats = self.db.execute_query(
            """SELECT COUNT(*) as count,
                      COUNT(DISTINCT date(timestamp)) as days,
                      MIN(timestamp) as earliest,
                      MAX(timestamp) as latest
               FROM greeks_history"""
        )[0]
        
        print(f"\n📈 Greeks Data:")
        print(f"  Total records: {greeks_stats['count']:,}")
        print(f"  Trading days: {greeks_stats['days']}")
        if greeks_stats['earliest']:
            print(f"  Date range: {greeks_stats['earliest'][:10]} to {greeks_stats['latest'][:10]}")
        
        # Options data summary
        options_count = self.db.execute_query(
            "SELECT COUNT(*) as count FROM options_data"
        )[0]['count']
        
        print(f"\n📋 Options Data:")
        print(f"  Total records: {options_count:,}")
        
        print(f"\n⏱️ Total time: {self.progress['total_time']:.1f} seconds")
        print("\n✅ Dashboard is ready with complete data!")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize comprehensive dashboard cache')
    parser.add_argument('--days', type=int, default=21,
                       help='Number of days of history (default: 21)')
    parser.add_argument('--env', choices=['sandbox', 'production'], default='sandbox',
                       help='Tradier environment (default: sandbox)')
    
    args = parser.parse_args()
    
    # Create client and initializer
    client = TradierClient(env=args.env)
    initializer = ComprehensiveCacheInitializer(client, days_back=args.days)
    
    # Run initialization
    results = initializer.initialize_all()
    
    return 0 if results['spy_data']['status'] == 'completed' else 1


if __name__ == "__main__":
    sys.exit(main())