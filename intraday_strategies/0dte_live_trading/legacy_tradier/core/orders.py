"""
Order management for Tradier
"""

from typing import Dict, List, Optional
from datetime import datetime

class OrderManager:
    """Manage orders and positions"""
    
    def __init__(self, client):
        """
        Initialize with Tradier client
        
        Args:
            client: TradierClient instance
        """
        self.client = client
    
    def place_strangle(self, call_symbol: str, put_symbol: str, 
                      quantity: int = 1) -> Optional[Dict]:
        """
        Place a strangle order (sell call and put)
        
        Args:
            call_symbol: Call option symbol
            put_symbol: Put option symbol
            quantity: Number of contracts (default 1)
            
        Returns:
            Order response or None
        """
        # Build multi-leg order
        legs = [
            {
                'symbol': call_symbol,
                'side': 'sell_to_open',
                'quantity': quantity
            },
            {
                'symbol': put_symbol,
                'side': 'sell_to_open',
                'quantity': quantity
            }
        ]
        
        print(f"\n📝 Placing strangle order:")
        print(f"   SELL {quantity} {call_symbol}")
        print(f"   SELL {quantity} {put_symbol}")
        
        result = self.client.place_multileg_order(legs)
        
        if result and 'order' in result:
            order = result['order']
            print(f"\n✅ Order placed successfully!")
            print(f"   Order ID: {order.get('id')}")
            print(f"   Status: {order.get('status')}")
            return result
        else:
            print(f"\n❌ Order failed")
            return None
    
    def close_strangle(self, call_symbol: str, put_symbol: str, 
                      quantity: int = 1) -> Optional[Dict]:
        """
        Close a strangle position (buy back call and put)
        
        Args:
            call_symbol: Call option symbol
            put_symbol: Put option symbol
            quantity: Number of contracts
            
        Returns:
            Order response or None
        """
        # Build multi-leg order to close
        legs = [
            {
                'symbol': call_symbol,
                'side': 'buy_to_close',
                'quantity': quantity
            },
            {
                'symbol': put_symbol,
                'side': 'buy_to_close',
                'quantity': quantity
            }
        ]
        
        print(f"\n📝 Closing strangle position:")
        print(f"   BUY {quantity} {call_symbol}")
        print(f"   BUY {quantity} {put_symbol}")
        
        result = self.client.place_multileg_order(legs)
        
        if result and 'order' in result:
            order = result['order']
            print(f"\n✅ Close order placed!")
            print(f"   Order ID: {order.get('id')}")
            print(f"   Status: {order.get('status')}")
            return result
        else:
            print(f"\n❌ Close order failed")
            return None
    
    def get_open_orders(self) -> List[Dict]:
        """Get list of open orders"""
        response = self.client.get_orders()
        
        if response and 'orders' in response:
            # Handle case where orders might be 'null' string
            if response['orders'] == 'null' or response['orders'] is None:
                return []
            
            orders = response['orders'].get('order', [])
            if not isinstance(orders, list):
                orders = [orders]
            
            # Filter for open orders
            open_orders = [o for o in orders if o.get('status') in ['pending', 'open', 'partially_filled']]
            return open_orders
        
        return []
    
    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders
        
        Returns:
            Number of orders cancelled
        """
        open_orders = self.get_open_orders()
        cancelled = 0
        
        for order in open_orders:
            order_id = order.get('id')
            if order_id:
                result = self.client.cancel_order(order_id)
                if result:
                    cancelled += 1
                    print(f"✅ Cancelled order {order_id}")
        
        return cancelled
    
    def get_strangle_positions(self) -> Optional[Dict]:
        """
        Get current strangle positions
        
        Returns:
            Dictionary with call and put positions
        """
        response = self.client.get_positions()
        
        if not response or 'positions' not in response:
            return None
        
        positions = response['positions'].get('position', [])
        if not isinstance(positions, list):
            positions = [positions]
        
        # Find options positions
        strangle = {'calls': [], 'puts': []}
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            
            # Parse option symbol (e.g., SPY240807C00635000)
            if len(symbol) > 10 and (symbol[-9] == 'C' or symbol[-9] == 'P'):
                option_type = 'calls' if symbol[-9] == 'C' else 'puts'
                strangle[option_type].append({
                    'symbol': symbol,
                    'quantity': pos.get('quantity', 0),
                    'cost_basis': pos.get('cost_basis', 0),
                    'current_value': pos.get('market_value', 0),
                    'unrealized_pl': float(pos.get('market_value', 0)) - float(pos.get('cost_basis', 0))
                })
        
        return strangle if (strangle['calls'] or strangle['puts']) else None