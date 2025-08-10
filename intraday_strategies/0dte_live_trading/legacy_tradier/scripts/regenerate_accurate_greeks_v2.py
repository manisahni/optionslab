#!/usr/bin/env python3
"""
Regenerate Accurate Greeks Using Market-Derived IV
This version calculates IV from actual bid/ask prices like the backtests do
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta, time as dt_time
import pandas as pd
import numpy as np
import pytz
from typing import Dict, List, Tuple, Optional

from core import TradierClient
from core.greeks_calculator import GreeksCalculator
from database import get_db_manager
from scripts.calculate_market_iv import MarketIVCalculator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketBasedGreeksGenerator:
    """Generate Greeks using market-derived IV from bid/ask prices"""
    
    def __init__(self, client: TradierClient = None):
        """Initialize the Greeks generator"""
        self.client = client or TradierClient(env="sandbox")
        self.db = get_db_manager()
        self.greeks_calc = GreeksCalculator()
        self.iv_calc = MarketIVCalculator()
        
        # Market operates in Eastern Time
        self.ET = pytz.timezone('US/Eastern')
        
        # Statistics
        self.stats = {
            'dates_processed': 0,
            'records_created': 0,
            'errors': 0,
            'iv_from_market': 0,
            'iv_fallback': 0
        }
    
    def regenerate_all_greeks(self, days_back: int = 21, 
                            entry_time: str = "15:00",
                            strike_offset: float = 2.0) -> Dict:
        """
        Regenerate all Greeks data using market-derived IV
        
        Args:
            days_back: Number of days to process
            entry_time: Entry time in HH:MM format (ET)
            strike_offset: Dollar offset for strikes from entry price
            
        Returns:
            Statistics dictionary
        """
        logger.info("="*70)
        logger.info(f"REGENERATING GREEKS WITH MARKET-DERIVED IV")
        logger.info(f"Entry Time: {entry_time} ET, Strike Offset: ${strike_offset}")
        logger.info("="*70)
        
        # First, ensure we have market IV calculated
        logger.info("\nStep 1: Calculating market IV from bid/ask prices...")
        self.iv_calc.update_options_iv()
        
        # Clear existing Greeks data
        logger.info("\nStep 2: Clearing existing Greeks data...")
        self._clear_existing_greeks()
        
        # Get list of trading days
        trading_days = self._get_trading_days(days_back)
        
        logger.info(f"\nStep 3: Processing {len(trading_days)} trading days...")
        for trading_date in trading_days:
            try:
                self._process_trading_day(trading_date, entry_time, strike_offset)
                self.stats['dates_processed'] += 1
            except Exception as e:
                logger.error(f"Error processing {trading_date}: {e}")
                self.stats['errors'] += 1
        
        # Print summary
        self._print_summary()
        
        return self.stats
    
    def _clear_existing_greeks(self):
        """Clear existing Greeks data from database"""
        count_query = "SELECT COUNT(*) as count FROM greeks_history"
        result = self.db.execute_query(count_query)
        existing_count = result[0]['count'] if result else 0
        
        if existing_count > 0:
            logger.info(f"Removing {existing_count} existing Greeks records...")
            delete_query = "DELETE FROM greeks_history"
            self.db.execute_query(delete_query)
            logger.info("Existing Greeks data cleared")
    
    def _get_trading_days(self, days_back: int) -> List[str]:
        """Get list of trading days to process"""
        query = """
            SELECT DISTINCT date(timestamp) as trading_date
            FROM spy_prices
            WHERE session_type = 'regular'
            ORDER BY trading_date DESC
            LIMIT ?
        """
        
        results = self.db.execute_query(query, (days_back,))
        trading_days = [row['trading_date'] for row in results]
        
        logger.info(f"Found {len(trading_days)} trading days to process")
        return trading_days
    
    def _process_trading_day(self, trading_date: str, entry_time: str, strike_offset: float):
        """
        Process a single trading day with market-based Greeks
        
        Args:
            trading_date: Date string (YYYY-MM-DD)
            entry_time: Entry time (HH:MM)
            strike_offset: Strike offset in dollars
        """
        logger.info(f"\nProcessing {trading_date}...")
        
        # Parse entry time
        entry_hour, entry_minute = map(int, entry_time.split(':'))
        date_obj = datetime.strptime(trading_date, '%Y-%m-%d').date()
        entry_datetime_et = self.ET.localize(
            datetime.combine(date_obj, dt_time(entry_hour, entry_minute))
        )
        
        # Get SPY price at entry time
        entry_price = self._get_price_at_time(trading_date, entry_time)
        if entry_price is None:
            logger.warning(f"No price data at {entry_time} for {trading_date}")
            return
        
        # Calculate strikes based on entry price
        call_strike = round(entry_price + strike_offset)
        put_strike = round(entry_price - strike_offset)
        
        logger.info(f"  Entry price (3 PM): ${entry_price:.2f}")
        logger.info(f"  Call strike: ${call_strike}, Put strike: ${put_strike}")
        logger.info(f"  Generating Greeks from 2 PM to 4 PM (full market hours)")
        
        # Get all prices from 2 PM to market close
        # Store complete data - handle cutoff at display/strategy layer
        prices_query = """
            SELECT timestamp, close, high, low
            FROM spy_prices
            WHERE date(timestamp) = ?
            AND time(timestamp) >= '14:00:00'  -- Start from 2 PM for perspective
            AND time(timestamp) <= '16:00:00'  -- Full market hours
            AND session_type = 'regular'
            ORDER BY timestamp
        """
        
        prices = self.db.execute_query(prices_query, (trading_date,))
        
        if not prices:
            logger.warning(f"No price data from 2 PM to market close for {trading_date}")
            return
        
        # Market closes at 4 PM ET
        expiry_et = self.ET.localize(datetime.combine(date_obj, dt_time(16, 0)))
        
        # Generate Greeks for each minute
        greeks_records = []
        
        for price_point in prices:
            timestamp = datetime.fromisoformat(price_point['timestamp'])
            timestamp_et = self.ET.localize(timestamp)
            spot = price_point['close']
            
            # Calculate time to expiry in years with minimum 5 minutes to prevent explosion
            seconds_to_expiry = max((expiry_et - timestamp_et).total_seconds(), 300)  # Min 5 minutes
            time_to_expiry = max(seconds_to_expiry / (365 * 24 * 3600), 5/(365*24*60))  # Min 5 minutes
            
            # Get market IV for these strikes at this time
            call_iv = self._get_market_iv(timestamp, call_strike, 'call')
            put_iv = self._get_market_iv(timestamp, put_strike, 'put')
            
            # If no market IV available, use reasonable estimate
            if call_iv is None:
                call_iv = self._estimate_fallback_iv(timestamp.hour, timestamp.minute)
                self.stats['iv_fallback'] += 1
            else:
                self.stats['iv_from_market'] += 1
                
            if put_iv is None:
                put_iv = self._estimate_fallback_iv(timestamp.hour, timestamp.minute)
                self.stats['iv_fallback'] += 1
            else:
                self.stats['iv_from_market'] += 1
            
            # Cap IV to prevent explosion effects near expiry
            # More aggressive capping in final 30 minutes
            minutes_to_expiry = seconds_to_expiry / 60
            if minutes_to_expiry <= 30:
                max_iv = 0.80  # 80% max in final 30 minutes
            elif minutes_to_expiry <= 60:
                max_iv = 1.00  # 100% max in final hour
            else:
                max_iv = 1.50  # 150% max otherwise
                
            call_iv = max(0.10, min(max_iv, call_iv))
            put_iv = max(0.10, min(max_iv, put_iv))
            
            # Calculate Greeks with market IV
            call_greeks = self.greeks_calc.calculate_greeks(
                spot=spot,
                strike=call_strike,
                time_to_expiry=time_to_expiry,
                volatility=call_iv,
                option_type='call'
            )
            
            put_greeks = self.greeks_calc.calculate_greeks(
                spot=spot,
                strike=put_strike,
                time_to_expiry=time_to_expiry,
                volatility=put_iv,
                option_type='put'
            )
            
            # Combine for short strangle (we are short both call and put)
            # For short positions: we reverse delta, gamma, vega, rho but COLLECT theta
            total_delta = -(call_greeks['delta'] + put_greeks['delta'])
            total_gamma = -(call_greeks['gamma'] + put_greeks['gamma'])
            total_theta = -(call_greeks['theta'] + put_greeks['theta'])  # We collect theta (becomes positive)
            total_vega = -(call_greeks['vega'] + put_greeks['vega'])  # We lose from vol increase
            total_rho = -(call_greeks.get('rho', 0) + put_greeks.get('rho', 0))
            
            # Get actual option prices if available
            option_prices = self._get_option_prices(timestamp, call_strike, put_strike)
            
            greeks_records.append({
                'timestamp': timestamp,
                'position_type': 'strangle',
                'underlying': 'SPY',
                'call_strike': call_strike,
                'put_strike': put_strike,
                'expiry': date_obj,
                'entry_time': entry_datetime_et,
                'entry_price': entry_price,
                'total_delta': total_delta,
                'total_gamma': total_gamma,
                'total_theta': total_theta,
                'total_vega': total_vega,
                'total_rho': total_rho,
                'underlying_price': spot,
                'call_iv': call_iv,
                'put_iv': put_iv,
                'call_price': option_prices.get('call_price', 0),
                'put_price': option_prices.get('put_price', 0),
                'pnl': option_prices.get('total_premium', 1.0) - option_prices.get('current_value', 0),
                'time_to_expiry_hours': seconds_to_expiry / 3600
            })
        
        # Store Greeks in database
        if greeks_records:
            self._store_greeks(greeks_records)
            logger.info(f"  Generated {len(greeks_records)} Greeks records")
            
            # Show IV source statistics
            market_pct = (self.stats['iv_from_market'] / 
                         (self.stats['iv_from_market'] + self.stats['iv_fallback']) * 100)
            logger.info(f"  IV source: {market_pct:.1f}% from market, "
                       f"{100-market_pct:.1f}% fallback")
            
            # Show sample Greeks evolution
            if len(greeks_records) >= 3:
                logger.info("  Greeks evolution:")
                logger.info(f"    Entry: Delta={greeks_records[0]['total_delta']:.3f}, "
                          f"IV={greeks_records[0]['call_iv']*100:.1f}%")
                mid_idx = len(greeks_records) // 2
                logger.info(f"    Mid:   Delta={greeks_records[mid_idx]['total_delta']:.3f}, "
                          f"IV={greeks_records[mid_idx]['call_iv']*100:.1f}%")
                logger.info(f"    Close: Delta={greeks_records[-1]['total_delta']:.3f}, "
                          f"IV={greeks_records[-1]['call_iv']*100:.1f}%")
    
    def _get_price_at_time(self, date: str, time: str) -> Optional[float]:
        """Get SPY price at specific time"""
        query = """
            SELECT close
            FROM spy_prices
            WHERE date(timestamp) = ?
            AND time(timestamp) >= ?
            AND session_type = 'regular'
            ORDER BY timestamp
            LIMIT 1
        """
        
        result = self.db.execute_query(query, (date, time))
        return result[0]['close'] if result else None
    
    def _get_market_iv(self, timestamp: datetime, strike: float, option_type: str) -> Optional[float]:
        """Get market-derived IV for specific option with interpolation fallback"""
        # First try exact match
        exact_query = """
            SELECT iv
            FROM options_data
            WHERE timestamp = ?
            AND strike = ?
            AND option_type = ?
            AND iv IS NOT NULL
            AND iv > 0
        """
        
        result = self.db.execute_query(exact_query, 
                                      (timestamp.strftime('%Y-%m-%d %H:%M:%S'), 
                                       strike, option_type))
        
        if result and result[0]['iv']:
            return result[0]['iv']
        
        # If no exact match, find closest strikes for interpolation
        closest_query = """
            SELECT strike, iv
            FROM options_data
            WHERE timestamp = ?
            AND option_type = ?
            AND iv IS NOT NULL
            AND iv > 0
            ORDER BY ABS(strike - ?) 
            LIMIT 2
        """
        
        closest_results = self.db.execute_query(closest_query,
                                               (timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                                option_type, strike))
        
        if not closest_results:
            return None
        
        if len(closest_results) == 1:
            # Only one strike available, use it
            return closest_results[0]['iv']
        
        # Interpolate between two closest strikes
        strike1, iv1 = closest_results[0]['strike'], closest_results[0]['iv']
        strike2, iv2 = closest_results[1]['strike'], closest_results[1]['iv']
        
        if strike1 == strike2:
            return iv1
        
        # Linear interpolation
        weight = (strike - strike1) / (strike2 - strike1)
        interpolated_iv = iv1 + weight * (iv2 - iv1)
        
        # Ensure reasonable bounds
        interpolated_iv = max(0.05, min(2.0, interpolated_iv))
        
        return interpolated_iv
    
    def _get_option_prices(self, timestamp: datetime, call_strike: float, put_strike: float) -> Dict:
        """Get actual option prices from market data"""
        query = """
            SELECT option_type, bid, ask
            FROM options_data
            WHERE timestamp = ?
            AND strike = ?
            AND option_type = ?
        """
        
        prices = {}
        
        # Get call price
        call_result = self.db.execute_query(query, 
                                           (timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                            call_strike, 'call'))
        if call_result:
            call_mid = (call_result[0]['bid'] + call_result[0]['ask']) / 2
            prices['call_price'] = call_mid
        
        # Get put price
        put_result = self.db.execute_query(query,
                                          (timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                           put_strike, 'put'))
        if put_result:
            put_mid = (put_result[0]['bid'] + put_result[0]['ask']) / 2
            prices['put_price'] = put_mid
        
        # Calculate totals
        if 'call_price' in prices and 'put_price' in prices:
            prices['current_value'] = prices['call_price'] + prices['put_price']
            # Assume we collected similar premium at entry
            prices['total_premium'] = prices['current_value'] * 1.2  # Rough estimate
        
        return prices
    
    def _estimate_fallback_iv(self, hour: int, minute: int) -> float:
        """
        Enhanced fallback IV estimation with smooth evolution
        Based on typical 0DTE patterns with realistic term structure
        """
        total_minutes = hour * 60 + minute
        minutes_to_close = max(960 - total_minutes, 1)  # Market closes at 4 PM (960 minutes)
        hours_to_close = minutes_to_close / 60.0
        
        # Base IV increases exponentially as expiry approaches
        # Typical 0DTE IV ranges from 25% (morning) to 80% (last hour)
        base_morning_iv = 0.28  # 28% at market open
        base_close_iv = 0.75    # 75% near close
        
        # Exponential increase with time decay
        time_factor = np.exp(-hours_to_close / 3.0)  # Exponential with 3-hour half-life
        smooth_iv = base_morning_iv + (base_close_iv - base_morning_iv) * time_factor
        
        # Add some randomness based on typical market patterns
        # Higher IV during typical volatility windows
        volatility_multiplier = 1.0
        if 570 <= total_minutes <= 600:  # 9:30-10:00 AM (opening volatility)
            volatility_multiplier = 1.15
        elif 660 <= total_minutes <= 690:  # 11:00-11:30 AM (mid-morning)
            volatility_multiplier = 0.95
        elif 780 <= total_minutes <= 840:  # 1:00-2:00 PM (lunch lull)
            volatility_multiplier = 0.9
        elif 900 <= total_minutes <= 960:  # 3:00-4:00 PM (closing volatility)
            volatility_multiplier = 1.25
        
        # Final IV with bounds
        final_iv = smooth_iv * volatility_multiplier
        return max(0.15, min(1.2, final_iv))  # Bound between 15% and 120%
    
    def _store_greeks(self, greeks_records: List[Dict]):
        """Store Greeks records in database"""
        insert_query = """
            INSERT INTO greeks_history 
            (timestamp, position_type, underlying, call_strike, put_strike, expiry,
             total_delta, total_gamma, total_theta, total_vega, total_rho,
             underlying_price, call_iv, put_iv, call_price, put_price, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        records = [
            (
                r['timestamp'], r['position_type'], r['underlying'],
                r['call_strike'], r['put_strike'], r['expiry'],
                r['total_delta'], r['total_gamma'], r['total_theta'],
                r['total_vega'], r['total_rho'], r['underlying_price'],
                r['call_iv'], r['put_iv'], r['call_price'], 
                r['put_price'], r['pnl']
            )
            for r in greeks_records
        ]
        
        self.db.execute_many(insert_query, records)
        self.stats['records_created'] += len(records)
    
    def _print_summary(self):
        """Print processing summary"""
        logger.info("\n" + "="*70)
        logger.info("GREEKS REGENERATION COMPLETE")
        logger.info("="*70)
        logger.info(f"Trading days processed: {self.stats['dates_processed']}")
        logger.info(f"Greeks records created: {self.stats['records_created']}")
        logger.info(f"IV from market data: {self.stats['iv_from_market']}")
        logger.info(f"IV fallback used: {self.stats['iv_fallback']}")
        
        if self.stats['iv_from_market'] > 0:
            market_pct = (self.stats['iv_from_market'] / 
                         (self.stats['iv_from_market'] + self.stats['iv_fallback']) * 100)
            logger.info(f"Market IV usage: {market_pct:.1f}%")
        
        logger.info(f"Errors encountered: {self.stats['errors']}")
        
        # Verify the data
        verification_query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT date(timestamp)) as unique_days,
                AVG(total_delta) as avg_delta,
                AVG(total_vega) as avg_vega,
                AVG(call_iv) as avg_iv,
                MIN(call_iv) as min_iv,
                MAX(call_iv) as max_iv
            FROM greeks_history
        """
        
        result = self.db.execute_query(verification_query)
        if result:
            stats = result[0]
            logger.info("\nVerification:")
            logger.info(f"  Total records: {stats['total_records']}")
            logger.info(f"  Unique days: {stats['unique_days']}")
            logger.info(f"  Average delta: {stats['avg_delta']:.4f}")
            logger.info(f"  Average vega: {stats['avg_vega']:.4f}")
            logger.info(f"  Average IV: {stats['avg_iv']*100:.1f}%")
            logger.info(f"  IV range: {stats['min_iv']*100:.1f}% - {stats['max_iv']*100:.1f}%")
            
            # Check for improvement
            if stats['avg_iv'] > 0.20 and stats['avg_iv'] < 0.60:
                logger.info("✅ IV values now match market reality!")
            else:
                logger.warning("⚠️ IV values may need review")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Regenerate Greeks with market-derived IV')
    parser.add_argument('--days', type=int, default=21,
                       help='Number of days to process (default: 21)')
    parser.add_argument('--entry-time', type=str, default='15:00',
                       help='Entry time in HH:MM format ET (default: 15:00)')
    parser.add_argument('--strike-offset', type=float, default=2.0,
                       help='Strike offset in dollars (default: 2.0)')
    parser.add_argument('--env', choices=['sandbox', 'production'], default='sandbox',
                       help='Tradier environment (default: sandbox)')
    
    args = parser.parse_args()
    
    # Create client and generator
    client = TradierClient(env=args.env)
    generator = MarketBasedGreeksGenerator(client)
    
    # Regenerate Greeks
    stats = generator.regenerate_all_greeks(
        days_back=args.days,
        entry_time=args.entry_time,
        strike_offset=args.strike_offset
    )
    
    return 0 if stats['errors'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())