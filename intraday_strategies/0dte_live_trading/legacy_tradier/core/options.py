"""
Options-specific functionality for Tradier
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import math

class OptionsManager:
    """Manage options-specific operations"""
    
    def __init__(self, client):
        """
        Initialize with Tradier client
        
        Args:
            client: TradierClient instance
        """
        self.client = client
    
    def get_0dte_options(self, symbol: str = "SPY") -> Optional[Dict]:
        """
        Get today's expiring options
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            0DTE option chain
        """
        today = date.today().strftime('%Y-%m-%d')
        return self.client.get_option_chains(symbol, today)
    
    def find_strangle_strikes(self, symbol: str = "SPY", 
                            target_delta: float = 0.15,
                            dte: int = 0) -> Optional[Tuple[Dict, Dict]]:
        """
        Find suitable strikes for a strangle
        
        Args:
            symbol: Underlying symbol
            target_delta: Target delta for strikes (0.15-0.20 typical)
            dte: Days to expiration (0 for today)
            
        Returns:
            Tuple of (call_option, put_option) or None
        """
        # Get expiration date
        if dte == 0:
            exp_date = date.today().strftime('%Y-%m-%d')
        else:
            from datetime import timedelta
            exp_date = (date.today() + timedelta(days=dte)).strftime('%Y-%m-%d')
        
        # Get option chain
        chain = self.client.get_option_chains(symbol, exp_date)
        if not chain or 'options' not in chain:
            print(f"No options found for {symbol} expiring {exp_date}")
            return None
        
        options = chain['options'].get('option', [])
        if not options:
            print(f"Empty option chain for {symbol}")
            return None
        
        # Get current price
        quote = self.client.get_quotes([symbol])
        if not quote or 'quotes' not in quote:
            print(f"Could not get quote for {symbol}")
            return None
        
        quote_data = quote['quotes'].get('quote', {})
        if isinstance(quote_data, list):
            quote_data = quote_data[0]
        
        spot_price = (quote_data.get('bid', 0) + quote_data.get('ask', 0)) / 2
        if spot_price == 0:
            spot_price = quote_data.get('last', 0)
        
        print(f"\n{symbol} Price: ${spot_price:.2f}")
        
        # Separate calls and puts
        calls = [opt for opt in options if opt['option_type'] == 'call']
        puts = [opt for opt in options if opt['option_type'] == 'put']
        
        # Find OTM options
        otm_calls = [c for c in calls if float(c['strike']) > spot_price]
        otm_puts = [p for p in puts if float(p['strike']) < spot_price]
        
        # Sort by distance from spot
        otm_calls.sort(key=lambda x: float(x['strike']))
        otm_puts.sort(key=lambda x: float(x['strike']), reverse=True)
        
        # Select strikes (typically 3-5 strikes OTM for 0DTE)
        selected_call = None
        selected_put = None
        
        # For 0DTE, use strike distance instead of Greeks
        target_distance = spot_price * 0.005  # 0.5% OTM
        
        # Find call strike
        for call in otm_calls[:10]:  # Check first 10 OTM strikes
            strike = float(call['strike'])
            distance = strike - spot_price
            if distance >= target_distance:
                selected_call = call
                break
        
        # Find put strike
        for put in otm_puts[:10]:  # Check first 10 OTM strikes
            strike = float(put['strike'])
            distance = spot_price - strike
            if distance >= target_distance:
                selected_put = put
                break
        
        if selected_call and selected_put:
            return (selected_call, selected_put)
        else:
            print("Could not find suitable strikes")
            return None
    
    def get_strangle_quotes(self, call_symbol: str, put_symbol: str) -> Optional[Dict]:
        """
        Get quotes for strangle legs
        
        Args:
            call_symbol: Call option symbol
            put_symbol: Put option symbol
            
        Returns:
            Dictionary with quotes for both legs
        """
        quotes = self.client.get_quotes([call_symbol, put_symbol])
        
        if not quotes or 'quotes' not in quotes:
            return None
        
        quote_data = quotes['quotes'].get('quote', [])
        if not isinstance(quote_data, list):
            quote_data = [quote_data]
        
        result = {}
        for quote in quote_data:
            symbol = quote.get('symbol')
            if symbol == call_symbol:
                result['call'] = {
                    'symbol': symbol,
                    'bid': quote.get('bid', 0),
                    'ask': quote.get('ask', 0),
                    'mid': (quote.get('bid', 0) + quote.get('ask', 0)) / 2,
                    'volume': quote.get('volume', 0),
                    'open_interest': quote.get('open_interest', 0)
                }
            elif symbol == put_symbol:
                result['put'] = {
                    'symbol': symbol,
                    'bid': quote.get('bid', 0),
                    'ask': quote.get('ask', 0),
                    'mid': (quote.get('bid', 0) + quote.get('ask', 0)) / 2,
                    'volume': quote.get('volume', 0),
                    'open_interest': quote.get('open_interest', 0)
                }
        
        return result
    
    def calculate_strangle_credit(self, call_quote: Dict, put_quote: Dict) -> float:
        """
        Calculate expected credit for strangle
        
        Args:
            call_quote: Call option quote
            put_quote: Put option quote
            
        Returns:
            Expected credit (using bid prices for selling)
        """
        call_bid = call_quote.get('bid', 0)
        put_bid = put_quote.get('bid', 0)
        
        return (call_bid + put_bid) * 100  # Convert to dollar amount