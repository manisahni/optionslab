"""
Alpaca API Client for Live Trading
Handles authentication, data, and trading operations
"""

import os
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import pandas as pd

class AlpacaClient:
    """Alpaca API client for options and stock trading"""
    
    def __init__(self, paper: bool = True):
        """
        Initialize Alpaca client
        
        Args:
            paper: Use paper trading (True) or live trading (False)
        """
        # Load environment variables
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
        
        self.paper = paper
        
        # API credentials
        self.api_key = os.getenv('ALPACA_API_KEY', 'PKMLDQM62IIIP4975X71')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY', '84Y8OoZTm34Cp3achHAVgNnbviYSmjCoCTxGft40')
        
        # Set base URLs
        if paper:
            self.base_url = "https://paper-api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
            self.options_url = "https://data.alpaca.markets/v1beta1"
        else:
            self.base_url = "https://api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
            self.options_url = "https://data.alpaca.markets/v1beta1"
        
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
            'accept': 'application/json'
        }
        
        self.account = None
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify API connection and get account info"""
        try:
            response = requests.get(f"{self.base_url}/v2/account", headers=self.headers)
            if response.status_code == 200:
                self.account = response.json()
                print(f"✅ Connected to Alpaca ({'Paper' if self.paper else 'Live'} mode)")
                print(f"   Account: {self.account.get('account_number', 'N/A')}")
                print(f"   Buying Power: ${float(self.account.get('buying_power', 0)):,.2f}")
            else:
                print(f"⚠️ Failed to connect: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
    
    def get_account(self) -> Dict:
        """Get account information"""
        response = requests.get(f"{self.base_url}/v2/account", headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return {}
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        response = requests.get(f"{self.base_url}/v2/positions", headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []
    
    def get_orders(self, status: str = "open") -> List[Dict]:
        """Get orders by status"""
        params = {"status": status}
        response = requests.get(f"{self.base_url}/v2/orders", headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    
    def get_stock_quote(self, symbol: str) -> Dict:
        """Get latest stock quote"""
        url = f"{self.data_url}/v2/stocks/{symbol}/quotes/latest"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if 'quote' in data:
                return data['quote']
        return {}
    
    def get_stock_bars(self, symbol: str, timeframe: str = "1Min", 
                      start: Optional[str] = None, end: Optional[str] = None,
                      limit: int = 1000) -> pd.DataFrame:
        """Get historical stock bars"""
        if not start:
            start = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S-05:00')
        if not end:
            end = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-05:00')
        
        params = {
            'symbols': symbol,
            'timeframe': timeframe,
            'start': start,
            'end': end,
            'limit': limit,
            'feed': 'sip'
        }
        
        url = f"{self.data_url}/v2/stocks/bars"
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if 'bars' in data and symbol in data['bars']:
                bars = data['bars'][symbol]
                df = pd.DataFrame(bars)
                if not df.empty:
                    df['t'] = pd.to_datetime(df['t'])
                    df.set_index('t', inplace=True)
                    df.columns = ['open', 'high', 'low', 'close', 'volume', 'trades', 'vwap']
                return df
        return pd.DataFrame()
    
    def get_option_contracts(self, underlying: str, expiration: Optional[str] = None,
                           strike_gte: Optional[float] = None, 
                           strike_lte: Optional[float] = None) -> List[Dict]:
        """Get option contracts for a symbol"""
        params = {
            'underlying_symbols': underlying,
            'status': 'active',
            'limit': 100
        }
        
        if expiration:
            params['expiration_date'] = expiration
        if strike_gte:
            params['strike_price_gte'] = str(strike_gte)
        if strike_lte:
            params['strike_price_lte'] = str(strike_lte)
        
        url = f"{self.base_url}/v2/options/contracts"
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('option_contracts', [])
        return []
    
    def get_option_quote(self, symbol: str) -> Dict:
        """Get latest option quote"""
        url = f"{self.options_url}/options/quotes/latest"
        params = {'symbols': symbol}
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if 'quotes' in data and symbol in data['quotes']:
                return data['quotes'][symbol]
        return {}
    
    def get_option_bars(self, symbol: str, timeframe: str = "1Min",
                       start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
        """Get historical option bars"""
        if not start:
            start = datetime.now().strftime('%Y-%m-%dT09:30:00Z')
        if not end:
            end = datetime.now().strftime('%Y-%m-%dT16:00:00Z')
        
        params = {
            'symbols': symbol,
            'timeframe': timeframe,
            'start': start,
            'end': end,
            'limit': 1000
        }
        
        url = f"{self.options_url}/options/bars"
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if 'bars' in data and symbol in data['bars']:
                bars = data['bars'][symbol]
                df = pd.DataFrame(bars)
                if not df.empty:
                    df['t'] = pd.to_datetime(df['t'])
                    df.set_index('t', inplace=True)
                    df.columns = ['open', 'high', 'low', 'close', 'volume', 'trades', 'vwap']
                return df
        return pd.DataFrame()
    
    def place_stock_order(self, symbol: str, qty: int, side: str, 
                         order_type: str = "market", 
                         time_in_force: str = "day",
                         limit_price: Optional[float] = None,
                         stop_price: Optional[float] = None) -> Dict:
        """Place a stock order"""
        order = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force
        }
        
        if limit_price:
            order["limit_price"] = str(limit_price)
        if stop_price:
            order["stop_price"] = str(stop_price)
        
        response = requests.post(f"{self.base_url}/v2/orders", 
                                headers=self.headers, json=order)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            return {"error": f"{response.status_code}: {response.text}"}
    
    def place_option_order(self, legs: List[Dict], qty: int = 1,
                          order_type: str = "market",
                          time_in_force: str = "day") -> Dict:
        """
        Place an option order (single or multi-leg)
        
        Args:
            legs: List of leg dictionaries with 'symbol', 'side', 'ratio_qty'
            qty: Base quantity
            order_type: Order type (market, limit)
            time_in_force: Time in force (day, gtc)
        """
        # Determine order class
        order_class = "simple" if len(legs) == 1 else "mleg"
        
        order = {
            "class": order_class,
            "type": order_type,
            "time_in_force": time_in_force,
            "qty": str(qty)
        }
        
        if order_class == "simple":
            # Single leg order
            order["symbol"] = legs[0]["symbol"]
            order["side"] = legs[0]["side"]
        else:
            # Multi-leg order
            order["legs"] = legs
        
        response = requests.post(f"{self.base_url}/v2/orders", 
                                headers=self.headers, json=order)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            return {"error": f"{response.status_code}: {response.text}"}
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        response = requests.delete(f"{self.base_url}/v2/orders/{order_id}", 
                                  headers=self.headers)
        return response.status_code == 204
    
    def close_position(self, symbol: str) -> Dict:
        """Close a position"""
        response = requests.delete(f"{self.base_url}/v2/positions/{symbol}", 
                                  headers=self.headers)
        if response.status_code in [200, 204]:
            return {"success": True}
        else:
            return {"error": f"{response.status_code}: {response.text}"}
    
    def close_all_positions(self) -> Dict:
        """Close all positions"""
        response = requests.delete(f"{self.base_url}/v2/positions", 
                                  headers=self.headers)
        if response.status_code in [200, 204, 207]:
            return {"success": True}
        else:
            return {"error": f"{response.status_code}: {response.text}"}
    
    def get_market_hours(self, date: Optional[str] = None) -> Dict:
        """Get market hours for a date"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/v2/clock"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        return {}
    
    def is_market_open(self) -> bool:
        """Check if market is open"""
        clock = self.get_market_hours()
        return clock.get('is_open', False)
    
    def find_0dte_strangle(self, symbol: str = "SPY", 
                          width: float = 3.0) -> Tuple[Optional[str], Optional[str]]:
        """
        Find appropriate 0DTE strangle strikes
        
        Args:
            symbol: Underlying symbol
            width: Strike width from current price
            
        Returns:
            Tuple of (call_symbol, put_symbol)
        """
        # Get current price
        quote = self.get_stock_quote(symbol)
        if not quote:
            return None, None
        
        current_price = (quote.get('ap', 0) + quote.get('bp', 0)) / 2
        
        # Calculate strikes
        call_strike = round(current_price + width)
        put_strike = round(current_price - width)
        
        # Get today's date for 0DTE
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get contracts
        contracts = self.get_option_contracts(
            symbol, 
            expiration=today,
            strike_gte=put_strike - 1,
            strike_lte=call_strike + 1
        )
        
        call_symbol = None
        put_symbol = None
        
        for contract in contracts:
            if contract['strike_price'] == str(call_strike) and contract['type'] == 'call':
                call_symbol = contract['symbol']
            elif contract['strike_price'] == str(put_strike) and contract['type'] == 'put':
                put_symbol = contract['symbol']
        
        return call_symbol, put_symbol