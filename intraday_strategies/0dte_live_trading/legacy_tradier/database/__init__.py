"""
Tradier Market Data Database Module
Provides SQLite-based caching for historical and real-time market data
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database connections and operations"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'market_data.db')
        
        self.db_path = db_path
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database and tables if they don't exist"""
        schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
        
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema)
                logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level='DEFERRED'
        )
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()):
        """Execute a query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of Row objects
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def execute_many(self, query: str, data: list):
        """Execute query for multiple rows of data
        
        Args:
            query: SQL query string
            data: List of parameter tuples
        """
        with self.get_connection() as conn:
            conn.executemany(query, data)
            logger.debug(f"Inserted {len(data)} records")
    
    def get_stats(self) -> dict:
        """Get database statistics
        
        Returns:
            Dictionary with cache statistics
        """
        stats = self.execute_query("SELECT * FROM cache_stats")
        if stats:
            row = stats[0]
            return {
                'total_spy_records': row['total_spy_records'],
                'total_options_records': row['total_options_records'],
                'earliest_data': row['earliest_spy_data'],
                'latest_data': row['latest_spy_data'],
                'trading_days': row['trading_days_cached'],
                'last_update': row['last_update_time']
            }
        return {}

# Create singleton instance
_db_manager = None

def get_db_manager(db_path: Optional[str] = None) -> DatabaseManager:
    """Get or create database manager instance
    
    Args:
        db_path: Optional path to database file
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager