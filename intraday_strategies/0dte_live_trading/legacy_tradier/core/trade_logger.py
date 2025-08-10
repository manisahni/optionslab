"""
Trade logging system for tracking all trades
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import json
import os

class TradeLogger:
    """Logs all trades to database for tracking and analysis"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'trades.db')
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize trades database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                trade_type TEXT,  -- 'strangle', 'call', 'put'
                symbol TEXT,
                call_symbol TEXT,
                call_strike REAL,
                put_symbol TEXT,
                put_strike REAL,
                quantity INTEGER,
                credit_received REAL,
                debit_paid REAL,
                entry_price REAL,  -- SPY price at entry
                entry_time DATETIME,
                exit_time DATETIME,
                exit_price REAL,  -- SPY price at exit
                exit_reason TEXT,  -- 'expired', 'stop_loss', 'manual', 'time_exit'
                final_pl REAL,
                max_profit REAL,
                max_loss REAL,
                strategy_score REAL,
                criteria_met TEXT,  -- JSON string of criteria
                environment TEXT,  -- 'sandbox' or 'production'
                notes TEXT
            )
        """)
        
        # Create trade_legs table for complex orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_legs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                symbol TEXT,
                option_type TEXT,  -- 'call' or 'put'
                strike REAL,
                quantity INTEGER,
                side TEXT,  -- 'buy' or 'sell'
                price REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        """)
        
        # Create trade_updates table for monitoring
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                spy_price REAL,
                position_delta REAL,
                position_gamma REAL,
                position_theta REAL,
                position_vega REAL,
                unrealized_pl REAL,
                notes TEXT,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_strangle_entry(self, call_symbol: str, put_symbol: str, 
                          call_strike: float, put_strike: float,
                          credit: float, spy_price: float,
                          strategy_score: float = 0, criteria: Dict = None,
                          environment: str = 'sandbox') -> int:
        """Log a new strangle trade entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (
                trade_type, symbol, call_symbol, call_strike,
                put_symbol, put_strike, quantity, credit_received,
                entry_price, entry_time, strategy_score, criteria_met,
                environment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'strangle', 'SPY', call_symbol, call_strike,
            put_symbol, put_strike, 1, credit,
            spy_price, datetime.now(), strategy_score,
            json.dumps(criteria) if criteria else None,
            environment
        ))
        
        trade_id = cursor.lastrowid
        
        # Log individual legs
        cursor.execute("""
            INSERT INTO trade_legs (trade_id, symbol, option_type, strike, quantity, side, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade_id, call_symbol, 'call', call_strike, 1, 'sell', credit/2))
        
        cursor.execute("""
            INSERT INTO trade_legs (trade_id, symbol, option_type, strike, quantity, side, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trade_id, put_symbol, 'put', put_strike, 1, 'sell', credit/2))
        
        conn.commit()
        conn.close()
        
        return trade_id
    
    def log_trade_update(self, trade_id: int, spy_price: float, 
                        unrealized_pl: float, greeks: Dict = None):
        """Log a trade update/monitoring event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trade_updates (
                trade_id, spy_price, position_delta, position_gamma,
                position_theta, position_vega, unrealized_pl
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id, spy_price,
            greeks.get('delta', 0) if greeks else 0,
            greeks.get('gamma', 0) if greeks else 0,
            greeks.get('theta', 0) if greeks else 0,
            greeks.get('vega', 0) if greeks else 0,
            unrealized_pl
        ))
        
        conn.commit()
        conn.close()
    
    def log_trade_exit(self, trade_id: int, exit_price: float,
                      final_pl: float, exit_reason: str):
        """Log trade exit"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE trades 
            SET exit_time = ?, exit_price = ?, final_pl = ?, exit_reason = ?
            WHERE id = ?
        """, (datetime.now(), exit_price, final_pl, exit_reason, trade_id))
        
        conn.commit()
        conn.close()
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trades"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return trades
    
    def get_today_trades(self) -> List[Dict]:
        """Get today's trades"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT * FROM trades 
            WHERE date(timestamp) = date(?)
            ORDER BY timestamp DESC
        """, (today,))
        
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return trades
    
    def get_open_trades(self) -> List[Dict]:
        """Get currently open trades"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trades 
            WHERE exit_time IS NULL
            ORDER BY timestamp DESC
        """)
        
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return trades
    
    def get_trade_updates(self, trade_id: int) -> List[Dict]:
        """Get all updates for a specific trade"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trade_updates 
            WHERE trade_id = ?
            ORDER BY timestamp
        """, (trade_id,))
        
        updates = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return updates
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN final_pl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN final_pl <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(final_pl) as total_pl,
                AVG(final_pl) as avg_pl,
                MAX(final_pl) as max_win,
                MIN(final_pl) as max_loss
            FROM trades 
            WHERE exit_time IS NOT NULL
        """)
        
        stats = dict(zip([d[0] for d in cursor.description], cursor.fetchone()))
        
        # Calculate win rate
        if stats['total_trades'] > 0:
            stats['win_rate'] = (stats['wins'] / stats['total_trades']) * 100
        else:
            stats['win_rate'] = 0
        
        conn.close()
        return stats