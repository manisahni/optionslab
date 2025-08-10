#!/usr/bin/env python3
"""
Calculate Market-Derived Implied Volatility from Bid/Ask Prices
This ensures dashboard Greeks match backtest methodology
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from scipy.stats import norm
import pytz

from database import get_db_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketIVCalculator:
    """Calculate implied volatility from market bid/ask prices"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize IV calculator
        
        Args:
            risk_free_rate: Annual risk-free rate (default 5%)
        """
        self.r = risk_free_rate
        self.db = get_db_manager()
        self.ET = pytz.timezone('US/Eastern')
        
    def calculate_iv_from_price(self,
                               spot: float,
                               strike: float,
                               time_to_expiry: float,
                               option_price: float,
                               option_type: str,
                               initial_guess: float = 0.25) -> Optional[float]:
        """
        Calculate implied volatility using Newton-Raphson method
        
        Args:
            spot: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            option_price: Market price of option (mid of bid/ask)
            option_type: 'call' or 'put'
            initial_guess: Starting IV guess
            
        Returns:
            Implied volatility or None if cannot converge
        """
        # Handle edge cases
        if time_to_expiry <= 0:
            return None
        
        if option_price <= 0:
            return None
            
        # Check for intrinsic value violations
        if option_type.lower() == 'call':
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)
            
        if option_price < intrinsic:
            logger.warning(f"Option price ${option_price:.2f} below intrinsic ${intrinsic:.2f}")
            return None
        
        # Newton-Raphson iteration
        max_iterations = 100
        precision = 1e-5
        vol = initial_guess
        
        for i in range(max_iterations):
            # Calculate theoretical price and vega
            bs_price = self._black_scholes_price(spot, strike, time_to_expiry, vol, option_type)
            vega = self._calculate_vega(spot, strike, time_to_expiry, vol)
            
            # Check convergence
            price_diff = bs_price - option_price
            if abs(price_diff) < precision:
                return vol
            
            # Vega adjustment
            if abs(vega) < 1e-10:
                # Vega too small, try different initial guess
                vol = initial_guess * (1 + 0.5 * (i % 4))
                continue
                
            # Newton-Raphson update
            vol = vol - price_diff / (vega * 100)  # vega per 100% move
            
            # Keep vol in reasonable range for 0DTE
            vol = max(0.05, min(2.0, vol))  # 5% to 200%
        
        logger.warning(f"IV calculation failed to converge for strike {strike}")
        return None
    
    def _black_scholes_price(self, spot: float, strike: float, time_to_expiry: float,
                            volatility: float, option_type: str) -> float:
        """Calculate Black-Scholes theoretical price"""
        if time_to_expiry <= 0:
            if option_type.lower() == 'call':
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        # Calculate d1 and d2
        d1 = (np.log(spot / strike) + (self.r + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)
        
        if option_type.lower() == 'call':
            return spot * norm.cdf(d1) - strike * np.exp(-self.r * time_to_expiry) * norm.cdf(d2)
        else:
            return strike * np.exp(-self.r * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)
    
    def _calculate_vega(self, spot: float, strike: float, time_to_expiry: float, volatility: float) -> float:
        """Calculate vega (sensitivity to volatility)"""
        if time_to_expiry <= 0:
            return 0
            
        d1 = (np.log(spot / strike) + (self.r + 0.5 * volatility**2) * time_to_expiry) / (volatility * np.sqrt(time_to_expiry))
        return spot * norm.pdf(d1) * np.sqrt(time_to_expiry) / 100  # Per 1% vol move
    
    def update_options_iv(self, date: Optional[str] = None) -> Dict:
        """
        Update IV for all options in database
        
        Args:
            date: Optional date filter (YYYY-MM-DD format)
            
        Returns:
            Statistics dictionary
        """
        logger.info("="*70)
        logger.info("CALCULATING MARKET IMPLIED VOLATILITY FROM BID/ASK")
        logger.info("="*70)
        
        # Query options data
        if date:
            query = """
                SELECT DISTINCT
                    o.timestamp,
                    o.strike,
                    o.option_type,
                    o.bid,
                    o.ask,
                    o.expiry,
                    s.close as spot_price
                FROM options_data o
                JOIN spy_prices s ON datetime(o.timestamp) = datetime(s.timestamp)
                WHERE date(o.timestamp) = ?
                ORDER BY o.timestamp, o.strike
            """
            params = (date,)
        else:
            query = """
                SELECT DISTINCT
                    o.timestamp,
                    o.strike,
                    o.option_type,
                    o.bid,
                    o.ask,
                    o.expiry,
                    s.close as spot_price
                FROM options_data o
                JOIN spy_prices s ON datetime(o.timestamp) = datetime(s.timestamp)
                ORDER BY o.timestamp, o.strike
            """
            params = ()
        
        results = self.db.execute_query(query, params)
        
        # Convert to DataFrame with explicit column names
        if results:
            # Convert sqlite3.Row objects to dictionaries
            data = [dict(row) for row in results]
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()
        
        if df.empty:
            logger.warning("No options data found")
            return {'status': 'error', 'message': 'No data found'}
        
        logger.info(f"Processing {len(df)} option records...")
        
        # Calculate IV for each option
        calculated_ivs = []
        stats = {
            'total': len(df),
            'successful': 0,
            'failed': 0,
            'avg_iv': 0,
            'min_iv': float('inf'),
            'max_iv': 0
        }
        
        for idx, row in df.iterrows():
            # Calculate mid price
            mid_price = (row['bid'] + row['ask']) / 2
            
            # Skip if spread is too wide or prices are invalid
            if row['ask'] <= 0 or row['bid'] <= 0:
                stats['failed'] += 1
                continue
                
            spread_pct = (row['ask'] - row['bid']) / mid_price if mid_price > 0 else float('inf')
            if spread_pct > 0.5:  # Skip if spread > 50%
                logger.debug(f"Skipping strike {row['strike']} - spread too wide ({spread_pct:.1%})")
                stats['failed'] += 1
                continue
            
            # Calculate time to expiry
            timestamp = pd.to_datetime(row['timestamp'])
            expiry = pd.to_datetime(row['expiry'])
            
            # 0DTE expires at 4 PM ET
            expiry_time = self.ET.localize(datetime.combine(expiry.date(), datetime.strptime("16:00", "%H:%M").time()))
            current_time = self.ET.localize(timestamp.replace(tzinfo=None))
            
            seconds_to_expiry = max((expiry_time - current_time).total_seconds(), 60)  # Min 1 minute
            years_to_expiry = seconds_to_expiry / (365.25 * 24 * 3600)
            
            # Calculate IV
            iv = self.calculate_iv_from_price(
                spot=row['spot_price'],
                strike=row['strike'],
                time_to_expiry=years_to_expiry,
                option_price=mid_price,
                option_type=row['option_type']
            )
            
            if iv is not None:
                calculated_ivs.append({
                    'timestamp': row['timestamp'],
                    'strike': row['strike'],
                    'option_type': row['option_type'],
                    'market_iv': iv,
                    'bid': row['bid'],
                    'ask': row['ask'],
                    'mid': mid_price,
                    'spot': row['spot_price']
                })
                
                stats['successful'] += 1
                stats['min_iv'] = min(stats['min_iv'], iv)
                stats['max_iv'] = max(stats['max_iv'], iv)
            else:
                stats['failed'] += 1
        
        if calculated_ivs:
            # Calculate average IV
            stats['avg_iv'] = np.mean([x['market_iv'] for x in calculated_ivs])
            
            # Update database with calculated IVs
            update_query = """
                UPDATE options_data
                SET iv = ?
                WHERE timestamp = ? AND strike = ? AND option_type = ?
            """
            
            updates = [
                (iv['market_iv'], iv['timestamp'], iv['strike'], iv['option_type'])
                for iv in calculated_ivs
            ]
            
            self.db.execute_many(update_query, updates)
            logger.info(f"Updated {len(updates)} records with market-derived IV")
            
            # Show sample results
            iv_df = pd.DataFrame(calculated_ivs)
            
            logger.info("\nSample Market IVs (First 5):")
            logger.info("-"*60)
            for _, row in iv_df.head().iterrows():
                moneyness = (row['strike'] - row['spot']) / row['spot'] * 100
                logger.info(f"Strike ${row['strike']:.0f} ({moneyness:+.1f}% OTM): "
                          f"IV = {row['market_iv']*100:.1f}%, "
                          f"Mid = ${row['mid']:.2f}")
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("SUMMARY")
        logger.info("="*70)
        logger.info(f"Total records: {stats['total']}")
        logger.info(f"Successfully calculated: {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)")
        logger.info(f"Failed: {stats['failed']}")
        if stats['successful'] > 0:
            logger.info(f"Average IV: {stats['avg_iv']*100:.1f}%")
            logger.info(f"IV Range: {stats['min_iv']*100:.1f}% - {stats['max_iv']*100:.1f}%")
        
        return stats
    
    def calculate_volatility_smile(self, timestamp: str) -> pd.DataFrame:
        """
        Calculate volatility smile for a specific timestamp
        
        Args:
            timestamp: Timestamp to analyze
            
        Returns:
            DataFrame with strike, IV, and moneyness
        """
        query = """
            SELECT 
                o.strike,
                o.option_type,
                o.bid,
                o.ask,
                o.iv,
                s.close as spot
            FROM options_data o
            JOIN spy_prices s ON datetime(o.timestamp) = datetime(s.timestamp)
            WHERE o.timestamp = ?
            ORDER BY o.strike
        """
        
        df = pd.DataFrame(self.db.execute_query(query, (timestamp,)))
        
        if not df.empty:
            df['moneyness'] = (df['strike'] - df['spot']) / df['spot'] * 100
            df['mid_price'] = (df['bid'] + df['ask']) / 2
        
        return df


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate market IV from bid/ask prices')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Process all available data')
    
    args = parser.parse_args()
    
    calculator = MarketIVCalculator()
    
    if args.all:
        stats = calculator.update_options_iv()
    else:
        # Use today if no date specified
        date = args.date or datetime.now().strftime('%Y-%m-%d')
        stats = calculator.update_options_iv(date)
    
    # Show volatility smile for latest timestamp
    if stats.get('successful', 0) > 0:
        query = "SELECT MAX(timestamp) as latest FROM options_data WHERE iv IS NOT NULL"
        result = calculator.db.execute_query(query)
        if result:
            latest_time = result[0]['latest']
            smile_df = calculator.calculate_volatility_smile(latest_time)
            
            if not smile_df.empty:
                logger.info("\nVolatility Smile at " + latest_time + ":")
                logger.info("-"*60)
                for option_type in ['call', 'put']:
                    type_df = smile_df[smile_df['option_type'] == option_type]
                    if not type_df.empty:
                        logger.info(f"\n{option_type.upper()}S:")
                        for _, row in type_df.iterrows():
                            logger.info(f"  Strike ${row['strike']:.0f} ({row['moneyness']:+.1f}%): "
                                      f"IV = {row['iv']*100:.1f}%")
    
    return 0 if stats.get('successful', 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())