#!/usr/bin/env python3
"""
Generate Live Greeks from Real Options Data
Fetches actual options chains and calculates Greeks for positions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from core import TradierClient
from core.greeks_calculator import GreeksCalculator
from database import get_db_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveGreeksGenerator:
    """Generate Greeks from live options data"""
    
    def __init__(self, client: TradierClient = None):
        """Initialize the Greeks generator
        
        Args:
            client: Tradier API client
        """
        self.client = client or TradierClient(env="sandbox")
        self.db = get_db_manager()
        self.greeks_calc = GreeksCalculator()
        
    def get_active_positions(self) -> List[Dict]:
        """Get active options positions from account
        
        Returns:
            List of position dictionaries
        """
        try:
            positions = self.client.get_positions()
            
            if not positions:
                logger.info("No active positions found")
                return []
            
            options_positions = []
            for pos in positions:
                # Filter for options positions
                if pos.get('symbol', '').startswith('SPY') and len(pos['symbol']) > 3:
                    options_positions.append(pos)
            
            return options_positions
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_atm_strikes(self, spot_price: float, expiry: str) -> Tuple[float, float]:
        """Get ATM strike prices for strangle
        
        Args:
            spot_price: Current SPY price
            expiry: Expiration date (YYYY-MM-DD)
            
        Returns:
            Tuple of (call_strike, put_strike)
        """
        # Round to nearest dollar for SPY
        atm_strike = round(spot_price)
        
        # For strangle, go slightly OTM
        call_strike = atm_strike + 2  # $2 OTM call
        put_strike = atm_strike - 2   # $2 OTM put
        
        return call_strike, put_strike
    
    def fetch_option_quotes(self, strikes: List[float], expiry: str) -> Dict:
        """Fetch real-time quotes for options
        
        Args:
            strikes: List of strike prices
            expiry: Expiration date (YYYY-MM-DD)
            
        Returns:
            Dictionary of option quotes by symbol
        """
        quotes = {}
        
        for strike in strikes:
            for option_type in ['C', 'P']:
                # Build option symbol (e.g., SPY250807C00636000)
                symbol = self._build_option_symbol('SPY', expiry, strike, option_type)
                
                try:
                    quotes = self.client.get_quotes([symbol])
                    quote = quotes.get(symbol) if quotes else None
                    if quote:
                        quotes[symbol] = quote
                except Exception as e:
                    logger.warning(f"Could not fetch quote for {symbol}: {e}")
        
        return quotes
    
    def _build_option_symbol(self, underlying: str, expiry: str, strike: float, option_type: str) -> str:
        """Build standardized option symbol
        
        Args:
            underlying: Underlying symbol (e.g., 'SPY')
            expiry: Expiration date (YYYY-MM-DD)
            option_type: 'C' for call, 'P' for put
            
        Returns:
            Option symbol (e.g., SPY250807C00636000)
        """
        # Parse expiry date
        exp_date = datetime.fromisoformat(expiry)
        exp_str = exp_date.strftime('%y%m%d')
        
        # Format strike (multiply by 1000 for standard format)
        strike_str = f"{int(strike * 1000):08d}"
        
        return f"{underlying}{exp_str}{option_type}{strike_str}"
    
    def calculate_live_greeks(self, spot_price: float, option_quotes: Dict, expiry: str) -> Dict:
        """Calculate Greeks from live option quotes
        
        Args:
            spot_price: Current underlying price
            option_quotes: Dictionary of option quotes
            expiry: Expiration date
            
        Returns:
            Dictionary of calculated Greeks
        """
        greeks_data = {}
        expiry_dt = datetime.fromisoformat(expiry).replace(hour=16, minute=0)
        tte = max((expiry_dt - datetime.now()).total_seconds() / (365 * 24 * 3600), 1e-6)
        
        for symbol, quote in option_quotes.items():
            # Parse symbol to get strike and type
            if 'SPY' not in symbol:
                continue
            
            # Extract components
            option_type = 'call' if 'C' in symbol[9:10] else 'put'
            strike = float(symbol[10:]) / 1000
            
            # Get IV from quote or calculate from prices
            iv = quote.get('greeks', {}).get('smv_vol', 0.15)
            if iv == 0:
                # Estimate IV from bid-ask spread
                mid_price = (quote.get('bid', 0) + quote.get('ask', 0)) / 2
                if mid_price > 0:
                    iv = self._estimate_iv(spot_price, strike, tte, mid_price, option_type)
                else:
                    iv = 0.15  # Default IV
            
            # Calculate Greeks
            greeks = self.greeks_calc.calculate_greeks(
                spot=spot_price,
                strike=strike,
                time_to_expiry=tte,
                volatility=iv,
                option_type=option_type
            )
            
            # Add market data
            greeks['bid'] = quote.get('bid', 0)
            greeks['ask'] = quote.get('ask', 0)
            greeks['last'] = quote.get('last', 0)
            greeks['volume'] = quote.get('volume', 0)
            greeks['open_interest'] = quote.get('open_interest', 0)
            greeks['iv'] = iv
            
            greeks_data[symbol] = greeks
        
        return greeks_data
    
    def _estimate_iv(self, spot: float, strike: float, tte: float, 
                     option_price: float, option_type: str) -> float:
        """Estimate implied volatility from option price
        
        Simple approximation - in production, use proper IV solver
        """
        # Basic ATM approximation
        if abs(spot - strike) < spot * 0.01:  # Near ATM
            # Rough approximation: IV ≈ option_price / (spot * sqrt(tte) * 0.4)
            import math
            if tte > 0:
                iv = option_price / (spot * math.sqrt(tte) * 0.4)
                return min(max(iv, 0.05), 1.0)  # Bound between 5% and 100%
        
        return 0.15  # Default 15% IV
    
    def generate_and_store_greeks(self, use_positions: bool = True) -> Dict:
        """Generate Greeks and store in database
        
        Args:
            use_positions: If True, use actual positions; if False, use ATM strangle
            
        Returns:
            Summary of Greeks generated
        """
        logger.info("Generating live Greeks data...")
        
        # Get current SPY price
        spy_quotes = self.client.get_quotes(['SPY'])
        if not spy_quotes or 'quotes' not in spy_quotes:
            logger.error("Could not fetch SPY quote")
            return {}
        
        # Extract quote from nested structure
        if 'quote' in spy_quotes['quotes']:
            spy_quote = spy_quotes['quotes']['quote']
        else:
            logger.error("Invalid quote structure")
            return {}
            
        spot_price = spy_quote.get('last', 630)
        
        # Get today's expiry (0DTE)
        today = datetime.now()
        expiry = today.strftime('%Y-%m-%d')
        
        results = {
            'timestamp': datetime.now(),
            'spot_price': spot_price,
            'positions': [],
            'total_greeks': {
                'delta': 0,
                'gamma': 0,
                'theta': 0,
                'vega': 0,
                'rho': 0
            }
        }
        
        if use_positions:
            # Use actual positions
            positions = self.get_active_positions()
            
            if positions:
                for pos in positions:
                    symbol = pos['symbol']
                    quantity = pos.get('quantity', 0)
                    
                    # Get quote for this position
                    quotes = self.client.get_quotes([symbol])
                    quote = quotes.get(symbol) if quotes else None
                    if quote:
                        quotes = {symbol: quote}
                        greeks = self.calculate_live_greeks(spot_price, quotes, expiry)
                        
                        if symbol in greeks:
                            pos_greeks = greeks[symbol]
                            # Scale by position size
                            for greek in ['delta', 'gamma', 'theta', 'vega', 'rho']:
                                results['total_greeks'][greek] += pos_greeks.get(greek, 0) * quantity
                            
                            results['positions'].append({
                                'symbol': symbol,
                                'quantity': quantity,
                                'greeks': pos_greeks
                            })
            else:
                logger.info("No positions found, using simulated ATM strangle")
                use_positions = False
        
        if not use_positions:
            # Use simulated ATM strangle
            call_strike, put_strike = self.get_atm_strikes(spot_price, expiry)
            
            # Fetch quotes for these strikes
            quotes = self.fetch_option_quotes([call_strike, put_strike], expiry)
            
            if quotes:
                greeks = self.calculate_live_greeks(spot_price, quotes, expiry)
                
                # Sum up strangle Greeks
                for symbol, pos_greeks in greeks.items():
                    for greek in ['delta', 'gamma', 'theta', 'vega', 'rho']:
                        results['total_greeks'][greek] += pos_greeks.get(greek, 0)
                    
                    option_type = 'call' if 'C' in symbol else 'put'
                    strike = call_strike if option_type == 'call' else put_strike
                    
                    results['positions'].append({
                        'symbol': symbol,
                        'quantity': 1,
                        'strike': strike,
                        'type': option_type,
                        'greeks': pos_greeks
                    })
        
        # Store in database
        self._store_greeks(results, expiry)
        
        # Also save to JSON for dashboard
        self._save_to_json(results)
        
        logger.info(f"Generated Greeks for {len(results['positions'])} positions")
        logger.info(f"Total Greeks - Delta: {results['total_greeks']['delta']:.4f}, "
                   f"Gamma: {results['total_greeks']['gamma']:.4f}, "
                   f"Theta: {results['total_greeks']['theta']:.4f}, "
                   f"Vega: {results['total_greeks']['vega']:.4f}")
        
        return results
    
    def _store_greeks(self, results: Dict, expiry: str):
        """Store Greeks in database
        
        Args:
            results: Greeks calculation results
            expiry: Expiration date
        """
        # Determine position type
        if len(results['positions']) == 2:
            has_call = any('C' in p.get('symbol', '') or p.get('type') == 'call' 
                          for p in results['positions'])
            has_put = any('P' in p.get('symbol', '') or p.get('type') == 'put' 
                         for p in results['positions'])
            if has_call and has_put:
                position_type = 'strangle'
            else:
                position_type = 'spread'
        elif len(results['positions']) == 1:
            position_type = results['positions'][0].get('type', 'unknown')
        else:
            position_type = 'complex'
        
        # Extract strikes
        call_strike = None
        put_strike = None
        call_iv = None
        put_iv = None
        call_price = None
        put_price = None
        
        for pos in results['positions']:
            if 'call' in str(pos.get('type', '')).lower() or 'C' in pos.get('symbol', ''):
                call_strike = pos.get('strike') or self._extract_strike(pos.get('symbol', ''))
                call_iv = pos.get('greeks', {}).get('iv', 0.15)
                call_price = pos.get('greeks', {}).get('last', 0)
            elif 'put' in str(pos.get('type', '')).lower() or 'P' in pos.get('symbol', ''):
                put_strike = pos.get('strike') or self._extract_strike(pos.get('symbol', ''))
                put_iv = pos.get('greeks', {}).get('iv', 0.15)
                put_price = pos.get('greeks', {}).get('last', 0)
        
        # Insert into database
        query = """
            INSERT OR REPLACE INTO greeks_history 
            (timestamp, position_type, underlying, call_strike, put_strike, expiry,
             total_delta, total_gamma, total_theta, total_vega, total_rho,
             underlying_price, call_iv, put_iv, call_price, put_price, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            results['timestamp'],
            position_type,
            'SPY',
            call_strike,
            put_strike,
            expiry,
            results['total_greeks']['delta'],
            results['total_greeks']['gamma'],
            results['total_greeks']['theta'],
            results['total_greeks']['vega'],
            results['total_greeks'].get('rho', 0),
            results['spot_price'],
            call_iv,
            put_iv,
            call_price,
            put_price,
            0  # PnL would be calculated from entry prices
        )
        
        self.db.execute_query(query, values)
    
    def _extract_strike(self, symbol: str) -> Optional[float]:
        """Extract strike price from option symbol
        
        Args:
            symbol: Option symbol (e.g., SPY250807C00636000)
            
        Returns:
            Strike price or None
        """
        try:
            if len(symbol) > 10:
                strike_str = symbol[10:]
                return float(strike_str) / 1000
        except:
            pass
        return None
    
    def _save_to_json(self, results: Dict):
        """Save Greeks to JSON file for dashboard
        
        Args:
            results: Greeks calculation results
        """
        json_path = os.path.join(os.path.dirname(__file__), '..', 'tradier_risk_metrics.json')
        
        # Load existing data
        existing_data = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    existing_data = json.load(f)
            except:
                existing_data = {}
        
        # Initialize history if not exists
        if 'history' not in existing_data:
            existing_data['history'] = []
        
        # Add new entry
        entry = {
            'timestamp': results['timestamp'].isoformat(),
            'spot_price': results['spot_price'],
            'greeks': results['total_greeks'],
            'positions': len(results['positions'])
        }
        
        existing_data['history'].append(entry)
        
        # Keep only last 1000 entries
        existing_data['history'] = existing_data['history'][-1000:]
        
        # Save updated data
        with open(json_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
    
    def run_continuous(self, interval_seconds: int = 60):
        """Run continuous Greeks generation
        
        Args:
            interval_seconds: Update interval in seconds
        """
        import time
        
        logger.info(f"Starting continuous Greeks generation (interval: {interval_seconds}s)")
        
        while True:
            try:
                # Check if market is open
                now = datetime.now()
                if now.hour >= 9 and now.hour < 16:
                    if now.hour == 9 and now.minute < 30:
                        logger.info("Waiting for market open...")
                    else:
                        results = self.generate_and_store_greeks(use_positions=True)
                        logger.info(f"Updated Greeks at {now.strftime('%H:%M:%S')}")
                else:
                    logger.info(f"Market closed at {now.strftime('%H:%M:%S')}")
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Stopping Greeks generator...")
                break
            except Exception as e:
                logger.error(f"Error in continuous generation: {e}")
                time.sleep(interval_seconds)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate live Greeks from options data')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous updates')
    parser.add_argument('--interval', type=int, default=60,
                       help='Update interval in seconds (default: 60)')
    parser.add_argument('--use-positions', action='store_true',
                       help='Use actual positions instead of simulated')
    parser.add_argument('--env', choices=['sandbox', 'production'], default='sandbox',
                       help='Tradier environment (default: sandbox)')
    
    args = parser.parse_args()
    
    # Create client and generator
    client = TradierClient(env=args.env)
    generator = LiveGreeksGenerator(client)
    
    if args.continuous:
        generator.run_continuous(interval_seconds=args.interval)
    else:
        results = generator.generate_and_store_greeks(use_positions=args.use_positions)
        
        print("\n" + "="*60)
        print("GREEKS GENERATION COMPLETE")
        print("="*60)
        print(f"Spot Price: ${results['spot_price']:.2f}")
        print(f"Positions: {len(results['positions'])}")
        print(f"\nTotal Greeks:")
        for greek, value in results['total_greeks'].items():
            print(f"  {greek.capitalize()}: {value:.4f}")


if __name__ == "__main__":
    main()