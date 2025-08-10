#!/usr/bin/env python3
"""
Unified Database Module
Manages historical data from both ThetaData and Alpaca sources
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class Database:
    """Unified database for historical market data"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "database", "unified_market_data.db"
            )
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        
        # Create tables
        self._create_tables()
        
        logger.info(f"Database initialized at {db_path}")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        
        # SPY prices table
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS spy_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                volume INTEGER,
                bid REAL,
                ask REAL,
                source TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, source)
            )
        ''')
        
        # Options data table
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS options_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                strike REAL NOT NULL,
                option_type TEXT NOT NULL,
                expiration DATE NOT NULL,
                
                -- Prices
                bid REAL,
                ask REAL,
                last REAL,
                mid REAL,
                
                -- Greeks
                delta REAL,
                gamma REAL,
                theta REAL,
                vega REAL,
                rho REAL,
                
                -- Other metrics
                implied_volatility REAL,
                volume INTEGER,
                open_interest INTEGER,
                underlying_price REAL,
                
                -- Metadata
                source TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(timestamp, symbol, source)
            )
        ''')
        
        # Greeks history table (for calculated Greeks)
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS greeks_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                
                -- Calculated Greeks
                delta REAL,
                gamma REAL,
                theta REAL,
                vega REAL,
                rho REAL,
                
                -- Calculation inputs
                spot_price REAL,
                strike_price REAL,
                time_to_expiry REAL,
                risk_free_rate REAL,
                implied_volatility REAL,
                
                -- Metadata
                calculation_method TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Backtest results table
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                
                -- Performance metrics
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                total_pnl REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                
                -- Strategy parameters
                parameters TEXT,  -- JSON string
                
                -- Results
                trades TEXT,  -- JSON string with trade details
                daily_returns TEXT,  -- JSON string
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Data sources tracking
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                data_type TEXT NOT NULL,  -- 'spy_prices' or 'options_data'
                source TEXT NOT NULL,  -- 'thetadata' or 'alpaca'
                record_count INTEGER,
                start_time DATETIME,
                end_time DATETIME,
                imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, data_type, source)
            )
        ''')
        
        # Create indexes for performance
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_spy_timestamp ON spy_prices(timestamp)')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_spy_date ON spy_prices(date(timestamp))')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_options_timestamp ON options_data(timestamp)')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_options_symbol ON options_data(symbol)')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_options_date ON options_data(date(timestamp))')
        self.cur.execute('CREATE INDEX IF NOT EXISTS idx_options_strike ON options_data(strike)')
        
        self.conn.commit()
    
    def insert_spy_prices(self, data: pd.DataFrame, source: str = "alpaca"):
        """
        Insert SPY price data
        
        Args:
            data: DataFrame with columns: timestamp, open, high, low, close, volume, bid, ask
            source: Data source ('alpaca' or 'thetadata')
        """
        records = []
        for _, row in data.iterrows():
            records.append((
                row['timestamp'],
                row.get('open'),
                row.get('high'),
                row.get('low'),
                row['close'],
                row.get('volume'),
                row.get('bid'),
                row.get('ask'),
                source
            ))
        
        self.cur.executemany('''
            INSERT OR REPLACE INTO spy_prices 
            (timestamp, open, high, low, close, volume, bid, ask, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        
        self.conn.commit()
        logger.info(f"Inserted {len(records)} SPY price records from {source}")
    
    def insert_options_data(self, data: pd.DataFrame, source: str = "alpaca"):
        """
        Insert options data
        
        Args:
            data: DataFrame with options data
            source: Data source
        """
        records = []
        for _, row in data.iterrows():
            records.append((
                row['timestamp'],
                row['symbol'],
                row['strike'],
                row['option_type'],
                row['expiration'],
                row.get('bid'),
                row.get('ask'),
                row.get('last'),
                row.get('mid', (row.get('bid', 0) + row.get('ask', 0)) / 2 if row.get('bid') and row.get('ask') else None),
                row.get('delta'),
                row.get('gamma'),
                row.get('theta'),
                row.get('vega'),
                row.get('rho'),
                row.get('implied_volatility'),
                row.get('volume'),
                row.get('open_interest'),
                row.get('underlying_price'),
                source
            ))
        
        self.cur.executemany('''
            INSERT OR REPLACE INTO options_data 
            (timestamp, symbol, strike, option_type, expiration,
             bid, ask, last, mid,
             delta, gamma, theta, vega, rho,
             implied_volatility, volume, open_interest, underlying_price, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        
        self.conn.commit()
        logger.info(f"Inserted {len(records)} options records from {source}")
    
    def get_spy_prices(self, start_date: str, end_date: str, 
                       source: Optional[str] = None) -> pd.DataFrame:
        """
        Get SPY prices for a date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source: Optional source filter
            
        Returns:
            DataFrame with SPY prices
        """
        query = '''
            SELECT timestamp, open, high, low, close, volume, bid, ask, source
            FROM spy_prices
            WHERE date(timestamp) BETWEEN ? AND ?
        '''
        params = [start_date, end_date]
        
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        query += ' ORDER BY timestamp'
        
        df = pd.read_sql_query(query, self.conn, params=params)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def get_options_data(self, date: str, strikes: Optional[List[float]] = None,
                        source: Optional[str] = None) -> pd.DataFrame:
        """
        Get options data for a specific date
        
        Args:
            date: Date (YYYY-MM-DD)
            strikes: Optional list of strikes to filter
            source: Optional source filter
            
        Returns:
            DataFrame with options data
        """
        query = '''
            SELECT * FROM options_data
            WHERE date(timestamp) = ?
        '''
        params = [date]
        
        if strikes:
            placeholders = ','.join(['?' for _ in strikes])
            query += f' AND strike IN ({placeholders})'
            params.extend(strikes)
        
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        query += ' ORDER BY timestamp, strike, option_type'
        
        df = pd.read_sql_query(query, self.conn, params=params)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['expiration'] = pd.to_datetime(df['expiration'])
        
        return df
    
    def get_strangle_data(self, date: str, call_strike: float, put_strike: float,
                         start_time: str = "14:30", end_time: str = "16:00") -> pd.DataFrame:
        """
        Get strangle data for specific strikes
        
        Args:
            date: Date (YYYY-MM-DD)
            call_strike: Call strike price
            put_strike: Put strike price
            start_time: Start time (HH:MM)
            end_time: End time (HH:MM)
            
        Returns:
            DataFrame with strangle data
        """
        query = '''
            SELECT 
                c.timestamp,
                c.underlying_price as spy_price,
                c.bid as call_bid,
                c.ask as call_ask,
                c.mid as call_mid,
                c.delta as call_delta,
                c.gamma as call_gamma,
                c.theta as call_theta,
                c.vega as call_vega,
                c.implied_volatility as call_iv,
                p.bid as put_bid,
                p.ask as put_ask,
                p.mid as put_mid,
                p.delta as put_delta,
                p.gamma as put_gamma,
                p.theta as put_theta,
                p.vega as put_vega,
                p.implied_volatility as put_iv
            FROM options_data c
            JOIN options_data p ON c.timestamp = p.timestamp
            WHERE date(c.timestamp) = ?
                AND c.strike = ? AND c.option_type = 'CALL'
                AND p.strike = ? AND p.option_type = 'PUT'
                AND time(c.timestamp) BETWEEN ? AND ?
            ORDER BY c.timestamp
        '''
        
        df = pd.read_sql_query(query, self.conn, 
                              params=[date, call_strike, put_strike, start_time, end_time])
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['total_premium'] = df['call_bid'] + df['put_bid']
            df['total_vega'] = abs(df['call_vega']) + abs(df['put_vega'])
            df['net_delta'] = df['call_delta'] + df['put_delta']
        
        return df
    
    def save_backtest_results(self, strategy_name: str, start_date: str, end_date: str,
                             metrics: Dict, parameters: Dict, trades: List[Dict]) -> int:
        """
        Save backtest results
        
        Args:
            strategy_name: Name of the strategy
            start_date: Backtest start date
            end_date: Backtest end date
            metrics: Performance metrics dictionary
            parameters: Strategy parameters
            trades: List of trade dictionaries
            
        Returns:
            Inserted row ID
        """
        self.cur.execute('''
            INSERT INTO backtest_results 
            (strategy_name, start_date, end_date,
             total_trades, winning_trades, losing_trades, win_rate,
             total_pnl, max_drawdown, sharpe_ratio,
             parameters, trades)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name, start_date, end_date,
            metrics.get('total_trades', 0),
            metrics.get('winning_trades', 0),
            metrics.get('losing_trades', 0),
            metrics.get('win_rate', 0),
            metrics.get('total_pnl', 0),
            metrics.get('max_drawdown', 0),
            metrics.get('sharpe_ratio', 0),
            json.dumps(parameters),
            json.dumps(trades)
        ))
        
        self.conn.commit()
        return self.cur.lastrowid
    
    def get_data_coverage(self) -> pd.DataFrame:
        """
        Get summary of data coverage by date and source
        
        Returns:
            DataFrame with coverage information
        """
        query = '''
            SELECT 
                date,
                data_type,
                source,
                record_count,
                start_time,
                end_time
            FROM data_sources
            ORDER BY date DESC, data_type, source
        '''
        
        return pd.read_sql_query(query, self.conn)
    
    def update_data_source(self, date: str, data_type: str, source: str, 
                          record_count: int, start_time: str, end_time: str):
        """
        Update data source tracking
        
        Args:
            date: Date of data
            data_type: Type of data ('spy_prices' or 'options_data')
            source: Data source
            record_count: Number of records
            start_time: Start timestamp
            end_time: End timestamp
        """
        self.cur.execute('''
            INSERT OR REPLACE INTO data_sources 
            (date, data_type, source, record_count, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, data_type, source, record_count, start_time, end_time))
        
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'conn'):
            self.conn.close()


if __name__ == "__main__":
    # Test the database
    db = Database()
    
    # Check coverage
    coverage = db.get_data_coverage()
    print(f"Data coverage: {len(coverage)} entries")
    print(coverage.head() if not coverage.empty else "No data yet")