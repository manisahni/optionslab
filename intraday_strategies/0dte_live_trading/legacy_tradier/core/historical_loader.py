"""
Historical Data Loader for Tradier
Downloads and caches historical market data in SQLite database
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from tqdm import tqdm
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_manager
from core.client import TradierClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """Loads historical data from Tradier API into local cache"""
    
    def __init__(self, client: Optional[TradierClient] = None):
        """Initialize the historical data loader
        
        Args:
            client: Tradier API client instance
        """
        self.client = client or TradierClient(env="sandbox")
        self.db = get_db_manager()
        
    def load_spy_history(self, days_back: int = 20) -> int:
        """Load historical SPY data for specified number of days
        
        Args:
            days_back: Number of days of history to load
            
        Returns:
            Number of records loaded
        """
        logger.info(f"Loading {days_back} days of SPY historical data...")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for API
        start_str = start_date.strftime("%Y-%m-%d 09:30")
        end_str = end_date.strftime("%Y-%m-%d 16:00")
        
        logger.info(f"Fetching SPY data from {start_str} to {end_str}")
        
        # Get timesales data
        response = self.client.get_timesales(
            symbol="SPY",
            interval="1min",
            start=start_str,
            end=end_str,
            session_filter="all"
        )
        
        if not response or 'series' not in response:
            logger.error("Failed to get timesales data")
            return 0
        
        # Parse and store data
        records_added = self._store_spy_timesales(response['series'])
        
        # Update metadata
        self._update_data_status(start_date, end_date, 'spy')
        
        logger.info(f"Loaded {records_added} SPY price records")
        return records_added
    
    def _store_spy_timesales(self, series_data: Dict) -> int:
        """Store timesales data in database
        
        Args:
            series_data: Time series data from API
            
        Returns:
            Number of records stored
        """
        if not series_data or 'data' not in series_data:
            return 0
        
        records = []
        for item in series_data['data']:
            # Parse timestamp
            timestamp = datetime.fromisoformat(item['time'].replace('T', ' ').replace('Z', ''))
            
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
        
        # Insert into database
        query = """
            INSERT OR IGNORE INTO spy_prices 
            (timestamp, open, high, low, close, volume, vwap, session_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute_many(query, records)
        return len(records)
    
    def load_options_history(self, symbol: str, strikes: List[float], 
                           expiry: str, days_back: int = 5) -> int:
        """Load historical options data for given strikes
        
        Args:
            symbol: Underlying symbol (e.g., "SPY")
            strikes: List of strike prices to load
            expiry: Expiration date (YYYY-MM-DD)
            days_back: Number of days of history
            
        Returns:
            Number of records loaded
        """
        logger.info(f"Loading options history for {len(strikes)} strikes...")
        
        total_records = 0
        
        for strike in tqdm(strikes, desc="Loading strikes"):
            for option_type in ['call', 'put']:
                # Build option symbol (e.g., SPY250807C00636000)
                option_symbol = self._build_option_symbol(symbol, expiry, strike, option_type)
                
                # Get historical data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                response = self.client.get_history(
                    symbol=option_symbol,
                    interval="daily",
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d")
                )
                
                if response and 'history' in response:
                    records = self._store_options_history(
                        response['history'], 
                        option_symbol, 
                        symbol, 
                        strike, 
                        option_type, 
                        expiry
                    )
                    total_records += records
                
                # Rate limiting
                time.sleep(0.1)
        
        logger.info(f"Loaded {total_records} options records")
        return total_records
    
    def _build_option_symbol(self, underlying: str, expiry: str, 
                            strike: float, option_type: str) -> str:
        """Build OCC option symbol
        
        Args:
            underlying: Underlying symbol
            expiry: Expiration date (YYYY-MM-DD)
            strike: Strike price
            option_type: 'call' or 'put'
            
        Returns:
            OCC option symbol
        """
        # Convert date format
        exp_date = datetime.strptime(expiry, "%Y-%m-%d")
        date_str = exp_date.strftime("%y%m%d")
        
        # Format strike (multiply by 1000, pad to 8 digits)
        strike_str = f"{int(strike * 1000):08d}"
        
        # Option type letter
        type_letter = 'C' if option_type == 'call' else 'P'
        
        return f"{underlying}{date_str}{type_letter}{strike_str}"
    
    def _store_options_history(self, history_data: Dict, symbol: str, 
                              underlying: str, strike: float, 
                              option_type: str, expiry: str) -> int:
        """Store options historical data
        
        Args:
            history_data: Historical data from API
            symbol: Option symbol
            underlying: Underlying symbol
            strike: Strike price
            option_type: 'call' or 'put'
            expiry: Expiration date
            
        Returns:
            Number of records stored
        """
        if not history_data or 'day' not in history_data:
            return 0
        
        records = []
        for day in history_data['day']:
            # For daily data, use market close time
            date_str = day['date']
            timestamp = datetime.strptime(f"{date_str} 16:00:00", "%Y-%m-%d %H:%M:%S")
            
            records.append((
                timestamp,
                symbol,
                underlying,
                strike,
                option_type,
                expiry,
                None,  # bid
                None,  # ask
                day.get('close'),  # last
                day.get('volume', 0),
                day.get('open_interest', 0),
                None,  # IV
                None,  # delta
                None,  # gamma
                None,  # theta
                None,  # vega
                None   # rho
            ))
        
        query = """
            INSERT OR IGNORE INTO options_data
            (timestamp, symbol, underlying, strike, option_type, expiry,
             bid, ask, last, volume, open_interest, iv,
             delta, gamma, theta, vega, rho)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.db.execute_many(query, records)
        return len(records)
    
    def _update_data_status(self, start_date: datetime, end_date: datetime, data_type: str):
        """Update data status metadata
        
        Args:
            start_date: Start of loaded data
            end_date: End of loaded data
            data_type: 'spy' or 'options'
        """
        # Get all dates in range
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Weekday
                date_str = current.strftime("%Y-%m-%d")
                
                if data_type == 'spy':
                    query = """
                        INSERT OR REPLACE INTO data_status 
                        (date, spy_loaded, last_update)
                        VALUES (?, 1, CURRENT_TIMESTAMP)
                    """
                else:
                    query = """
                        UPDATE data_status 
                        SET options_loaded = 1, last_update = CURRENT_TIMESTAMP
                        WHERE date = ?
                    """
                
                self.db.execute_query(query, (date_str,))
            
            current += timedelta(days=1)
    
    def get_cached_date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get the range of dates currently cached
        
        Returns:
            Tuple of (earliest_date, latest_date)
        """
        query = """
            SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date
            FROM spy_prices
        """
        
        result = self.db.execute_query(query)
        if result and result[0]['min_date']:
            return (
                datetime.fromisoformat(result[0]['min_date']),
                datetime.fromisoformat(result[0]['max_date'])
            )
        return None, None
    
    def load_today_data(self) -> int:
        """Load or update today's data
        
        Returns:
            Number of new records added
        """
        today = datetime.now()
        
        # Start from pre-market (4:00 AM ET) to capture all available data
        start_str = today.strftime("%Y-%m-%d 04:00")
        end_str = today.strftime("%Y-%m-%d %H:%M")
        
        # If before market open, still try to get pre-market data
        current_hour = today.hour
        if current_hour < 9 or (current_hour == 9 and today.minute < 30):
            logger.info(f"Pre-market: Loading available data from {start_str} to {end_str}")
        else:
            logger.info(f"Loading today's data from {start_str} to {end_str}")
        
        response = self.client.get_timesales(
            symbol="SPY",
            interval="1min",
            start=start_str,
            end=end_str,
            session_filter="all"  # Include pre-market and after-hours
        )
        
        if response and 'series' in response:
            return self._store_spy_timesales(response['series'])
        
        return 0