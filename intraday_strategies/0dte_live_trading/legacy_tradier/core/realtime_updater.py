"""
Real-time Data Updater for Tradier
Updates market data cache every 10 seconds during market hours
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import signal
import sys

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_manager
from core.client import TradierClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealtimeUpdater:
    """Updates market data in real-time during market hours"""
    
    def __init__(self, client: Optional[TradierClient] = None, update_interval: int = 10):
        """Initialize the real-time updater
        
        Args:
            client: Tradier API client instance
            update_interval: Update interval in seconds (default: 10)
        """
        self.client = client or TradierClient(env="sandbox")
        self.db = get_db_manager()
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        self.last_update = None
        
        # Setup signal handlers for graceful shutdown only in main thread
        try:
            import threading
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
        except:
            # Signal handling not available in this context
            pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("Shutdown signal received, stopping updater...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start the real-time updater thread"""
        if self.running:
            logger.warning("Updater is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info(f"Real-time updater started (interval: {self.update_interval}s)")
    
    def stop(self):
        """Stop the real-time updater"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Real-time updater stopped")
    
    def _update_loop(self):
        """Main update loop that runs in separate thread"""
        while self.running:
            try:
                # Check if market is open
                if self._should_update():
                    start_time = time.time()
                    records_added = self._perform_update()
                    duration = int((time.time() - start_time) * 1000)
                    
                    # Log update
                    self._log_update('realtime', records_added, duration, 'success')
                    
                    if records_added > 0:
                        logger.info(f"Added {records_added} new records in {duration}ms")
                
                # Wait for next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Update error: {e}")
                self._log_update('realtime', 0, 0, 'error', str(e))
                time.sleep(self.update_interval)
    
    def _should_update(self) -> bool:
        """Check if we should perform an update
        
        Returns:
            True if market is open or recently closed
        """
        now = datetime.now()
        
        # Check if market is open
        if self.client.is_market_open():
            return True
        
        # Also update for 30 minutes after market close
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if now.hour >= 16 and (now - market_close).seconds < 1800:
            return True
        
        # Update during pre-market (8:00 AM - 9:30 AM)
        if 8 <= now.hour < 9 or (now.hour == 9 and now.minute < 30):
            return True
        
        return False
    
    def _perform_update(self) -> int:
        """Perform a single update cycle
        
        Returns:
            Number of new records added
        """
        records_added = 0
        
        # Get the latest timestamp in database
        last_timestamp = self._get_latest_timestamp()
        
        # Calculate time range for update
        if last_timestamp:
            start_time = last_timestamp + timedelta(seconds=60)
        else:
            # If no data, get last hour
            start_time = datetime.now() - timedelta(hours=1)
        
        end_time = datetime.now()
        
        # Format times for API
        start_str = start_time.strftime("%Y-%m-%d %H:%M")
        end_str = end_time.strftime("%Y-%m-%d %H:%M")
        
        # Get SPY timesales data
        response = self.client.get_timesales(
            symbol="SPY",
            interval="1min",
            start=start_str,
            end=end_str,
            session_filter="all"
        )
        
        # Check response format more carefully
        if response and isinstance(response, dict):
            if 'series' in response and isinstance(response['series'], dict):
                if 'data' in response['series'] and isinstance(response['series']['data'], list):
                    records_added = self._store_incremental_data(response['series']['data'])
                else:
                    logger.debug(f"No data in response series: {response.get('series', {})}")
            else:
                logger.debug(f"Invalid response format: {type(response)}")
        else:
            logger.debug("Empty or invalid response from API")
        
        # Update positions if we have them
        if records_added > 0:
            self._update_active_options()
        
        self.last_update = datetime.now()
        return records_added
    
    def _get_latest_timestamp(self) -> Optional[datetime]:
        """Get the latest timestamp in the database
        
        Returns:
            Latest timestamp or None if no data
        """
        query = "SELECT MAX(timestamp) as latest FROM spy_prices"
        result = self.db.execute_query(query)
        
        if result and result[0]['latest']:
            return datetime.fromisoformat(result[0]['latest'])
        return None
    
    def _store_incremental_data(self, data: List[Dict]) -> int:
        """Store incremental data updates
        
        Args:
            data: List of timesales data points
            
        Returns:
            Number of new records added
        """
        if not data:
            return 0
        
        records = []
        for item in data:
            # Skip if item is not a dict
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item: {type(item)}")
                continue
                
            # Parse timestamp
            time_str = item.get('time')
            if not time_str:
                logger.warning(f"Missing 'time' field in item: {item}")
                continue
                
            try:
                timestamp = datetime.fromisoformat(time_str.replace('T', ' ').replace('Z', ''))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid timestamp format: {time_str}, error: {e}")
                continue
            
            # Determine session type
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
        
        # Insert into database (ignore duplicates)
        query = """
            INSERT OR IGNORE INTO spy_prices 
            (timestamp, open, high, low, close, volume, vwap, session_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute_many(query, records)
        
        # Count actual insertions
        return self._count_new_records(records)
    
    def _count_new_records(self, records: List) -> int:
        """Count how many records were actually new
        
        Args:
            records: List of record tuples
            
        Returns:
            Number of new records
        """
        if not records:
            return 0
        
        timestamps = [r[0] for r in records]
        placeholders = ','.join('?' * len(timestamps))
        
        query = f"""
            SELECT COUNT(*) as count 
            FROM spy_prices 
            WHERE timestamp IN ({placeholders})
        """
        
        result = self.db.execute_query(query, timestamps)
        existing = result[0]['count'] if result else 0
        
        return len(records) - existing
    
    def _update_active_options(self):
        """Update options data for active positions"""
        # This will be implemented when we have active positions to track
        # For now, it's a placeholder for future enhancement
        pass
    
    def _log_update(self, update_type: str, records: int, duration: int, 
                   status: str, error: Optional[str] = None):
        """Log update to database
        
        Args:
            update_type: Type of update
            records: Number of records added
            duration: Duration in milliseconds
            status: Status of update
            error: Error message if any
        """
        query = """
            INSERT INTO update_log 
            (update_type, records_added, duration_ms, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        """
        
        self.db.execute_query(query, (update_type, records, duration, status, error))
    
    def get_status(self) -> Dict:
        """Get current updater status
        
        Returns:
            Dictionary with status information
        """
        return {
            'running': self.running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'update_interval': self.update_interval,
            'market_open': self.client.is_market_open(),
            'should_update': self._should_update()
        }


class UpdaterDaemon:
    """Daemon process for continuous updates"""
    
    def __init__(self, update_interval: int = 10):
        """Initialize the daemon
        
        Args:
            update_interval: Update interval in seconds
        """
        self.updater = RealtimeUpdater(update_interval=update_interval)
    
    def run(self):
        """Run the daemon process"""
        logger.info("Starting realtime updater daemon...")
        
        try:
            self.updater.start()
            
            # Keep the main thread alive
            while True:
                status = self.updater.get_status()
                logger.info(f"Updater status: {status}")
                time.sleep(60)  # Log status every minute
                
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by user")
        finally:
            self.updater.stop()
            logger.info("Daemon stopped")


if __name__ == "__main__":
    # Run as standalone daemon
    daemon = UpdaterDaemon(update_interval=10)
    daemon.run()