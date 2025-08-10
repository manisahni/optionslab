"""
Tradier Cache Manager
Central interface for managing cached market data
"""

import logging
import pandas as pd
from datetime import datetime, timedelta, time
from typing import Optional, Dict, List, Tuple
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_manager
from core.client import TradierClient
from core.historical_loader import HistoricalDataLoader
from core.realtime_updater import RealtimeUpdater

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradierCacheManager:
    """Manages cached market data with historical loading and real-time updates"""
    
    def __init__(self, client: Optional[TradierClient] = None):
        """Initialize the cache manager
        
        Args:
            client: Tradier API client instance
        """
        self.client = client or TradierClient(env="sandbox")
        self.db = get_db_manager()
        self.loader = HistoricalDataLoader(self.client)
        self.updater = RealtimeUpdater(self.client, update_interval=10)
        self._initialized = False
    
    def initialize_cache(self, days_back: int = 21, force: bool = False) -> Dict:
        """Initialize cache with historical data
        
        Args:
            days_back: Number of days of history to load
            force: Force reload even if data exists
            
        Returns:
            Dictionary with initialization results
        """
        logger.info("Initializing market data cache...")
        
        results = {
            'spy_records': 0,
            'options_records': 0,
            'cache_exists': False,
            'loaded_from': None,
            'loaded_to': None
        }
        
        # Check existing cache
        stats = self.db.get_stats()
        if stats and stats.get('total_spy_records', 0) > 0 and not force:
            results['cache_exists'] = True
            results['spy_records'] = stats['total_spy_records']
            results['loaded_from'] = stats.get('earliest_data')
            results['loaded_to'] = stats.get('latest_data')
            logger.info(f"Cache already contains {results['spy_records']} records")
            
            # Just update today's data
            new_records = self.loader.load_today_data()
            results['spy_records'] += new_records
            
        else:
            # Load historical data
            logger.info(f"Loading {days_back} days of historical data...")
            results['spy_records'] = self.loader.load_spy_history(days_back)
            
            # Get date range
            min_date, max_date = self.loader.get_cached_date_range()
            results['loaded_from'] = min_date.isoformat() if min_date else None
            results['loaded_to'] = max_date.isoformat() if max_date else None
        
        self._initialized = True
        logger.info(f"Cache initialization complete: {results}")
        return results
    
    def start_realtime_updates(self):
        """Start real-time data updates"""
        if not self._initialized:
            self.initialize_cache()
        
        self.updater.start()
        logger.info("Real-time updates started")
    
    def stop_realtime_updates(self):
        """Stop real-time data updates"""
        self.updater.stop()
        logger.info("Real-time updates stopped")
    
    def get_spy_data(self, start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None,
                     session_type: str = 'all') -> pd.DataFrame:
        """Get SPY price data for specified date range
        
        Args:
            start_date: Start date (default: today's market open)
            end_date: End date (default: now)
            session_type: 'all', 'regular', or 'extended'
            
        Returns:
            DataFrame with SPY price data
        """
        # Default to today's trading session
        if start_date is None:
            start_date = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
        if end_date is None:
            end_date = datetime.now()
        
        # Build query
        query = """
            SELECT timestamp, open, high, low, close, volume, vwap, session_type
            FROM spy_prices
            WHERE timestamp >= ? AND timestamp <= ?
        """
        
        params = [start_date, end_date]
        
        if session_type != 'all':
            query += " AND session_type = ?"
            params.append(session_type)
        
        query += " ORDER BY timestamp"
        
        # Execute query
        rows = self.db.execute_query(query, tuple(params))
        
        # Convert to DataFrame
        if rows:
            df = pd.DataFrame([dict(row) for row in rows])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
        
        return pd.DataFrame()
    
    def get_options_data(self, strikes: List[float], 
                        expiry: Optional[str] = None,
                        timestamp: Optional[datetime] = None) -> pd.DataFrame:
        """Get options data for specified strikes
        
        Args:
            strikes: List of strike prices
            expiry: Expiration date (default: today)
            timestamp: Specific timestamp (default: latest)
            
        Returns:
            DataFrame with options data
        """
        if expiry is None:
            expiry = datetime.now().strftime("%Y-%m-%d")
        
        if timestamp is None:
            # Get latest available timestamp
            query = "SELECT MAX(timestamp) as latest FROM options_data WHERE expiry = ?"
            result = self.db.execute_query(query, (expiry,))
            if result and result[0]['latest']:
                timestamp = result[0]['latest']
            else:
                timestamp = datetime.now()
        
        # Build query
        placeholders = ','.join('?' * len(strikes))
        query = f"""
            SELECT *
            FROM options_data
            WHERE strike IN ({placeholders})
            AND expiry = ?
            AND timestamp = ?
            ORDER BY strike, option_type
        """
        
        params = strikes + [expiry, timestamp]
        rows = self.db.execute_query(query, params)
        
        if rows:
            df = pd.DataFrame([dict(row) for row in rows])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        
        return pd.DataFrame()
    
    def get_latest_spy_price(self) -> Optional[float]:
        """Get the latest SPY price
        
        Returns:
            Latest SPY close price or None
        """
        query = """
            SELECT close 
            FROM spy_prices 
            ORDER BY timestamp DESC 
            LIMIT 1
        """
        
        result = self.db.execute_query(query)
        if result:
            return result[0]['close']
        return None
    
    def get_intraday_stats(self, date: Optional[datetime] = None) -> Dict:
        """Get intraday statistics for a given date
        
        Args:
            date: Date to get stats for (default: today)
            
        Returns:
            Dictionary with intraday statistics
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        query = """
            SELECT 
                MIN(low) as daily_low,
                MAX(high) as daily_high,
                MIN(CASE WHEN time(timestamp) = '09:30:00' THEN open END) as open,
                MAX(CASE WHEN time(timestamp) <= time('now') THEN close END) as last,
                SUM(volume) as total_volume,
                COUNT(*) as bar_count,
                AVG(volume) as avg_volume
            FROM spy_prices
            WHERE date(timestamp) = ?
            AND session_type = 'regular'
        """
        
        result = self.db.execute_query(query, (date_str,))
        
        if result:
            stats = dict(result[0])
            
            # Calculate additional metrics
            if stats['open'] and stats['last']:
                stats['change'] = stats['last'] - stats['open']
                stats['change_pct'] = (stats['change'] / stats['open']) * 100
                stats['range'] = stats['daily_high'] - stats['daily_low']
            
            return stats
        
        return {}
    
    def get_cache_statistics(self) -> Dict:
        """Get comprehensive cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        stats = self.db.get_stats()
        
        # Add updater status
        if self.updater:
            stats['updater_status'] = self.updater.get_status()
        
        # Add data freshness
        if stats.get('latest_data'):
            latest = datetime.fromisoformat(stats['latest_data'])
            age_seconds = (datetime.now() - latest).total_seconds()
            stats['data_age_seconds'] = age_seconds
            stats['data_fresh'] = age_seconds < 60  # Fresh if less than 1 minute old
        
        return stats
    
    def export_to_csv(self, start_date: datetime, end_date: datetime, 
                     output_dir: str = "exports") -> str:
        """Export cached data to CSV files
        
        Args:
            start_date: Start date for export
            end_date: End date for export
            output_dir: Directory to save CSV files
            
        Returns:
            Path to export directory
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Export SPY data
        spy_data = self.get_spy_data(start_date, end_date)
        spy_file = os.path.join(output_dir, f"spy_data_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv")
        spy_data.to_csv(spy_file)
        logger.info(f"Exported {len(spy_data)} SPY records to {spy_file}")
        
        return output_dir
    
    def validate_data_integrity(self) -> Dict:
        """Validate data integrity and check for gaps
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'has_gaps': False,
            'gaps': [],
            'duplicate_count': 0,
            'missing_sessions': []
        }
        
        # Check for time gaps in SPY data
        query = """
            WITH time_diff AS (
                SELECT 
                    timestamp,
                    LAG(timestamp) OVER (ORDER BY timestamp) as prev_timestamp,
                    (julianday(timestamp) - julianday(LAG(timestamp) OVER (ORDER BY timestamp))) * 24 * 60 as minutes_diff
                FROM spy_prices
                WHERE session_type = 'regular'
            )
            SELECT timestamp, prev_timestamp, minutes_diff
            FROM time_diff
            WHERE minutes_diff > 1.5  -- More than 1.5 minutes gap
            AND time(timestamp) > '09:31:00'
            AND time(prev_timestamp) < '15:59:00'
        """
        
        gaps = self.db.execute_query(query)
        if gaps:
            results['has_gaps'] = True
            results['gaps'] = [dict(row) for row in gaps]
        
        # Check for duplicates
        query = """
            SELECT timestamp, COUNT(*) as count
            FROM spy_prices
            GROUP BY timestamp
            HAVING COUNT(*) > 1
        """
        
        duplicates = self.db.execute_query(query)
        results['duplicate_count'] = len(duplicates) if duplicates else 0
        
        return results


# Convenience function for quick access
def get_cache_manager(client: Optional[TradierClient] = None) -> TradierCacheManager:
    """Get or create cache manager instance
    
    Args:
        client: Optional Tradier client
        
    Returns:
        TradierCacheManager instance
    """
    return TradierCacheManager(client)