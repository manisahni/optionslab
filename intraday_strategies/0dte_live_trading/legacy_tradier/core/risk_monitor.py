"""
Risk Monitor for Tradier Strangle Positions
Real-time risk monitoring with Greeks tracking
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime
import json
import os
from .greeks_calculator import GreeksCalculator

class RiskMonitor:
    """Monitor and track risk metrics for strangle positions"""
    
    def __init__(self, client, vega_limit: float = 2.0, delta_limit: float = 0.20):
        """
        Initialize risk monitor
        
        Args:
            client: TradierClient instance
            vega_limit: Maximum acceptable vega exposure
            delta_limit: Maximum acceptable delta (absolute value)
        """
        self.client = client
        self.greeks_calc = GreeksCalculator()
        self.vega_limit = vega_limit
        self.delta_limit = delta_limit
        
        # Risk thresholds
        self.thresholds = {
            'max_loss_pct': 200,  # Max loss as % of credit
            'profit_target_pct': 50,  # Profit target as % of credit
            'strike_buffer': 0.50,  # Minimum distance from strike
            'vega_warning': 1.5,    # Vega warning level
            'time_stop_minutes': 1,  # Minutes before close to exit
        }
        
        # Track position history
        self.position_history = []
    
    def get_strangle_data(self) -> Optional[Dict]:
        """
        Get current strangle position data with prices
        
        Returns:
            Dictionary with position and market data
        """
        # Get positions
        positions = self.client.get_positions()
        if not positions or 'positions' not in positions:
            return None
        
        pos_list = positions['positions'].get('position', [])
        if not isinstance(pos_list, list):
            pos_list = [pos_list] if pos_list else []
        
        # Find strangle positions
        calls = []
        puts = []
        
        for pos in pos_list:
            symbol = pos.get('symbol', '')
            # Parse option type from symbol
            if 'C' in symbol and len(symbol) > 15:  # Call option
                calls.append(pos)
            elif 'P' in symbol and len(symbol) > 15:  # Put option
                puts.append(pos)
        
        if not calls and not puts:
            return None
        
        # Get current quotes for positions
        symbols = []
        if calls:
            symbols.append(calls[0]['symbol'])
        if puts:
            symbols.append(puts[0]['symbol'])
        
        # Get SPY quote
        symbols.append('SPY')
        
        quotes = self.client.get_quotes(symbols)
        if not quotes or 'quotes' not in quotes:
            return None
        
        quote_data = quotes['quotes'].get('quote', [])
        if not isinstance(quote_data, list):
            quote_data = [quote_data]
        
        # Parse quotes
        quote_map = {q['symbol']: q for q in quote_data}
        
        return {
            'calls': calls,
            'puts': puts,
            'quotes': quote_map,
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_risk_metrics(self) -> Optional[Dict]:
        """
        Calculate comprehensive risk metrics including Greeks
        
        Returns:
            Dictionary with all risk metrics
        """
        # Get position data
        data = self.get_strangle_data()
        if not data:
            return None
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'spy_price': 0,
            'positions': {},
            'greeks': {},
            'risk_levels': {},
            'warnings': []
        }
        
        # Get SPY price
        spy_quote = data['quotes'].get('SPY', {})
        spy_price = (spy_quote.get('bid', 0) + spy_quote.get('ask', 0)) / 2
        metrics['spy_price'] = spy_price
        
        # Process call position
        call_strike = 0
        call_iv = 0.30  # Default IV
        
        if data['calls']:
            call = data['calls'][0]
            call_symbol = call['symbol']
            
            # Parse strike from symbol
            call_strike = float(call_symbol[-8:-3])
            
            # Get call quote
            call_quote = data['quotes'].get(call_symbol, {})
            call_mid = (call_quote.get('bid', 0) + call_quote.get('ask', 0)) / 2
            
            # Calculate IV from price if possible
            if call_mid > 0:
                time_to_expiry = self.greeks_calc.calculate_time_to_expiry(
                    datetime.now().strftime('%Y-%m-%d')
                )
                
                try:
                    call_iv = self.greeks_calc.calculate_iv_from_price(
                        call_mid, spy_price, call_strike, time_to_expiry, 'call'
                    )
                except:
                    call_iv = 0.30  # Fallback
            
            metrics['positions']['call'] = {
                'symbol': call_symbol,
                'strike': call_strike,
                'quantity': float(call.get('quantity', 0)),
                'price': call_mid,
                'iv': call_iv,
                'distance': spy_price - call_strike
            }
        
        # Process put position
        put_strike = 0
        put_iv = 0.30  # Default IV
        
        if data['puts']:
            put = data['puts'][0]
            put_symbol = put['symbol']
            
            # Parse strike from symbol
            put_strike = float(put_symbol[-8:-3])
            
            # Get put quote
            put_quote = data['quotes'].get(put_symbol, {})
            put_mid = (put_quote.get('bid', 0) + put_quote.get('ask', 0)) / 2
            
            # Calculate IV from price if possible
            if put_mid > 0:
                time_to_expiry = self.greeks_calc.calculate_time_to_expiry(
                    datetime.now().strftime('%Y-%m-%d')
                )
                
                try:
                    put_iv = self.greeks_calc.calculate_iv_from_price(
                        put_mid, spy_price, put_strike, time_to_expiry, 'put'
                    )
                except:
                    put_iv = 0.30  # Fallback
            
            metrics['positions']['put'] = {
                'symbol': put_symbol,
                'strike': put_strike,
                'quantity': float(put.get('quantity', 0)),
                'price': put_mid,
                'iv': put_iv,
                'distance': spy_price - put_strike
            }
        
        # Calculate strangle Greeks
        if call_strike > 0 and put_strike > 0:
            time_to_expiry = self.greeks_calc.calculate_time_to_expiry(
                datetime.now().strftime('%Y-%m-%d')
            )
            
            greeks = self.greeks_calc.calculate_strangle_greeks(
                spy_price, call_strike, put_strike,
                time_to_expiry, call_iv, put_iv,
                metrics['positions'].get('call', {}).get('quantity', -1),
                metrics['positions'].get('put', {}).get('quantity', -1)
            )
            
            metrics['greeks'] = greeks
            
            # Calculate risk levels
            metrics['risk_levels'] = self.assess_risk_levels(metrics)
            
            # Generate warnings
            metrics['warnings'] = self.generate_warnings(metrics)
        
        # Store in history
        self.position_history.append(metrics)
        
        return metrics
    
    def assess_risk_levels(self, metrics: Dict) -> Dict[str, str]:
        """
        Assess risk levels based on current metrics
        
        Args:
            metrics: Current risk metrics
            
        Returns:
            Dictionary with risk level assessments
        """
        levels = {}
        
        # Vega risk
        total_vega = abs(metrics['greeks'].get('vega', 0))
        if total_vega < self.vega_limit * 0.5:
            levels['vega'] = 'LOW'
        elif total_vega < self.vega_limit * 0.75:
            levels['vega'] = 'MEDIUM'
        elif total_vega < self.vega_limit:
            levels['vega'] = 'HIGH'
        else:
            levels['vega'] = 'CRITICAL'
        
        # Delta risk
        total_delta = abs(metrics['greeks'].get('delta', 0))
        if total_delta < 0.05:
            levels['delta'] = 'NEUTRAL'
        elif total_delta < 0.10:
            levels['delta'] = 'LOW'
        elif total_delta < self.delta_limit:
            levels['delta'] = 'MEDIUM'
        else:
            levels['delta'] = 'HIGH'
        
        # Strike breach risk
        call_distance = abs(metrics['positions'].get('call', {}).get('distance', 999))
        put_distance = abs(metrics['positions'].get('put', {}).get('distance', 999))
        min_distance = min(call_distance, put_distance)
        
        if min_distance > 5:
            levels['strike'] = 'SAFE'
        elif min_distance > 2:
            levels['strike'] = 'WATCH'
        elif min_distance > self.thresholds['strike_buffer']:
            levels['strike'] = 'WARNING'
        else:
            levels['strike'] = 'DANGER'
        
        # Gamma risk (acceleration)
        gamma = abs(metrics['greeks'].get('gamma', 0))
        if gamma < 0.01:
            levels['gamma'] = 'LOW'
        elif gamma < 0.05:
            levels['gamma'] = 'MEDIUM'
        else:
            levels['gamma'] = 'HIGH'
        
        # Overall risk
        critical_count = sum(1 for v in levels.values() if v in ['CRITICAL', 'DANGER'])
        high_count = sum(1 for v in levels.values() if v == 'HIGH')
        
        if critical_count > 0:
            levels['overall'] = 'CRITICAL'
        elif high_count >= 2:
            levels['overall'] = 'HIGH'
        elif high_count == 1:
            levels['overall'] = 'MEDIUM'
        else:
            levels['overall'] = 'LOW'
        
        return levels
    
    def generate_warnings(self, metrics: Dict) -> List[str]:
        """
        Generate warning messages based on risk metrics
        
        Args:
            metrics: Current risk metrics
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check vega
        vega = abs(metrics['greeks'].get('vega', 0))
        if vega > self.vega_limit:
            warnings.append(f"🚨 VEGA LIMIT EXCEEDED: {vega:.2f} > {self.vega_limit}")
        elif vega > self.thresholds['vega_warning']:
            warnings.append(f"⚠️ High vega exposure: {vega:.2f}")
        
        # Check delta
        delta = metrics['greeks'].get('delta', 0)
        if abs(delta) > self.delta_limit:
            warnings.append(f"⚠️ Delta imbalance: {delta:+.3f}")
        
        # Check strike proximity
        call_distance = abs(metrics['positions'].get('call', {}).get('distance', 999))
        put_distance = abs(metrics['positions'].get('put', {}).get('distance', 999))
        
        if call_distance < self.thresholds['strike_buffer']:
            warnings.append(f"🚨 SPY near CALL strike: ${call_distance:.2f} away")
        elif call_distance < 1:
            warnings.append(f"⚠️ Approaching call strike: ${call_distance:.2f} away")
        
        if put_distance < self.thresholds['strike_buffer']:
            warnings.append(f"🚨 SPY near PUT strike: ${put_distance:.2f} away")
        elif put_distance < 1:
            warnings.append(f"⚠️ Approaching put strike: ${put_distance:.2f} away")
        
        # Check time to close
        now = datetime.now()
        close_time = now.replace(hour=15, minute=59, second=0)
        minutes_to_close = (close_time - now).total_seconds() / 60
        
        if minutes_to_close <= self.thresholds['time_stop_minutes']:
            warnings.append(f"🚨 CLOSING TIME: {minutes_to_close:.0f} minutes to exit")
        elif minutes_to_close <= 30:
            warnings.append(f"⏰ Time warning: {minutes_to_close:.0f} minutes remaining")
        
        # Check gamma
        gamma = abs(metrics['greeks'].get('gamma', 0))
        if gamma > 0.05:
            warnings.append(f"⚠️ High gamma risk: {gamma:.3f}")
        
        return warnings
    
    def export_metrics(self, filepath: str = 'risk_metrics.json'):
        """
        Export risk metrics history to file
        
        Args:
            filepath: Path to export file
        """
        with open(filepath, 'w') as f:
            json.dump({
                'thresholds': self.thresholds,
                'history': self.position_history,
                'last_update': datetime.now().isoformat()
            }, f, indent=2)
    
    def should_exit(self, metrics: Dict) -> Tuple[bool, str]:
        """
        Determine if position should be exited
        
        Args:
            metrics: Current risk metrics
            
        Returns:
            Tuple of (should_exit, reason)
        """
        # Critical risk level
        if metrics['risk_levels'].get('overall') == 'CRITICAL':
            return True, "Critical risk level reached"
        
        # Vega limit exceeded
        if abs(metrics['greeks'].get('vega', 0)) > self.vega_limit:
            return True, f"Vega limit exceeded: {metrics['greeks']['vega']:.2f}"
        
        # Strike breach
        min_distance = min(
            abs(metrics['positions'].get('call', {}).get('distance', 999)),
            abs(metrics['positions'].get('put', {}).get('distance', 999))
        )
        if min_distance < self.thresholds['strike_buffer']:
            return True, f"Strike breach imminent: {min_distance:.2f} points"
        
        # Time stop
        now = datetime.now()
        close_time = now.replace(hour=15, minute=59, second=0)
        if (close_time - now).total_seconds() <= self.thresholds['time_stop_minutes'] * 60:
            return True, "Closing time reached"
        
        return False, "Position OK"