#!/usr/bin/env python3
"""
Regenerate Accurate Greeks Based on Entry Time
This script calculates Greeks correctly based on actual entry time and strikes
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AccurateGreeksGenerator:
    """Generate accurate Greeks based on entry time strikes"""
    
    def __init__(self, client: TradierClient = None):
        """Initialize the Greeks generator"""
        self.client = client or TradierClient(env="sandbox")
        self.db = get_db_manager()
        self.greeks_calc = GreeksCalculator()
        
        # Market operates in Eastern Time
        self.ET = pytz.timezone('US/Eastern')
        
        # Statistics
        self.stats = {
            'dates_processed': 0,
            'records_created': 0,
            'errors': 0
        }
    
    def regenerate_all_greeks(self, days_back: int = 21, 
                            entry_time: str = "15:00",
                            strike_offset: float = 2.0) -> Dict:
        """
        Regenerate all Greeks data with correct entry-time-based calculations
        
        Args:
            days_back: Number of days to process
            entry_time: Entry time in HH:MM format (ET)
            strike_offset: Dollar offset for strikes from entry price
            
        Returns:
            Statistics dictionary
        """
        logger.info("="*70)
        logger.info(f"REGENERATING GREEKS WITH ENTRY TIME: {entry_time} ET")
        logger.info(f"Strike Offset: ${strike_offset}")
        logger.info("="*70)
        
        # Clear existing Greeks data
        self._clear_existing_greeks()
        
        # Get list of trading days
        trading_days = self._get_trading_days(days_back)
        
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
        logger.info("Clearing existing Greeks data...")
        
        # First, check how many records exist
        count_query = "SELECT COUNT(*) as count FROM greeks_history"
        result = self.db.execute_query(count_query)
        existing_count = result[0]['count'] if result else 0
        
        if existing_count > 0:
            logger.info(f"Removing {existing_count} existing Greeks records...")
            delete_query = "DELETE FROM greeks_history"
            self.db.execute_query(delete_query)
            logger.info("Existing Greeks data cleared")
        else:
            logger.info("No existing Greeks data to clear")
    
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
        Process a single trading day with accurate Greeks
        
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
        
        logger.info(f"  Entry price: ${entry_price:.2f}")
        logger.info(f"  Call strike: ${call_strike}, Put strike: ${put_strike}")
        
        # Get all prices from entry to close
        prices_query = """
            SELECT timestamp, close, high, low
            FROM spy_prices
            WHERE date(timestamp) = ?
            AND time(timestamp) >= ?
            AND time(timestamp) <= '16:00:00'
            AND session_type = 'regular'
            ORDER BY timestamp
        """
        
        prices = self.db.execute_query(prices_query, (trading_date, entry_time))
        
        if not prices:
            logger.warning(f"No price data from {entry_time} to close for {trading_date}")
            return
        
        # Market closes at 4 PM ET
        expiry_et = self.ET.localize(datetime.combine(date_obj, dt_time(16, 0)))
        
        # Generate Greeks for each minute from entry to close
        greeks_records = []
        
        for price_point in prices:
            timestamp = datetime.fromisoformat(price_point['timestamp'])
            timestamp_et = self.ET.localize(timestamp)
            spot = price_point['close']
            
            # Calculate time to expiry in years
            seconds_to_expiry = max((expiry_et - timestamp_et).total_seconds(), 60)  # Min 1 minute
            time_to_expiry = seconds_to_expiry / (365 * 24 * 3600)
            
            # Estimate IV based on time of day and market conditions
            iv = self._estimate_iv(timestamp.hour, timestamp.minute, 
                                  price_point['high'], price_point['low'])
            
            # Calculate Greeks for call
            call_greeks = self.greeks_calc.calculate_greeks(
                spot=spot,
                strike=call_strike,
                time_to_expiry=time_to_expiry,
                volatility=iv,
                option_type='call'
            )
            
            # Calculate Greeks for put
            put_greeks = self.greeks_calc.calculate_greeks(
                spot=spot,
                strike=put_strike,
                time_to_expiry=time_to_expiry,
                volatility=iv,
                option_type='put'
            )
            
            # Combine for short strangle (negative quantities)
            total_delta = -(call_greeks['delta'] + put_greeks['delta'])
            total_gamma = -(call_greeks['gamma'] + put_greeks['gamma'])
            total_theta = -(call_greeks['theta'] + put_greeks['theta'])  # Positive for short
            total_vega = -(call_greeks['vega'] + put_greeks['vega'])
            total_rho = -(call_greeks.get('rho', 0) + put_greeks.get('rho', 0))
            
            # Estimate P&L (simplified - would need actual premiums)
            initial_premium = 1.0  # Placeholder
            current_value = call_greeks.get('price', 0) + put_greeks.get('price', 0)
            pnl = initial_premium - current_value
            
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
                'call_iv': iv,
                'put_iv': iv,
                'call_price': call_greeks.get('price', 0),
                'put_price': put_greeks.get('price', 0),
                'pnl': pnl,
                'time_to_expiry_hours': seconds_to_expiry / 3600
            })
        
        # Store Greeks in database
        if greeks_records:
            self._store_greeks(greeks_records)
            logger.info(f"  Generated {len(greeks_records)} Greeks records")
            
            # Show sample Greeks evolution
            if len(greeks_records) >= 3:
                logger.info("  Greeks evolution:")
                logger.info(f"    Entry: Delta={greeks_records[0]['total_delta']:.3f}, "
                          f"Vega={greeks_records[0]['total_vega']:.3f}")
                mid_idx = len(greeks_records) // 2
                logger.info(f"    Mid:   Delta={greeks_records[mid_idx]['total_delta']:.3f}, "
                          f"Vega={greeks_records[mid_idx]['total_vega']:.3f}")
                logger.info(f"    Close: Delta={greeks_records[-1]['total_delta']:.3f}, "
                          f"Vega={greeks_records[-1]['total_vega']:.3f}")
    
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
    
    def _estimate_iv(self, hour: int, minute: int, high: float, low: float) -> float:
        """
        Estimate MARKET-CALIBRATED implied volatility for 0DTE options
        Based on empirical observations from successful backtests
        
        Args:
            hour: Hour of day
            minute: Minute of hour
            high: High price in period
            low: Low price in period
            
        Returns:
            Market-calibrated IV for 0DTE
        """
        # CORRECTED: Base IV for 0DTE SPY options (NOT annual IV)
        # Real 0DTE options trade at 25-35% IV
        base_iv = 0.28  # 28% - realistic for 0DTE
        
        # Adjust based on time of day
        total_minutes = hour * 60 + minute
        
        # 0DTE IV actually INCREASES near expiry due to gamma risk
        if total_minutes < 600:  # Before 10 AM
            time_mult = 1.0  # Normal IV early
        elif total_minutes < 720:  # 10 AM - 12 PM
            time_mult = 1.05  # Slight increase
        elif total_minutes < 840:  # 12 PM - 2 PM
            time_mult = 1.1  # Increasing as expiry approaches
        elif total_minutes < 900:  # 2 PM - 3:00 PM
            time_mult = 1.2  # Higher near entry time
        elif total_minutes < 930:  # 3:00 PM - 3:30 PM
            time_mult = 1.3  # Peak IV in final hour
        else:  # After 3:30 PM
            time_mult = 1.4  # Maximum IV in final 30 min
        
        # Adjust based on intraday range (volatility of volatility)
        price_range = (high - low) / ((high + low) / 2)
        if price_range > 0.01:  # More than 1% intraday range
            range_mult = 1.3  # Much higher IV on volatile days
        elif price_range > 0.005:  # 0.5-1% range
            range_mult = 1.15
        elif price_range > 0.003:  # 0.3-0.5% range
            range_mult = 1.05
        else:
            range_mult = 1.0  # Normal day
        
        # Calculate final IV
        final_iv = base_iv * time_mult * range_mult
        
        # Cap at reasonable limits for 0DTE
        return min(max(final_iv, 0.20), 0.50)  # Between 20% and 50%
    
    def _store_greeks(self, greeks_records: List[Dict]):
        """Store Greeks records in database"""
        # First, ensure we have the entry_time and entry_price columns
        # They might not exist in the original schema
        
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
        logger.info(f"Errors encountered: {self.stats['errors']}")
        
        # Verify the data
        verification_query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT date(timestamp)) as unique_days,
                AVG(total_delta) as avg_delta,
                AVG(total_vega) as avg_vega,
                MIN(total_delta) as min_delta,
                MAX(total_delta) as max_delta
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
            logger.info(f"  Delta range: [{stats['min_delta']:.4f}, {stats['max_delta']:.4f}]")
            
            # Check for flatline issue
            if abs(stats['min_delta']) > 0.9 or abs(stats['max_delta']) > 0.9:
                logger.warning("⚠️ Warning: Greeks may still have extreme values!")
            else:
                logger.info("✅ Greeks values look reasonable!")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Regenerate accurate Greeks data')
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
    generator = AccurateGreeksGenerator(client)
    
    # Regenerate Greeks
    stats = generator.regenerate_all_greeks(
        days_back=args.days,
        entry_time=args.entry_time,
        strike_offset=args.strike_offset
    )
    
    return 0 if stats['errors'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())