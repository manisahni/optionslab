#!/usr/bin/env python3
"""
Dummy Testing Strategy - Ultra-aggressive parameters for rapid testing
Tests all edge cases including Greeks-based exits
Hold time: 2-5 minutes per trade
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient, OptionsManager, OrderManager
from core.greeks_calculator import GreeksCalculator
from core.trade_logger import TradeLogger
from datetime import datetime, timedelta
import time
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dummy_test_strategy.log')
    ]
)
logger = logging.getLogger(__name__)

class DummyTestStrategy:
    """Ultra-aggressive testing strategy with comprehensive exit conditions"""
    
    def __init__(self, env="sandbox"):
        self.client = TradierClient(env=env)
        self.options_mgr = OptionsManager(self.client)
        self.order_mgr = OrderManager(self.client)
        self.greeks_calc = GreeksCalculator()
        self.trade_logger = TradeLogger()
        
        # ULTRA LIBERAL Entry parameters
        self.MIN_DELTA = 0.05      # Very low delta acceptable
        self.MAX_DELTA = 0.25      # Wide range
        self.MIN_PREMIUM = 0.01    # Basically any premium
        self.SCORE_REQUIRED = 20   # Very low score requirement
        
        # Time parameters
        self.MIN_HOLD_TIME = 120   # 2 minutes minimum
        self.MAX_HOLD_TIME = 300   # 5 minutes maximum
        
        # P&L Exit parameters
        self.PROFIT_TARGET = 1.0    # $1 profit
        self.PROFIT_PCT = 0.05      # 5% of credit
        self.STOP_LOSS = 5.0        # $5 loss
        self.STOP_PCT = 0.25        # 25% of credit
        self.BREAKEVEN_EXIT = 0.50  # Quick $0.50 profit
        
        # Greeks Exit parameters
        self.MAX_TOTAL_DELTA = 0.20     # Position too directional
        self.MAX_CALL_DELTA = 0.30      # Call getting ITM
        self.MAX_PUT_DELTA = -0.30      # Put getting ITM
        self.MAX_TOTAL_GAMMA = 0.05     # Acceleration risk
        self.MAX_GAMMA_IMBALANCE = 0.03 # One side dominating
        self.MAX_TOTAL_VEGA = 3.0       # High vol exposure
        self.MAX_VEGA_IMBALANCE = 2.0   # One side too sensitive
        self.MIN_THETA = -2.0           # Decay accelerating
        self.MAX_THETA = 0.5            # Unusual positive theta
        
        # Price movement exits
        self.MAX_SPY_MOVE = 1.0         # $1 move from entry
        self.MAX_SPY_MOVE_PCT = 0.003   # 0.3% move
        self.STRIKE_PROXIMITY = 0.25    # $0.25 from strike
        
        # Tracking
        self.position = None
        self.entry_spy_price = 0
        self.entry_time = None
        self.credit_received = 0
        self.entry_greeks = {}
        self.trades_executed = 0
        self.max_trades = 25
        self.exit_reasons = {}
        
    def calculate_current_greeks(self, spy_price: float) -> dict:
        """Calculate real-time Greeks for current position"""
        if not self.position:
            return {}
        
        # Get current option quotes
        strangle_quotes = self.options_mgr.get_strangle_quotes(
            self.position['call_symbol'],
            self.position['put_symbol']
        )
        
        if not strangle_quotes:
            return {}
        
        # Calculate time to expiry
        now = datetime.now()
        expiry_time = now.replace(hour=16, minute=0, second=0)
        time_to_expiry = max((expiry_time - now).total_seconds() / (365 * 24 * 3600), 1e-6)
        
        # Calculate IV from market prices
        call_mid = strangle_quotes['call']['mid']
        put_mid = strangle_quotes['put']['mid']
        
        # Use Greeks calculator to get IV
        call_iv = self.greeks_calc.calculate_iv_from_price(
            spy_price, self.position['call_strike'], time_to_expiry, 
            call_mid, 'call'
        )
        put_iv = self.greeks_calc.calculate_iv_from_price(
            spy_price, self.position['put_strike'], time_to_expiry,
            put_mid, 'put'
        )
        
        # Default IVs if calculation fails
        if not call_iv:
            call_iv = 0.15
        if not put_iv:
            put_iv = 0.15
        
        # Calculate strangle Greeks (short position = -1 quantity)
        greeks = self.greeks_calc.calculate_strangle_greeks(
            spy_price,
            self.position['call_strike'],
            self.position['put_strike'],
            time_to_expiry,
            call_iv,
            put_iv,
            call_qty=-1,
            put_qty=-1
        )
        
        # Add additional info
        greeks['spy_price'] = spy_price
        greeks['call_iv'] = call_iv
        greeks['put_iv'] = put_iv
        greeks['time_to_expiry_hours'] = time_to_expiry * 365 * 24
        
        return greeks
    
    def check_entry_criteria(self) -> dict:
        """Check ultra-liberal entry criteria"""
        criteria = {
            'met': [],
            'not_met': [],
            'score': 0
        }
        
        # 1. Market must be open
        if not self.client.is_market_open():
            criteria['not_met'].append("Market closed")
            return criteria
        
        criteria['met'].append("✅ Market open")
        
        # 2. Get SPY quote
        quotes = self.client.get_quotes(['SPY'])
        if not quotes or 'quotes' not in quotes:
            criteria['not_met'].append("No SPY quote")
            return criteria
        
        quote = quotes['quotes'].get('quote', {})
        if isinstance(quote, list):
            quote = quote[0]
        
        spy_price = (quote.get('bid', 0) + quote.get('ask', 0)) / 2
        criteria['met'].append(f"✅ SPY at ${spy_price:.2f}")
        
        # 3. Find strikes (very liberal)
        strikes = self.options_mgr.find_strangle_strikes(
            'SPY', 
            target_delta=0.10,  # Lower delta for wider strikes
            dte=0
        )
        
        if not strikes:
            criteria['not_met'].append("No strikes found")
            return criteria
        
        call_option, put_option = strikes
        criteria['met'].append(f"✅ Strikes: C${call_option['strike']} P${put_option['strike']}")
        
        # 4. Get quotes
        strangle_quotes = self.options_mgr.get_strangle_quotes(
            call_option['symbol'],
            put_option['symbol']
        )
        
        if strangle_quotes:
            call_mid = strangle_quotes['call']['mid']
            put_mid = strangle_quotes['put']['mid']
            
            # Ultra-liberal premium check
            if call_mid >= self.MIN_PREMIUM:
                criteria['met'].append(f"✅ Call premium ${call_mid:.2f}")
            if put_mid >= self.MIN_PREMIUM:
                criteria['met'].append(f"✅ Put premium ${put_mid:.2f}")
        
        # 5. Check buying power
        balances = self.client.get_balances()
        if balances and 'balances' in balances:
            margin = balances['balances'].get('margin', {})
            bp = margin.get('option_buying_power', 0)
            if bp > 1000:
                criteria['met'].append(f"✅ BP: ${bp:,.0f}")
            else:
                criteria['not_met'].append(f"Low BP: ${bp:,.0f}")
        
        # Calculate ultra-liberal score
        total = len(criteria['met']) + len(criteria['not_met'])
        score = (len(criteria['met']) / total * 100) if total > 0 else 0
        criteria['score'] = score
        
        return criteria
    
    def place_entry(self) -> bool:
        """Place strangle entry with logging"""
        logger.info("=" * 60)
        logger.info(f"TRADE #{self.trades_executed + 1} - CHECKING ENTRY")
        
        criteria = self.check_entry_criteria()
        logger.info(f"Entry Score: {criteria['score']:.0f}%")
        
        if criteria['score'] < self.SCORE_REQUIRED:
            logger.info(f"Score too low ({criteria['score']:.0f}% < {self.SCORE_REQUIRED}%)")
            return False
        
        # Get SPY price
        quotes = self.client.get_quotes(['SPY'])
        quote = quotes['quotes'].get('quote', {})
        if isinstance(quote, list):
            quote = quote[0]
        spy_price = (quote.get('bid', 0) + quote.get('ask', 0)) / 2
        
        # Find strikes
        strikes = self.options_mgr.find_strangle_strikes('SPY', target_delta=0.10, dte=0)
        if not strikes:
            return False
        
        call_option, put_option = strikes
        
        # Get quotes
        strangle_quotes = self.options_mgr.get_strangle_quotes(
            call_option['symbol'],
            put_option['symbol']
        )
        
        if strangle_quotes:
            credit = self.options_mgr.calculate_strangle_credit(
                strangle_quotes['call'],
                strangle_quotes['put']
            )
            logger.info(f"Expected Credit: ${credit:.2f}")
        else:
            credit = 0
        
        # Place order
        logger.info(f"PLACING STRANGLE: {call_option['symbol']} / {put_option['symbol']}")
        result = self.order_mgr.place_strangle(
            call_option['symbol'],
            put_option['symbol'],
            quantity=1
        )
        
        if result:
            self.position = {
                'call_symbol': call_option['symbol'],
                'call_strike': call_option['strike'],
                'put_symbol': put_option['symbol'],
                'put_strike': put_option['strike'],
                'credit': credit,
                'entry_time': datetime.now(),
                'entry_spy': spy_price
            }
            
            self.entry_spy_price = spy_price
            self.entry_time = datetime.now()
            self.credit_received = credit
            self.trades_executed += 1
            
            # Calculate entry Greeks
            self.entry_greeks = self.calculate_current_greeks(spy_price)
            
            logger.info("✅ ENTRY SUCCESSFUL")
            logger.info(f"Entry SPY: ${spy_price:.2f}")
            logger.info(f"Entry Greeks:")
            logger.info(f"  Delta: {self.entry_greeks.get('delta', 0):.3f}")
            logger.info(f"  Gamma: {self.entry_greeks.get('gamma', 0):.3f}")
            logger.info(f"  Vega: {self.entry_greeks.get('vega', 0):.2f}")
            logger.info(f"  Theta: {self.entry_greeks.get('theta', 0):.2f}")
            
            # Log to database
            self.trade_logger.log_strangle_entry(
                call_option['symbol'],
                put_option['symbol'],
                call_option['strike'],
                put_option['strike'],
                credit,
                spy_price
            )
            
            return True
        
        return False
    
    def check_exit_conditions(self) -> tuple:
        """Check all exit conditions and return (should_exit, reason)"""
        if not self.position:
            return False, None
        
        now = datetime.now()
        time_in_position = (now - self.entry_time).total_seconds()
        
        # Get current SPY price
        quotes = self.client.get_quotes(['SPY'])
        if not quotes:
            return False, None
        
        quote = quotes['quotes'].get('quote', {})
        if isinstance(quote, list):
            quote = quote[0]
        spy_price = (quote.get('bid', 0) + quote.get('ask', 0)) / 2
        
        # Get current P&L
        strangle_pos = self.order_mgr.get_strangle_positions()
        if not strangle_pos:
            return True, "Position disappeared"
        
        total_pl = 0
        for call in strangle_pos.get('calls', []):
            total_pl += call['unrealized_pl']
        for put in strangle_pos.get('puts', []):
            total_pl += put['unrealized_pl']
        
        # Calculate current Greeks
        current_greeks = self.calculate_current_greeks(spy_price)
        
        # Log current status
        logger.debug(f"Time: {time_in_position:.0f}s, P&L: ${total_pl:.2f}, SPY: ${spy_price:.2f}")
        
        # === TIME-BASED EXITS ===
        if time_in_position >= self.MAX_HOLD_TIME:
            return True, f"MAX_HOLD_TIME ({self.MAX_HOLD_TIME}s)"
        
        if now.hour == 15 and now.minute >= 55:
            return True, "MARKET_CLOSE"
        
        # Only check other exits after minimum hold time
        if time_in_position < self.MIN_HOLD_TIME:
            return False, None
        
        # === P&L EXITS ===
        if total_pl >= self.PROFIT_TARGET:
            return True, f"PROFIT_TARGET (${total_pl:.2f})"
        
        if self.credit_received > 0 and total_pl >= self.credit_received * self.PROFIT_PCT:
            return True, f"PROFIT_PCT ({self.PROFIT_PCT*100:.0f}% of credit)"
        
        if total_pl >= self.BREAKEVEN_EXIT:
            return True, f"BREAKEVEN_EXIT (${total_pl:.2f})"
        
        if total_pl <= -self.STOP_LOSS:
            return True, f"STOP_LOSS (${total_pl:.2f})"
        
        if self.credit_received > 0 and total_pl <= -self.credit_received * self.STOP_PCT:
            return True, f"STOP_PCT ({self.STOP_PCT*100:.0f}% of credit)"
        
        # === GREEKS EXITS ===
        if current_greeks:
            # Delta exits
            total_delta = abs(current_greeks.get('delta', 0))
            if total_delta > self.MAX_TOTAL_DELTA:
                return True, f"MAX_DELTA ({total_delta:.3f})"
            
            call_delta = current_greeks.get('call_delta', 0)
            if call_delta > self.MAX_CALL_DELTA:
                return True, f"CALL_DELTA_HIGH ({call_delta:.3f})"
            
            put_delta = current_greeks.get('put_delta', 0)
            if put_delta < self.MAX_PUT_DELTA:
                return True, f"PUT_DELTA_HIGH ({put_delta:.3f})"
            
            # Gamma exits
            total_gamma = abs(current_greeks.get('gamma', 0))
            if total_gamma > self.MAX_TOTAL_GAMMA:
                return True, f"MAX_GAMMA ({total_gamma:.3f})"
            
            # Vega exits
            total_vega = abs(current_greeks.get('vega', 0))
            if total_vega > self.MAX_TOTAL_VEGA:
                return True, f"MAX_VEGA ({total_vega:.2f})"
            
            # Theta exits
            theta = current_greeks.get('theta', 0)
            if theta < self.MIN_THETA:
                return True, f"MIN_THETA ({theta:.2f})"
            if theta > self.MAX_THETA:
                return True, f"MAX_THETA ({theta:.2f})"
        
        # === PRICE MOVEMENT EXITS ===
        spy_move = abs(spy_price - self.entry_spy_price)
        if spy_move > self.MAX_SPY_MOVE:
            return True, f"SPY_MOVE (${spy_move:.2f})"
        
        spy_move_pct = spy_move / self.entry_spy_price
        if spy_move_pct > self.MAX_SPY_MOVE_PCT:
            return True, f"SPY_MOVE_PCT ({spy_move_pct*100:.2f}%)"
        
        # Check proximity to strikes
        call_distance = abs(spy_price - self.position['call_strike'])
        put_distance = abs(spy_price - self.position['put_strike'])
        
        if call_distance <= self.STRIKE_PROXIMITY:
            return True, f"NEAR_CALL_STRIKE (${call_distance:.2f})"
        if put_distance <= self.STRIKE_PROXIMITY:
            return True, f"NEAR_PUT_STRIKE (${put_distance:.2f})"
        
        return False, None
    
    def close_position(self, reason: str) -> bool:
        """Close position and log results"""
        if not self.position:
            return False
        
        logger.info("=" * 60)
        logger.info(f"CLOSING POSITION - Reason: {reason}")
        
        # Get final P&L
        strangle_pos = self.order_mgr.get_strangle_positions()
        total_pl = 0
        if strangle_pos:
            for call in strangle_pos.get('calls', []):
                total_pl += call['unrealized_pl']
            for put in strangle_pos.get('puts', []):
                total_pl += put['unrealized_pl']
        
        # Calculate final Greeks
        quotes = self.client.get_quotes(['SPY'])
        quote = quotes['quotes'].get('quote', {})
        if isinstance(quote, list):
            quote = quote[0]
        spy_price = (quote.get('bid', 0) + quote.get('ask', 0)) / 2
        
        exit_greeks = self.calculate_current_greeks(spy_price)
        
        # Calculate hold time
        hold_time = (datetime.now() - self.entry_time).total_seconds()
        
        # Close the position
        result = self.order_mgr.close_strangle(
            self.position['call_symbol'],
            self.position['put_symbol']
        )
        
        if result:
            logger.info("✅ POSITION CLOSED")
            logger.info(f"Hold Time: {hold_time:.0f} seconds")
            logger.info(f"P&L: ${total_pl:.2f}")
            logger.info(f"SPY Move: ${spy_price - self.entry_spy_price:.2f}")
            
            if exit_greeks:
                logger.info(f"Exit Greeks:")
                logger.info(f"  Delta: {exit_greeks.get('delta', 0):.3f}")
                logger.info(f"  Gamma: {exit_greeks.get('gamma', 0):.3f}")
                logger.info(f"  Vega: {exit_greeks.get('vega', 0):.2f}")
                logger.info(f"  Theta: {exit_greeks.get('theta', 0):.2f}")
            
            # Track exit reason
            if reason not in self.exit_reasons:
                self.exit_reasons[reason] = 0
            self.exit_reasons[reason] += 1
            
            # Log to database
            self.trade_logger.log_strangle_exit(
                self.position['call_symbol'],
                self.position['put_symbol'],
                total_pl,
                spy_price
            )
            
            # Clear position
            self.position = None
            self.entry_spy_price = 0
            self.entry_time = None
            self.credit_received = 0
            self.entry_greeks = {}
            
            return True
        
        return False
    
    def run(self):
        """Run the testing strategy"""
        print("=" * 60)
        print("🧪 DUMMY TEST STRATEGY - ULTRA AGGRESSIVE")
        print("=" * 60)
        print(f"Parameters:")
        print(f"  Hold Time: {self.MIN_HOLD_TIME}-{self.MAX_HOLD_TIME} seconds")
        print(f"  Max Trades: {self.max_trades}")
        print(f"  Entry Score Required: {self.SCORE_REQUIRED}%")
        print("=" * 60)
        
        while self.trades_executed < self.max_trades:
            try:
                now = datetime.now()
                
                # Check market hours
                if now.hour >= 16:
                    print("\n🔔 Market closed")
                    break
                
                # If no position, try to enter
                if not self.position:
                    if self.trades_executed > 0:
                        print(f"\n⏳ Waiting 10 seconds before next trade...")
                        time.sleep(10)
                    
                    print(f"\n🎯 Looking for entry (Trade #{self.trades_executed + 1}/{self.max_trades})")
                    self.place_entry()
                
                # If in position, monitor for exit
                else:
                    should_exit, reason = self.check_exit_conditions()
                    
                    if should_exit:
                        self.close_position(reason)
                        
                        # Print statistics
                        print("\n📊 EXIT STATISTICS:")
                        for exit_reason, count in self.exit_reasons.items():
                            print(f"  {exit_reason}: {count}")
                
                # Wait before next check
                if self.position:
                    time.sleep(2)  # Check every 2 seconds when in position
                else:
                    time.sleep(5)  # Check every 5 seconds when looking for entry
                
            except KeyboardInterrupt:
                print("\n\n✋ Strategy stopped by user")
                if self.position:
                    self.close_position("USER_STOP")
                break
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                time.sleep(5)
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        print(f"Total Trades: {self.trades_executed}")
        print("\nExit Reasons:")
        for reason, count in sorted(self.exit_reasons.items(), key=lambda x: x[1], reverse=True):
            pct = (count / self.trades_executed * 100) if self.trades_executed > 0 else 0
            print(f"  {reason}: {count} ({pct:.0f}%)")
        
        # Get overall P&L from database
        stats = self.trade_logger.get_statistics()
        if stats:
            print(f"\nOverall P&L: ${stats['total_pnl']:.2f}")
            print(f"Win Rate: {stats['win_rate']:.1f}%")
            print(f"Avg Hold Time: {stats.get('avg_hold_time', 0):.0f} seconds")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Dummy Test Strategy')
    parser.add_argument('--max-trades', type=int, default=25,
                       help='Maximum number of trades to execute')
    parser.add_argument('--no-confirm', action='store_true',
                       help='Skip confirmation prompt')
    args = parser.parse_args()
    
    print("⚠️  SANDBOX MODE - Paper Trading Only")
    print("This strategy uses ultra-aggressive parameters for testing")
    
    if not args.no_confirm:
        try:
            response = input("Type 'YES' to continue: ")
            if response.strip().upper() != 'YES':
                print("Exiting...")
                return
        except EOFError:
            print("Running in non-interactive mode...")
    
    strategy = DummyTestStrategy(env="sandbox")
    strategy.max_trades = args.max_trades
    strategy.run()

if __name__ == "__main__":
    main()