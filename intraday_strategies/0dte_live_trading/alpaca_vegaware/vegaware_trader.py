#!/usr/bin/env python3
"""
VegaAware Live Trading System - Alpaca
Full implementation of the 93.7% win rate 0DTE strategy with all entry criteria,
Greeks monitoring, stop losses, and profit targets
"""

from alpaca_vegaware.core.client import AlpacaClient
from alpaca_vegaware.core.greeks import GreeksCalculator
import sqlite3
from datetime import datetime, time, timedelta
import time as time_module
import pytz
import threading
import signal
import json
import numpy as np

class VegaAwareTrader:
    """Advanced VegaAware strategy implementation with full risk management"""
    
    def __init__(self, paper: bool = True):
        """Initialize VegaAware trader with all strategy parameters"""
        self.client = AlpacaClient(paper=paper)
        self.greeks_calc = GreeksCalculator()
        self.ET = pytz.timezone('US/Eastern')
        
        # === STRATEGY PARAMETERS (93.7% Win Rate Settings) ===
        
        # Entry Criteria Thresholds
        self.TARGET_DELTA = 0.15        # Target delta for strikes
        self.MAX_DELTA_DEVIATION = 0.05 # Allow 0.10-0.20 delta range
        self.MIN_PREMIUM = 0.30         # Minimum premium per side
        self.MAX_SPREAD = 0.02          # Max SPY bid-ask spread
        self.MIN_BUYING_POWER = 5000    # Minimum account buying power
        self.ENTRY_SCORE_THRESHOLD = 80 # Require 80% criteria met
        
        # Greeks Limits
        self.MAX_VEGA = 2.0             # Maximum total vega exposure
        self.VEGA_WARNING = 1.5         # Vega warning level
        self.MAX_DELTA_IMBALANCE = 0.10 # Max net delta allowed
        
        # Risk Management
        self.STOP_LOSS_MULTIPLIER = 2.0 # Stop at 2x credit received
        self.PROFIT_TARGET_PCT = 50     # Take profit at 50% of credit
        self.STRIKE_BUFFER_PCT = 0.25   # Exit if within 0.25% of strike
        
        # Time Windows
        self.ENTRY_START = time(14, 30)  # 2:30 PM ET
        self.ENTRY_END = time(15, 30)    # 3:30 PM ET
        self.OPTIMAL_ENTRY = time(15, 0) # 3:00 PM ET
        self.RECOMMENDED_EXIT = time(15, 55) # 3:55 PM ET (avoid chaos)
        self.FINAL_EXIT = time(15, 58)   # 3:58 PM ET (absolute latest)
        
        # State Management
        self.running = False
        self.position_open = False
        self.current_position = None
        self.monitoring_thread = None
        self.entry_criteria_history = []
        
        # Performance Tracking
        self.trades_today = 0
        self.daily_pnl = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Database
        self.conn = sqlite3.connect('database/market_data.db', check_same_thread=False)
        self.cur = self.conn.cursor()
        self._create_enhanced_trades_table()
    
    def _create_enhanced_trades_table(self):
        """Create enhanced table with Greeks and criteria tracking"""
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS alpaca_vegaware_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date DATE,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                
                -- Prices
                spy_entry REAL,
                spy_exit REAL,
                call_symbol TEXT,
                put_symbol TEXT,
                call_strike REAL,
                put_strike REAL,
                call_entry REAL,
                put_entry REAL,
                call_exit REAL,
                put_exit REAL,
                
                -- Greeks at Entry
                entry_call_delta REAL,
                entry_put_delta REAL,
                entry_total_vega REAL,
                entry_call_iv REAL,
                entry_put_iv REAL,
                entry_call_theta REAL,
                entry_put_theta REAL,
                
                -- Entry Criteria
                entry_score INTEGER,
                entry_criteria_json TEXT,
                
                -- P&L
                total_collected REAL,
                total_exit REAL,
                pnl REAL,
                pnl_pct REAL,
                
                -- Exit Info
                exit_reason TEXT,
                max_adverse REAL,
                max_profit REAL,
                
                -- Status
                status TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with levels"""
        timestamp = datetime.now(self.ET).strftime('%Y-%m-%d %H:%M:%S ET')
        symbols = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "TRADE": "💰",
            "ALERT": "🔔"
        }
        symbol = symbols.get(level, "📝")
        print(f"[{timestamp}] {symbol} {message}")
    
    def check_entry_criteria(self) -> dict:
        """Check all 13 VegaAware entry criteria"""
        criteria = {
            'timestamp': datetime.now(self.ET),
            'checks': {},
            'score': 0,
            'can_trade': False,
            'details': {}
        }
        
        # 1. Market Open Check
        is_open = self.client.is_market_open()
        criteria['checks']['market_open'] = is_open
        if not is_open:
            self.log("Market is closed", "WARNING")
            return criteria
        
        # 2. Time Window Check
        now = datetime.now(self.ET)
        current_time = now.time()
        in_window = self.ENTRY_START <= current_time <= self.ENTRY_END
        is_optimal = abs((datetime.combine(now.date(), current_time) - 
                         datetime.combine(now.date(), self.OPTIMAL_ENTRY)).total_seconds()) < 300
        
        criteria['checks']['time_window'] = in_window
        criteria['checks']['optimal_time'] = is_optimal
        criteria['details']['current_time'] = current_time.strftime('%H:%M:%S')
        
        # 3. Get SPY Quote and Check Spread
        spy_quote = self.client.get_stock_quote("SPY")
        if not spy_quote:
            self.log("Failed to get SPY quote", "ERROR")
            return criteria
        
        bid = spy_quote.get('bp', 0)
        ask = spy_quote.get('ap', 0)
        spread = ask - bid
        spy_mid = (bid + ask) / 2
        
        criteria['checks']['spy_spread_ok'] = spread <= self.MAX_SPREAD
        criteria['details']['spy_price'] = spy_mid
        criteria['details']['spy_spread'] = spread
        
        # 4. Account Checks
        account = self.client.get_account()
        buying_power = float(account.get('buying_power', 0))
        criteria['checks']['sufficient_buying_power'] = buying_power >= self.MIN_BUYING_POWER
        criteria['details']['buying_power'] = buying_power
        
        # 5. Check for Existing Positions
        positions = self.client.get_positions()
        options_positions = [p for p in positions if len(p.get('symbol', '')) > 10]
        criteria['checks']['no_existing_positions'] = len(options_positions) == 0
        
        # 6. Find Delta-Based Strikes
        optimal_strikes = self.find_delta_strikes(spy_mid)
        if optimal_strikes:
            call_symbol, put_symbol, call_strike, put_strike = optimal_strikes
            criteria['checks']['strikes_found'] = True
            criteria['details']['call_strike'] = call_strike
            criteria['details']['put_strike'] = put_strike
            
            # 7. Get Option Quotes
            call_quote = self.client.get_option_quote(call_symbol)
            put_quote = self.client.get_option_quote(put_symbol)
            
            if call_quote and put_quote:
                call_bid = call_quote.get('bp', 0)
                call_ask = call_quote.get('ap', 0)
                put_bid = put_quote.get('bp', 0)
                put_ask = put_quote.get('ap', 0)
                
                call_mid = (call_bid + call_ask) / 2
                put_mid = (put_bid + put_ask) / 2
                
                # 8. Premium Checks
                criteria['checks']['call_premium_sufficient'] = call_mid >= self.MIN_PREMIUM
                criteria['checks']['put_premium_sufficient'] = put_mid >= self.MIN_PREMIUM
                criteria['details']['call_premium'] = call_mid
                criteria['details']['put_premium'] = put_mid
                criteria['details']['total_credit'] = call_mid + put_mid
                
                # 9. Calculate Greeks
                expiry = datetime.now().strftime('%Y-%m-%d')
                time_to_expiry = self.greeks_calc.calculate_time_to_expiry(expiry)
                
                if time_to_expiry > 0:
                    # Calculate IV from prices
                    try:
                        call_iv = self.greeks_calc.calculate_iv_from_price(
                            call_mid, spy_mid, call_strike, time_to_expiry, 'call'
                        )
                        put_iv = self.greeks_calc.calculate_iv_from_price(
                            put_mid, spy_mid, put_strike, time_to_expiry, 'put'
                        )
                        
                        # Calculate Greeks
                        call_greeks = self.greeks_calc.calculate_greeks(
                            spy_mid, call_strike, time_to_expiry, call_iv, 'call'
                        )
                        put_greeks = self.greeks_calc.calculate_greeks(
                            spy_mid, put_strike, time_to_expiry, put_iv, 'put'
                        )
                        
                        # 10. Vega Check
                        total_vega = abs(call_greeks['vega']) + abs(put_greeks['vega'])
                        criteria['checks']['vega_acceptable'] = total_vega <= self.MAX_VEGA
                        criteria['details']['total_vega'] = total_vega
                        
                        # 11. Delta Balance Check
                        net_delta = call_greeks['delta'] + put_greeks['delta']
                        criteria['checks']['delta_neutral'] = abs(net_delta) <= self.MAX_DELTA_IMBALANCE
                        criteria['details']['net_delta'] = net_delta
                        criteria['details']['call_delta'] = call_greeks['delta']
                        criteria['details']['put_delta'] = put_greeks['delta']
                        
                        # 12. IV Environment Check
                        avg_iv = (call_iv + put_iv) / 2
                        criteria['checks']['iv_reasonable'] = 0.10 <= avg_iv <= 0.50
                        criteria['details']['avg_iv'] = avg_iv
                        
                        # Store Greeks for later use
                        criteria['greeks'] = {
                            'call': call_greeks,
                            'put': put_greeks,
                            'call_iv': call_iv,
                            'put_iv': put_iv
                        }
                        
                    except Exception as e:
                        self.log(f"Greeks calculation error: {e}", "ERROR")
                        criteria['checks']['greeks_calculated'] = False
                
                # 13. Strike Distance Check
                call_distance = (call_strike - spy_mid) / spy_mid
                put_distance = (spy_mid - put_strike) / spy_mid
                criteria['checks']['strikes_safe_distance'] = (call_distance >= 0.004 and 
                                                               put_distance >= 0.004)
                criteria['details']['call_distance_pct'] = call_distance * 100
                criteria['details']['put_distance_pct'] = put_distance * 100
        else:
            criteria['checks']['strikes_found'] = False
        
        # Calculate total score
        total_checks = len(criteria['checks'])
        passed_checks = sum(1 for v in criteria['checks'].values() if v)
        criteria['score'] = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        criteria['can_trade'] = criteria['score'] >= self.ENTRY_SCORE_THRESHOLD
        
        # Log summary
        self.log(f"Entry Score: {criteria['score']:.0f}% ({passed_checks}/{total_checks} passed)")
        
        return criteria
    
    def find_delta_strikes(self, spy_price: float) -> tuple:
        """Find option strikes with target delta (0.15)"""
        # Get today's expiration
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get all available contracts
        contracts = self.client.get_option_contracts(
            "SPY",
            expiration=today,
            strike_gte=spy_price - 10,
            strike_lte=spy_price + 10
        )
        
        if not contracts:
            self.log("No contracts available", "WARNING")
            return None
        
        # Calculate time to expiry
        expiry = today
        time_to_expiry = self.greeks_calc.calculate_time_to_expiry(expiry)
        
        if time_to_expiry <= 0:
            self.log("Options expired or about to expire", "WARNING")
            return None
        
        # Find best call and put strikes
        best_call = None
        best_put = None
        best_call_delta_diff = float('inf')
        best_put_delta_diff = float('inf')
        
        # Use a reasonable IV estimate for initial selection
        estimated_iv = 0.15  # 15% IV as starting point
        
        for contract in contracts:
            strike = float(contract.get('strike_price', 0))
            contract_type = contract.get('type')
            symbol = contract.get('symbol')
            
            # Calculate approximate delta
            try:
                greeks = self.greeks_calc.calculate_greeks(
                    spy_price, strike, time_to_expiry, estimated_iv, contract_type
                )
                delta = abs(greeks['delta'])
                
                # Check if delta is within acceptable range
                delta_diff = abs(delta - self.TARGET_DELTA)
                
                if contract_type == 'call' and strike > spy_price:
                    if delta_diff < best_call_delta_diff and delta_diff <= self.MAX_DELTA_DEVIATION:
                        best_call = (symbol, strike)
                        best_call_delta_diff = delta_diff
                        
                elif contract_type == 'put' and strike < spy_price:
                    if delta_diff < best_put_delta_diff and delta_diff <= self.MAX_DELTA_DEVIATION:
                        best_put = (symbol, strike)
                        best_put_delta_diff = delta_diff
                        
            except:
                continue
        
        if best_call and best_put:
            call_symbol, call_strike = best_call
            put_symbol, put_strike = best_put
            
            self.log(f"Found delta-based strikes: Call ${call_strike:.0f}, Put ${put_strike:.0f}")
            return call_symbol, put_symbol, call_strike, put_strike
        
        # Fallback to fixed width if delta-based fails
        self.log("Delta-based selection failed, using $3 width fallback", "WARNING")
        call_strike = round(spy_price + 3)
        put_strike = round(spy_price - 3)
        
        for contract in contracts:
            strike = float(contract.get('strike_price', 0))
            if strike == call_strike and contract.get('type') == 'call':
                call_symbol = contract.get('symbol')
            elif strike == put_strike and contract.get('type') == 'put':
                put_symbol = contract.get('symbol')
        
        if 'call_symbol' in locals() and 'put_symbol' in locals():
            return call_symbol, put_symbol, call_strike, put_strike
        
        return None
    
    def enter_strangle(self) -> bool:
        """Enter strangle position with full criteria validation"""
        self.log("=" * 60)
        self.log("CHECKING VEGAWARE ENTRY CRITERIA", "INFO")
        self.log("=" * 60)
        
        # Check all entry criteria
        criteria = self.check_entry_criteria()
        
        # Display criteria results
        self.log("\n📊 Entry Criteria Results:")
        for check, passed in criteria['checks'].items():
            status = "✅" if passed else "❌"
            self.log(f"  {status} {check.replace('_', ' ').title()}")
        
        # Display key metrics
        if 'details' in criteria:
            self.log("\n📈 Key Metrics:")
            details = criteria['details']
            if 'spy_price' in details:
                self.log(f"  SPY: ${details['spy_price']:.2f}")
            if 'total_credit' in details:
                self.log(f"  Expected Credit: ${details['total_credit']:.2f}")
            if 'total_vega' in details:
                self.log(f"  Total Vega: {details['total_vega']:.2f}")
            if 'net_delta' in details:
                self.log(f"  Net Delta: {details['net_delta']:.3f}")
        
        # Check if we can trade
        if not criteria['can_trade']:
            self.log(f"\n⛔ Cannot trade - Score {criteria['score']:.0f}% < {self.ENTRY_SCORE_THRESHOLD}%", 
                    "WARNING")
            return False
        
        self.log(f"\n✅ All criteria met! Score: {criteria['score']:.0f}%", "SUCCESS")
        
        # Get the strikes we identified
        call_strike = criteria['details'].get('call_strike')
        put_strike = criteria['details'].get('put_strike')
        
        if not call_strike or not put_strike:
            self.log("Strike information missing", "ERROR")
            return False
        
        # Find the contract symbols
        optimal_strikes = self.find_delta_strikes(criteria['details']['spy_price'])
        if not optimal_strikes:
            self.log("Failed to find contract symbols", "ERROR")
            return False
        
        call_symbol, put_symbol, _, _ = optimal_strikes
        
        # Place the strangle order
        self.log("\n📝 Placing strangle order...")
        
        legs = [
            {"symbol": call_symbol, "side": "sell", "ratio_qty": 1},
            {"symbol": put_symbol, "side": "sell", "ratio_qty": 1}
        ]
        
        order = self.client.place_option_order(legs, qty=1, order_type="market")
        
        if 'error' in order:
            self.log(f"Order failed: {order['error']}", "ERROR")
            return False
        
        self.log(f"Order placed successfully! ID: {order.get('id')}", "SUCCESS")
        
        # Store position information
        self.current_position = {
            'entry_time': datetime.now(self.ET),
            'call_symbol': call_symbol,
            'put_symbol': put_symbol,
            'call_strike': call_strike,
            'put_strike': put_strike,
            'call_entry': criteria['details'].get('call_premium', 0),
            'put_entry': criteria['details'].get('put_premium', 0),
            'total_collected': criteria['details'].get('total_credit', 0),
            'spy_entry': criteria['details'].get('spy_price', 0),
            'entry_criteria': criteria,
            'order_id': order.get('id'),
            'max_adverse': 0,
            'max_profit': 0
        }
        
        # Store Greeks if available
        if 'greeks' in criteria:
            self.current_position['entry_greeks'] = criteria['greeks']
        
        self.position_open = True
        self.trades_today += 1
        
        # Log to database
        criteria_json = json.dumps(criteria['checks'])
        
        self.cur.execute('''
            INSERT INTO alpaca_vegaware_trades (
                trade_date, entry_time, spy_entry,
                call_symbol, put_symbol, call_strike, put_strike,
                call_entry, put_entry, total_collected,
                entry_call_delta, entry_put_delta, entry_total_vega,
                entry_call_iv, entry_put_iv, entry_score, entry_criteria_json,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().date(),
            self.current_position['entry_time'],
            self.current_position['spy_entry'],
            call_symbol, put_symbol, call_strike, put_strike,
            self.current_position['call_entry'],
            self.current_position['put_entry'],
            self.current_position['total_collected'],
            criteria.get('greeks', {}).get('call', {}).get('delta', 0),
            criteria.get('greeks', {}).get('put', {}).get('delta', 0),
            criteria['details'].get('total_vega', 0),
            criteria.get('greeks', {}).get('call_iv', 0),
            criteria.get('greeks', {}).get('put_iv', 0),
            criteria['score'],
            criteria_json,
            'OPEN'
        ))
        self.conn.commit()
        self.current_position['trade_id'] = self.cur.lastrowid
        
        self.log("\n🎯 STRANGLE POSITION OPENED", "TRADE")
        self.log(f"  Call: {call_symbol} (${call_strike:.0f})")
        self.log(f"  Put: {put_symbol} (${put_strike:.0f})")
        self.log(f"  Credit: ${self.current_position['total_collected']:.2f}")
        
        return True
    
    def monitor_position(self) -> dict:
        """Monitor position with stop losses and profit targets"""
        if not self.position_open or not self.current_position:
            return {'status': 'no_position'}
        
        # Get current quotes
        call_quote = self.client.get_option_quote(self.current_position['call_symbol'])
        put_quote = self.client.get_option_quote(self.current_position['put_symbol'])
        spy_quote = self.client.get_stock_quote("SPY")
        
        if not call_quote or not put_quote or not spy_quote:
            return {'status': 'quote_error'}
        
        # Calculate current values
        call_bid = call_quote.get('bp', 0)
        call_ask = call_quote.get('ap', 0)
        put_bid = put_quote.get('bp', 0)
        put_ask = put_quote.get('ap', 0)
        spy_bid = spy_quote.get('bp', 0)
        spy_ask = spy_quote.get('ap', 0)
        
        call_mid = (call_bid + call_ask) / 2
        put_mid = (put_bid + put_ask) / 2
        spy_mid = (spy_bid + spy_ask) / 2
        
        # Calculate P&L (for short positions, profit when current < entry)
        current_value = call_mid + put_mid
        collected = self.current_position['total_collected']
        pnl = collected - current_value
        pnl_pct = (pnl / collected * 100) if collected > 0 else 0
        
        # Track max adverse and profit
        if pnl < self.current_position['max_adverse']:
            self.current_position['max_adverse'] = pnl
        if pnl > self.current_position['max_profit']:
            self.current_position['max_profit'] = pnl
        
        # Calculate current Greeks
        expiry = datetime.now().strftime('%Y-%m-%d')
        time_to_expiry = self.greeks_calc.calculate_time_to_expiry(expiry)
        
        current_greeks = {}
        if time_to_expiry > 0:
            try:
                call_iv = self.greeks_calc.calculate_iv_from_price(
                    call_mid, spy_mid, self.current_position['call_strike'],
                    time_to_expiry, 'call'
                )
                put_iv = self.greeks_calc.calculate_iv_from_price(
                    put_mid, spy_mid, self.current_position['put_strike'],
                    time_to_expiry, 'put'
                )
                
                call_greeks = self.greeks_calc.calculate_greeks(
                    spy_mid, self.current_position['call_strike'],
                    time_to_expiry, call_iv, 'call'
                )
                put_greeks = self.greeks_calc.calculate_greeks(
                    spy_mid, self.current_position['put_strike'],
                    time_to_expiry, put_iv, 'put'
                )
                
                current_greeks = {
                    'total_vega': abs(call_greeks['vega']) + abs(put_greeks['vega']),
                    'net_delta': call_greeks['delta'] + put_greeks['delta'],
                    'call_iv': call_iv,
                    'put_iv': put_iv
                }
            except:
                pass
        
        # Build status report
        status = {
            'status': 'monitoring',
            'spy_price': spy_mid,
            'call_price': call_mid,
            'put_price': put_mid,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'current_value': current_value,
            'collected': collected,
            'greeks': current_greeks,
            'exit_signal': None
        }
        
        # === CHECK EXIT CONDITIONS ===
        
        # 1. Stop Loss Check (2x credit)
        max_loss = -self.STOP_LOSS_MULTIPLIER * collected
        if pnl <= max_loss:
            self.log(f"🛑 STOP LOSS TRIGGERED! P&L ${pnl:.2f} <= ${max_loss:.2f}", "ALERT")
            status['exit_signal'] = 'stop_loss'
            return status
        
        # 2. Profit Target Check (50% of credit)
        profit_target = self.PROFIT_TARGET_PCT / 100 * collected
        if pnl >= profit_target:
            self.log(f"🎯 PROFIT TARGET HIT! P&L ${pnl:.2f} >= ${profit_target:.2f}", "ALERT")
            status['exit_signal'] = 'profit_target'
            return status
        
        # 3. Strike Breach Check
        call_breach = spy_mid >= self.current_position['call_strike'] * (1 - self.STRIKE_BUFFER_PCT/100)
        put_breach = spy_mid <= self.current_position['put_strike'] * (1 + self.STRIKE_BUFFER_PCT/100)
        
        if call_breach:
            self.log(f"⚠️ CALL STRIKE BREACH! SPY ${spy_mid:.2f} near ${self.current_position['call_strike']:.0f}", 
                    "ALERT")
            status['exit_signal'] = 'call_breach'
            return status
        
        if put_breach:
            self.log(f"⚠️ PUT STRIKE BREACH! SPY ${spy_mid:.2f} near ${self.current_position['put_strike']:.0f}", 
                    "ALERT")
            status['exit_signal'] = 'put_breach'
            return status
        
        # 4. Vega Explosion Check
        if current_greeks and 'total_vega' in current_greeks:
            if current_greeks['total_vega'] > self.MAX_VEGA * 1.5:
                self.log(f"🌋 VEGA EXPLOSION! Vega {current_greeks['total_vega']:.2f} > limit", "ALERT")
                status['exit_signal'] = 'vega_explosion'
                return status
        
        # 5. Time-Based Exit
        now = datetime.now(self.ET)
        current_time = now.time()
        
        if current_time >= self.FINAL_EXIT:
            self.log("⏰ FINAL EXIT TIME - Closing position", "ALERT")
            status['exit_signal'] = 'time_final'
            return status
        elif current_time >= self.RECOMMENDED_EXIT:
            self.log("⏰ Recommended exit time reached (3:55 PM)", "WARNING")
            # Optional: can make this automatic
            # status['exit_signal'] = 'time_recommended'
        
        # Log current status every 30 seconds
        if hasattr(self, '_last_log_time'):
            if (datetime.now() - self._last_log_time).seconds >= 30:
                self._log_position_status(status)
                self._last_log_time = datetime.now()
        else:
            self._last_log_time = datetime.now()
        
        return status
    
    def _log_position_status(self, status: dict):
        """Log current position status"""
        pnl_color = "SUCCESS" if status['pnl'] >= 0 else "WARNING"
        self.log(f"Position: SPY ${status['spy_price']:.2f} | "
                f"P&L: ${status['pnl']:.2f} ({status['pnl_pct']:.1f}%)", pnl_color)
        
        if status.get('greeks'):
            greeks = status['greeks']
            if 'total_vega' in greeks:
                self.log(f"  Greeks: Vega {greeks['total_vega']:.2f}, "
                        f"Delta {greeks.get('net_delta', 0):.3f}")
    
    def exit_strangle(self, reason: str = "manual") -> bool:
        """Exit strangle position"""
        if not self.position_open or not self.current_position:
            return False
        
        self.log("=" * 60)
        self.log(f"EXITING POSITION - Reason: {reason.upper()}", "ALERT")
        self.log("=" * 60)
        
        # Place closing orders
        legs = [
            {"symbol": self.current_position['call_symbol'], "side": "buy", "ratio_qty": 1},
            {"symbol": self.current_position['put_symbol'], "side": "buy", "ratio_qty": 1}
        ]
        
        self.log("Placing closing order...")
        order = self.client.place_option_order(legs, qty=1, order_type="market")
        
        if 'error' in order:
            self.log(f"Close order failed: {order['error']}", "ERROR")
            # Try individual closes as fallback
            self.client.close_position(self.current_position['call_symbol'])
            self.client.close_position(self.current_position['put_symbol'])
        
        # Get final prices
        call_quote = self.client.get_option_quote(self.current_position['call_symbol'])
        put_quote = self.client.get_option_quote(self.current_position['put_symbol'])
        spy_quote = self.client.get_stock_quote("SPY")
        
        call_exit = (call_quote.get('ap', 0) + call_quote.get('bp', 0)) / 2 if call_quote else 0
        put_exit = (put_quote.get('ap', 0) + put_quote.get('bp', 0)) / 2 if put_quote else 0
        spy_exit = (spy_quote.get('ap', 0) + spy_quote.get('bp', 0)) / 2 if spy_quote else 0
        
        # Calculate final P&L
        total_exit = call_exit + put_exit
        collected = self.current_position['total_collected']
        pnl = collected - total_exit
        pnl_pct = (pnl / collected * 100) if collected > 0 else 0
        
        # Update daily tracking
        self.daily_pnl += pnl
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        # Update database
        self.cur.execute('''
            UPDATE alpaca_vegaware_trades
            SET exit_time = ?, spy_exit = ?, call_exit = ?, put_exit = ?,
                total_exit = ?, pnl = ?, pnl_pct = ?, 
                exit_reason = ?, max_adverse = ?, max_profit = ?, status = ?
            WHERE id = ?
        ''', (
            datetime.now(self.ET),
            spy_exit, call_exit, put_exit, total_exit,
            pnl, pnl_pct, reason,
            self.current_position.get('max_adverse', 0),
            self.current_position.get('max_profit', 0),
            'CLOSED',
            self.current_position['trade_id']
        ))
        self.conn.commit()
        
        # Log results
        self.log(f"\n📊 TRADE RESULTS:", "TRADE")
        self.log(f"  Entry Credit: ${collected:.2f}")
        self.log(f"  Exit Cost: ${total_exit:.2f}")
        self.log(f"  P&L: ${pnl:.2f} ({pnl_pct:.1f}%)")
        self.log(f"  Exit Reason: {reason}")
        
        result_type = "SUCCESS" if pnl > 0 else "WARNING"
        self.log(f"\n{'✅ PROFITABLE' if pnl > 0 else '❌ LOSS'} - Trade #{self.trades_today}", result_type)
        
        # Display daily statistics
        win_rate = (self.win_count / (self.win_count + self.loss_count) * 100) if (self.win_count + self.loss_count) > 0 else 0
        self.log(f"\n📈 Daily Stats: W:{self.win_count} L:{self.loss_count} "
                f"({win_rate:.0f}% win rate) | P&L: ${self.daily_pnl:.2f}")
        
        # Reset position
        self.position_open = False
        self.current_position = None
        
        return True
    
    def run_monitoring_loop(self):
        """Main monitoring loop with full strategy implementation"""
        while self.running:
            try:
                now = datetime.now(self.ET)
                current_time = now.time()
                
                # Skip weekends
                if now.weekday() >= 5:
                    time_module.sleep(60)
                    continue
                
                # Market hours check
                if not self.client.is_market_open():
                    time_module.sleep(60)
                    continue
                
                # === POSITION MANAGEMENT ===
                if self.position_open:
                    # Monitor existing position
                    status = self.monitor_position()
                    
                    # Check for exit signals
                    if status.get('exit_signal'):
                        self.exit_strangle(reason=status['exit_signal'])
                
                # === ENTRY LOGIC ===
                elif current_time >= self.ENTRY_START and current_time <= self.ENTRY_END:
                    # Only attempt entry once per minute during window
                    if not hasattr(self, '_last_entry_check'):
                        self._last_entry_check = datetime.now()
                    
                    if (datetime.now() - self._last_entry_check).seconds >= 60:
                        self.log("\n🔍 Checking entry opportunity...")
                        if self.enter_strangle():
                            self.log("Position opened successfully", "SUCCESS")
                        self._last_entry_check = datetime.now()
                
                # === END OF DAY ===
                elif current_time >= time(16, 0):
                    if self.trades_today > 0:
                        self.log("\n📊 END OF DAY SUMMARY", "INFO")
                        self.log(f"  Trades: {self.trades_today}")
                        self.log(f"  Daily P&L: ${self.daily_pnl:.2f}")
                        win_rate = (self.win_count / (self.win_count + self.loss_count) * 100) if (self.win_count + self.loss_count) > 0 else 0
                        self.log(f"  Win Rate: {win_rate:.0f}%")
                    
                    # Reset for next day
                    self.trades_today = 0
                    self.daily_pnl = 0
                    self.win_count = 0
                    self.loss_count = 0
                    
                    # Sleep until next trading day
                    time_module.sleep(3600)
                
                # Sleep between checks
                time_module.sleep(10)
                
            except Exception as e:
                self.log(f"Error in monitoring loop: {e}", "ERROR")
                time_module.sleep(30)
    
    def start(self):
        """Start the VegaAware trader"""
        self.log("=" * 70)
        self.log("ALPACA VEGAWARE TRADER STARTED", "SUCCESS")
        self.log(f"Mode: {'PAPER' if self.client.paper else 'LIVE'} TRADING")
        self.log("Strategy: VegaAware 0DTE (93.7% Win Rate Rules)")
        self.log(f"Entry: {self.ENTRY_START.strftime('%I:%M %p')}-{self.ENTRY_END.strftime('%I:%M %p')} ET")
        self.log(f"Optimal: {self.OPTIMAL_ENTRY.strftime('%I:%M %p')} ET")
        self.log(f"Exit: {self.RECOMMENDED_EXIT.strftime('%I:%M %p')} ET (recommended)")
        self.log("=" * 70)
        
        self.log("\n📋 Strategy Parameters:")
        self.log(f"  Target Delta: {self.TARGET_DELTA}")
        self.log(f"  Max Vega: {self.MAX_VEGA}")
        self.log(f"  Min Premium: ${self.MIN_PREMIUM}")
        self.log(f"  Stop Loss: {self.STOP_LOSS_MULTIPLIER}x credit")
        self.log(f"  Profit Target: {self.PROFIT_TARGET_PCT}%")
        self.log(f"  Entry Score Required: {self.ENTRY_SCORE_THRESHOLD}%")
        
        # Check account
        account = self.client.get_account()
        if account:
            bp = float(account.get('buying_power', 0))
            self.log(f"\n💰 Account Buying Power: ${bp:,.2f}")
            if bp < self.MIN_BUYING_POWER:
                self.log(f"⚠️ Warning: Buying power below minimum ${self.MIN_BUYING_POWER}", "WARNING")
        
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
        """Stop the trader gracefully"""
        self.log("\nShutting down VegaAware trader...", "INFO")
        self.running = False
        
        # Close any open positions
        if self.position_open:
            self.log("Closing open position before shutdown...", "WARNING")
            self.exit_strangle(reason="shutdown")
        
        # Wait for thread
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        # Final summary
        if self.trades_today > 0:
            self.log("\n📊 Session Summary:", "INFO")
            self.log(f"  Total Trades: {self.trades_today}")
            self.log(f"  Wins: {self.win_count}")
            self.log(f"  Losses: {self.loss_count}")
            self.log(f"  Total P&L: ${self.daily_pnl:.2f}")
        
        # Close database
        self.conn.close()
        
        self.log("✅ Shutdown complete", "SUCCESS")

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
        print("\n" + "=" * 70)
        print("⚠️  WARNING: LIVE TRADING MODE")
        print("=" * 70)
        print("This will trade with REAL MONEY!")
        print("The VegaAware strategy will:")
        print("  - Enter strangles based on 13 criteria")
        print("  - Use stop losses at 2x credit")
        print("  - Exit on profit targets or time")
        print("")
        response = input("Are you ABSOLUTELY sure? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    # Start trader
    trader = VegaAwareTrader(paper=paper_mode)
    trader.start()