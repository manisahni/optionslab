#!/usr/bin/env python3
"""
Alpaca Live Trading System for VegaAware Strategy
Monitors and executes 0DTE strangle trades automatically
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.alpaca_client import AlpacaClient
from core.greeks_calculator import GreeksCalculator
import sqlite3
from datetime import datetime, time, timedelta
import time as time_module
import pytz
import threading
import signal

class AlpacaLiveTrader:
    """Live trading system for 0DTE options with Alpaca"""
    
    def __init__(self, paper: bool = True):
        """Initialize live trader"""
        self.client = AlpacaClient(paper=paper)
        self.greeks_calc = GreeksCalculator()
        self.ET = pytz.timezone('US/Eastern')
        
        # Trading parameters
        self.underlying = "SPY"
        self.strike_width = 3.0  # $3 away from spot
        self.entry_time = time(15, 0)  # 3:00 PM ET
        self.exit_time = time(15, 58)  # 3:58 PM ET (before close)
        
        # State
        self.running = False
        self.position_open = False
        self.current_position = None
        self.monitoring_thread = None
        
        # Database
        self.conn = sqlite3.connect('database/market_data.db', check_same_thread=False)
        self.cur = self.conn.cursor()
        
        # Create trades table if not exists
        self._create_trades_table()
    
    def _create_trades_table(self):
        """Create table for tracking trades"""
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS alpaca_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date DATE,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                spy_entry REAL,
                spy_exit REAL,
                call_symbol TEXT,
                put_symbol TEXT,
                call_entry REAL,
                put_entry REAL,
                call_exit REAL,
                put_exit REAL,
                total_collected REAL,
                total_exit REAL,
                pnl REAL,
                pnl_pct REAL,
                status TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now(self.ET).strftime('%Y-%m-%d %H:%M:%S ET')
        print(f"[{timestamp}] {message}")
    
    def check_market_conditions(self) -> bool:
        """Check if market conditions are suitable for trading"""
        # Check if market is open
        if not self.client.is_market_open():
            self.log("Market is closed")
            return False
        
        # Check account status
        account = self.client.get_account()
        if not account:
            self.log("Failed to get account info")
            return False
        
        # Check buying power
        buying_power = float(account.get('buying_power', 0))
        if buying_power < 1000:
            self.log(f"Insufficient buying power: ${buying_power:.2f}")
            return False
        
        # Check if already in position
        positions = self.client.get_positions()
        options_positions = [p for p in positions if len(p.get('symbol', '')) > 10]
        if options_positions:
            self.log(f"Already have {len(options_positions)} options positions")
            return False
        
        return True
    
    def find_strangle_strikes(self) -> tuple:
        """Find appropriate strangle strikes for current market"""
        # Get current SPY price
        quote = self.client.get_stock_quote(self.underlying)
        if not quote:
            self.log("Failed to get SPY quote")
            return None, None
        
        bid = quote.get('bp', 0)
        ask = quote.get('ap', 0)
        mid_price = (bid + ask) / 2
        
        self.log(f"SPY: ${mid_price:.2f} (Bid: ${bid:.2f}, Ask: ${ask:.2f})")
        
        # Calculate strikes
        call_strike = round(mid_price + self.strike_width)
        put_strike = round(mid_price - self.strike_width)
        
        self.log(f"Strangle strikes: Put ${put_strike}, Call ${call_strike}")
        
        # Get today's expiration
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Find contracts
        contracts = self.client.get_option_contracts(
            self.underlying,
            expiration=today,
            strike_gte=put_strike - 1,
            strike_lte=call_strike + 1
        )
        
        call_symbol = None
        put_symbol = None
        
        for contract in contracts:
            strike = float(contract.get('strike_price', 0))
            if strike == call_strike and contract.get('type') == 'call':
                call_symbol = contract.get('symbol')
            elif strike == put_strike and contract.get('type') == 'put':
                put_symbol = contract.get('symbol')
        
        if not call_symbol or not put_symbol:
            self.log(f"Could not find contracts: Call={call_symbol}, Put={put_symbol}")
            return None, None
        
        return call_symbol, put_symbol
    
    def enter_strangle(self) -> bool:
        """Enter strangle position"""
        self.log("=" * 60)
        self.log("ENTERING STRANGLE POSITION")
        self.log("=" * 60)
        
        # Find strikes
        call_symbol, put_symbol = self.find_strangle_strikes()
        if not call_symbol or not put_symbol:
            return False
        
        # Get quotes
        call_quote = self.client.get_option_quote(call_symbol)
        put_quote = self.client.get_option_quote(put_symbol)
        
        if not call_quote or not put_quote:
            self.log("Failed to get option quotes")
            return False
        
        # Calculate mid prices
        call_mid = (call_quote.get('ap', 0) + call_quote.get('bp', 0)) / 2
        put_mid = (put_quote.get('ap', 0) + put_quote.get('bp', 0)) / 2
        
        self.log(f"Call {call_symbol}: ${call_mid:.2f}")
        self.log(f"Put {put_symbol}: ${put_mid:.2f}")
        self.log(f"Total credit: ${call_mid + put_mid:.2f}")
        
        # Place orders (sell strangle)
        legs = [
            {"symbol": call_symbol, "side": "sell", "ratio_qty": 1},
            {"symbol": put_symbol, "side": "sell", "ratio_qty": 1}
        ]
        
        self.log("Placing strangle order...")
        order = self.client.place_option_order(legs, qty=1, order_type="market")
        
        if 'error' in order:
            self.log(f"Order failed: {order['error']}")
            return False
        
        self.log(f"Order placed: {order.get('id')}")
        
        # Store position info
        self.current_position = {
            'entry_time': datetime.now(self.ET),
            'call_symbol': call_symbol,
            'put_symbol': put_symbol,
            'call_entry': call_mid,
            'put_entry': put_mid,
            'total_collected': call_mid + put_mid,
            'spy_entry': (call_quote.get('ap', 0) + call_quote.get('bp', 0)) / 2,
            'order_id': order.get('id')
        }
        
        self.position_open = True
        
        # Log to database
        self.cur.execute('''
            INSERT INTO alpaca_trades (
                trade_date, entry_time, spy_entry,
                call_symbol, put_symbol, call_entry, put_entry,
                total_collected, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().date(),
            self.current_position['entry_time'],
            self.current_position['spy_entry'],
            call_symbol, put_symbol,
            call_mid, put_mid,
            call_mid + put_mid,
            'OPEN'
        ))
        self.conn.commit()
        self.current_position['trade_id'] = self.cur.lastrowid
        
        self.log("✅ Position opened successfully")
        return True
    
    def monitor_position(self):
        """Monitor open position and calculate P&L"""
        if not self.position_open or not self.current_position:
            return
        
        # Get current quotes
        call_quote = self.client.get_option_quote(self.current_position['call_symbol'])
        put_quote = self.client.get_option_quote(self.current_position['put_symbol'])
        spy_quote = self.client.get_stock_quote(self.underlying)
        
        if not call_quote or not put_quote or not spy_quote:
            return
        
        # Calculate current values
        call_mid = (call_quote.get('ap', 0) + call_quote.get('bp', 0)) / 2
        put_mid = (put_quote.get('ap', 0) + put_quote.get('bp', 0)) / 2
        spy_mid = (spy_quote.get('ap', 0) + spy_quote.get('bp', 0)) / 2
        
        total_current = call_mid + put_mid
        pnl = self.current_position['total_collected'] - total_current
        pnl_pct = (pnl / self.current_position['total_collected']) * 100 if self.current_position['total_collected'] > 0 else 0
        
        # Calculate Greeks
        expiry = datetime.now().strftime('%Y-%m-%d')
        time_to_expiry = self.greeks_calc.calculate_time_to_expiry(expiry)
        
        try:
            call_iv = self.greeks_calc.calculate_iv_from_price(
                call_mid, spy_mid, 
                float(self.current_position['call_symbol'][13:16]),  # Extract strike
                time_to_expiry, 'call'
            )
            put_iv = self.greeks_calc.calculate_iv_from_price(
                put_mid, spy_mid,
                float(self.current_position['put_symbol'][13:16]),  # Extract strike
                time_to_expiry, 'put'
            )
        except:
            call_iv = put_iv = 0
        
        # Log status
        self.log(f"Position Update: SPY ${spy_mid:.2f} | "
                f"Call ${call_mid:.2f} (IV: {call_iv:.1%}) | "
                f"Put ${put_mid:.2f} (IV: {put_iv:.1%}) | "
                f"P&L: ${pnl:.2f} ({pnl_pct:.1f}%)")
    
    def exit_strangle(self) -> bool:
        """Exit strangle position"""
        if not self.position_open or not self.current_position:
            return False
        
        self.log("=" * 60)
        self.log("EXITING STRANGLE POSITION")
        self.log("=" * 60)
        
        # Place buy-to-close orders
        legs = [
            {"symbol": self.current_position['call_symbol'], "side": "buy", "ratio_qty": 1},
            {"symbol": self.current_position['put_symbol'], "side": "buy", "ratio_qty": 1}
        ]
        
        self.log("Placing closing order...")
        order = self.client.place_option_order(legs, qty=1, order_type="market")
        
        if 'error' in order:
            self.log(f"Close order failed: {order['error']}")
            # Try to close individually
            self.client.close_position(self.current_position['call_symbol'])
            self.client.close_position(self.current_position['put_symbol'])
        
        # Get final prices
        call_quote = self.client.get_option_quote(self.current_position['call_symbol'])
        put_quote = self.client.get_option_quote(self.current_position['put_symbol'])
        spy_quote = self.client.get_stock_quote(self.underlying)
        
        call_exit = (call_quote.get('ap', 0) + call_quote.get('bp', 0)) / 2 if call_quote else 0
        put_exit = (put_quote.get('ap', 0) + put_quote.get('bp', 0)) / 2 if put_quote else 0
        spy_exit = (spy_quote.get('ap', 0) + spy_quote.get('bp', 0)) / 2 if spy_quote else 0
        
        total_exit = call_exit + put_exit
        pnl = self.current_position['total_collected'] - total_exit
        pnl_pct = (pnl / self.current_position['total_collected']) * 100 if self.current_position['total_collected'] > 0 else 0
        
        # Update database
        self.cur.execute('''
            UPDATE alpaca_trades
            SET exit_time = ?, spy_exit = ?, call_exit = ?, put_exit = ?,
                total_exit = ?, pnl = ?, pnl_pct = ?, status = ?
            WHERE id = ?
        ''', (
            datetime.now(self.ET),
            spy_exit, call_exit, put_exit,
            total_exit, pnl, pnl_pct, 'CLOSED',
            self.current_position['trade_id']
        ))
        self.conn.commit()
        
        self.log(f"Position closed: P&L ${pnl:.2f} ({pnl_pct:.1f}%)")
        
        self.position_open = False
        self.current_position = None
        
        return True
    
    def run_monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                now = datetime.now(self.ET)
                current_time = now.time()
                
                # Check if it's a trading day
                if now.weekday() >= 5:  # Weekend
                    time_module.sleep(60)
                    continue
                
                # Entry logic - 3:00 PM ET
                if (current_time >= self.entry_time and 
                    current_time < time(15, 5) and 
                    not self.position_open):
                    
                    if self.check_market_conditions():
                        self.enter_strangle()
                
                # Monitoring - while position is open
                elif self.position_open:
                    self.monitor_position()
                    
                    # Exit logic - 3:58 PM ET or market close
                    if current_time >= self.exit_time:
                        self.exit_strangle()
                
                # Sleep for 10 seconds between checks
                time_module.sleep(10)
                
            except Exception as e:
                self.log(f"Error in monitoring loop: {e}")
                time_module.sleep(30)
    
    def start(self):
        """Start live trading"""
        self.log("=" * 70)
        self.log("ALPACA LIVE TRADER STARTED")
        self.log(f"Mode: {'PAPER' if self.client.paper else 'LIVE'} TRADING")
        self.log(f"Strategy: VegaAware 0DTE Strangle")
        self.log(f"Entry: 3:00 PM ET | Exit: 3:58 PM ET")
        self.log("=" * 70)
        
        self.running = True
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self.run_monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # Wait for interrupt
        try:
            while self.running:
                time_module.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop live trading"""
        self.log("Shutting down...")
        self.running = False
        
        # Close any open positions
        if self.position_open:
            self.log("Closing open position before shutdown...")
            self.exit_strangle()
        
        # Wait for thread to finish
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        # Close database
        self.conn.close()
        
        self.log("✅ Shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global trader
    if trader:
        trader.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check command line arguments
    paper_mode = True
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        paper_mode = False
        response = input("⚠️  WARNING: Live trading mode! Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    # Start trader
    trader = AlpacaLiveTrader(paper=paper_mode)
    trader.start()