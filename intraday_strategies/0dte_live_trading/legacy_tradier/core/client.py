"""
Tradier API Client
Handles authentication and basic API calls
"""

import os
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from dotenv import load_dotenv

class TradierClient:
    """Tradier API client for options trading"""
    
    def __init__(self, env: str = "sandbox"):
        """
        Initialize Tradier client
        
        Args:
            env: 'sandbox' for paper trading or 'production' for live
        """
        # Load environment variables
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
        
        self.env = env
        
        if env == "sandbox":
            self.token = os.getenv('TRADIER_SANDBOX_TOKEN')
            self.base_url = "https://sandbox.tradier.com/v1"
        else:
            self.token = os.getenv('TRADIER_PROD_TOKEN')
            self.base_url = "https://api.tradier.com/v1"
        
        if not self.token:
            raise ValueError(f"No Tradier token found for {env} environment. Please set in .env file")
        
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json'
        }
        
        self.account_id = None
        self._get_account_id()
    
    def _get_account_id(self):
        """Get the first account ID"""
        try:
            response = self.get_profile()
            if response and 'profile' in response:
                accounts = response['profile'].get('account', [])
                if accounts:
                    if isinstance(accounts, list):
                        self.account_id = accounts[0]['account_number']
                    else:
                        self.account_id = accounts['account_number']
                    print(f"Using account: {self.account_id}")
        except Exception as e:
            print(f"Warning: Could not get account ID: {e}")
    
    def _request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """
        Make API request to Tradier
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: POST data
            
        Returns:
            Response data or None if error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, data=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            else:
                print(f"API Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    # Account Methods
    def get_profile(self) -> Optional[Dict]:
        """Get user profile"""
        return self._request("GET", "/user/profile")
    
    def get_balances(self) -> Optional[Dict]:
        """Get account balances"""
        if not self.account_id:
            print("No account ID available")
            return None
        return self._request("GET", f"/accounts/{self.account_id}/balances")
    
    def get_positions(self) -> Optional[Dict]:
        """Get current positions"""
        if not self.account_id:
            print("No account ID available")
            return None
        return self._request("GET", f"/accounts/{self.account_id}/positions")
    
    def get_orders(self) -> Optional[Dict]:
        """Get current orders"""
        if not self.account_id:
            print("No account ID available")
            return None
        return self._request("GET", f"/accounts/{self.account_id}/orders")
    
    # Market Data Methods
    def get_quotes(self, symbols: List[str]) -> Optional[Dict]:
        """
        Get quotes for symbols
        
        Args:
            symbols: List of symbols (stocks or options)
            
        Returns:
            Quote data
        """
        params = {'symbols': ','.join(symbols)}
        return self._request("GET", "/markets/quotes", params=params)
    
    def get_option_chains(self, symbol: str, expiration: str = None) -> Optional[Dict]:
        """
        Get option chain for a symbol
        
        Args:
            symbol: Underlying symbol (e.g., 'SPY')
            expiration: Optional expiration date (YYYY-MM-DD)
            
        Returns:
            Option chain data
        """
        params = {'symbol': symbol}
        if expiration:
            params['expiration'] = expiration
        
        return self._request("GET", "/markets/options/chains", params=params)
    
    def get_option_strikes(self, symbol: str, expiration: str) -> Optional[Dict]:
        """
        Get available strikes for an expiration
        
        Args:
            symbol: Underlying symbol
            expiration: Expiration date (YYYY-MM-DD)
            
        Returns:
            Strike prices
        """
        params = {
            'symbol': symbol,
            'expiration': expiration
        }
        return self._request("GET", "/markets/options/strikes", params=params)
    
    def get_option_expirations(self, symbol: str) -> Optional[Dict]:
        """
        Get available expiration dates
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            Expiration dates
        """
        params = {'symbol': symbol}
        return self._request("GET", "/markets/options/expirations", params=params)
    
    # Order Methods
    def place_order(self, order_data: Dict) -> Optional[Dict]:
        """
        Place an order
        
        Args:
            order_data: Order parameters
            
        Returns:
            Order response
        """
        if not self.account_id:
            print("No account ID available")
            return None
        
        return self._request("POST", f"/accounts/{self.account_id}/orders", data=order_data)
    
    def place_multileg_order(self, orders: List[Dict]) -> Optional[Dict]:
        """
        Place a multi-leg options order
        
        Args:
            orders: List of order legs
            
        Returns:
            Order response
        """
        if not self.account_id:
            print("No account ID available")
            return None
        
        # Build multileg order data with symbol parameter
        # First, we need the underlying symbol
        symbol = 'SPY'  # Default to SPY for options
        
        order_data = {
            'class': 'multileg',
            'symbol': symbol,  # Required for multileg orders
            'type': 'market',
            'duration': 'day'
        }
        
        # Add each leg
        for i, leg in enumerate(orders):
            order_data[f'option_symbol[{i}]'] = leg['symbol']
            order_data[f'side[{i}]'] = leg['side']
            order_data[f'quantity[{i}]'] = leg['quantity']
        
        return self._request("POST", f"/accounts/{self.account_id}/orders", data=order_data)
    
    def cancel_order(self, order_id: str) -> Optional[Dict]:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        if not self.account_id:
            print("No account ID available")
            return None
        
        return self._request("DELETE", f"/accounts/{self.account_id}/orders/{order_id}")
    
    # Market Status
    def get_market_status(self) -> Optional[Dict]:
        """Get market status (open/closed)"""
        return self._request("GET", "/markets/clock")
    
    def is_market_open(self) -> bool:
        """Check if market is open"""
        status = self.get_market_status()
        if status and 'clock' in status:
            state = status['clock'].get('state', '')
            return state == 'open'
        return False
    
    # Historical Data Methods
    def get_timesales(self, symbol: str, interval: str = "1min", 
                     start: Optional[str] = None, end: Optional[str] = None,
                     session_filter: str = "all") -> Optional[Dict]:
        """
        Get time and sales data for charting
        
        Args:
            symbol: Stock symbol (e.g., "SPY")
            interval: Time interval - "1min", "5min", "15min"
            start: Start datetime (YYYY-MM-DD HH:MM)
            end: End datetime (YYYY-MM-DD HH:MM)
            session_filter: "all" or "open"
            
        Returns:
            Time series data
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "session_filter": session_filter
        }
        
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        
        return self._request("GET", "/markets/timesales", params=params)
    
    def get_history(self, symbol: str, interval: str = "daily",
                   start: Optional[str] = None, end: Optional[str] = None) -> Optional[Dict]:
        """
        Get historical pricing data
        
        Args:
            symbol: Stock or option symbol
            interval: "daily", "weekly", or "monthly"
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            
        Returns:
            Historical price data
        """
        params = {
            "symbol": symbol,
            "interval": interval
        }
        
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        
        return self._request("GET", "/markets/history", params=params)