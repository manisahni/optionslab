#!/usr/bin/env python3
"""
Secure Alpaca Configuration and Connection Test
Uses environment variables for API credentials
"""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
import yaml

# Load environment variables
load_dotenv()


class AlpacaConfig:
    """Secure configuration manager for Alpaca"""
    
    def __init__(self, paper=True):
        """Initialize configuration from environment variables"""
        self.paper = paper
        
        if paper:
            self.api_key = os.getenv('ALPACA_PAPER_API_KEY', '')
            self.secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY', '')
            self.base_url = os.getenv('ALPACA_PAPER_BASE_URL', 'https://paper-api.alpaca.markets')
        else:
            self.api_key = os.getenv('ALPACA_LIVE_API_KEY', '')
            self.secret_key = os.getenv('ALPACA_LIVE_SECRET_KEY', '')
            self.base_url = os.getenv('ALPACA_LIVE_BASE_URL', 'https://api.alpaca.markets')
        
        self.data_url = os.getenv('ALPACA_DATA_URL', 'https://data.alpaca.markets')
        
        # Validate
        if not self.api_key:
            raise ValueError(f"{'Paper' if paper else 'Live'} API key not found in environment variables")
    
    def get_trading_client(self):
        """Get Alpaca trading client"""
        return TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper
        )
    
    def get_data_client(self):
        """Get Alpaca data client"""
        return StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
    
    def update_yaml_config(self):
        """Update YAML config with secure references"""
        config = {
            'alpaca': {
                'paper': {
                    'api_key': '${ALPACA_PAPER_API_KEY}',
                    'secret_key': '${ALPACA_PAPER_SECRET_KEY}',
                    'base_url': self.base_url,
                    'data_url': self.data_url
                },
                'live': {
                    'api_key': '${ALPACA_LIVE_API_KEY}',
                    'secret_key': '${ALPACA_LIVE_SECRET_KEY}',
                    'base_url': 'https://api.alpaca.markets',
                    'data_url': self.data_url
                }
            }
        }
        
        # Load existing config and update only Alpaca section
        try:
            with open('alpaca_config.yaml', 'r') as f:
                full_config = yaml.safe_load(f)
            full_config['alpaca'] = config['alpaca']
        except:
            full_config = config
        
        with open('alpaca_config.yaml', 'w') as f:
            yaml.dump(full_config, f, default_flow_style=False)
        
        print("✅ Updated alpaca_config.yaml to use environment variables")


def test_connection():
    """Test Alpaca connection and capabilities"""
    print("\n" + "="*50)
    print("ALPACA CONNECTION TEST")
    print("="*50)
    
    try:
        # Initialize config
        config = AlpacaConfig(paper=True)
        print(f"✅ Configuration loaded")
        print(f"   Mode: PAPER")
        print(f"   Endpoint: {config.base_url}")
        
        # Test trading client
        print("\n📊 Testing Trading Client...")
        trading_client = config.get_trading_client()
        
        # Get account info
        account = trading_client.get_account()
        print(f"✅ Account connected")
        print(f"   Account ID: {account.account_number}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Pattern Day Trader: {account.pattern_day_trader}")
        
        # Check if options trading is enabled
        print(f"\n📈 Options Trading Status:")
        print(f"   Options Approved: {account.options_approved_level if hasattr(account, 'options_approved_level') else 'Unknown'}")
        print(f"   Options Trading Level: {account.options_trading_level if hasattr(account, 'options_trading_level') else 'Unknown'}")
        
        # Test data client
        print("\n📊 Testing Data Client...")
        data_client = config.get_data_client()
        
        # Get SPY quote
        request = StockLatestQuoteRequest(symbol_or_symbols="SPY")
        quote = data_client.get_stock_latest_quote(request)
        
        spy_bid = quote["SPY"].bid_price
        spy_ask = quote["SPY"].ask_price
        spy_mid = (spy_bid + spy_ask) / 2
        
        print(f"✅ Market data working")
        print(f"   SPY Bid: ${spy_bid:.2f}")
        print(f"   SPY Ask: ${spy_ask:.2f}")
        print(f"   SPY Mid: ${spy_mid:.2f}")
        
        # Check for options data capability
        print("\n🔍 Checking Options Data...")
        try:
            # Alpaca options are still in development
            # This is how you would check when available
            assets_request = GetAssetsRequest(asset_class=AssetClass.US_OPTION)
            options = trading_client.get_all_assets(assets_request)
            if options:
                print(f"✅ Options data available: {len(options)} option contracts found")
            else:
                print("⚠️  No options data found (may need subscription)")
        except Exception as e:
            print(f"⚠️  Options API not available: {str(e)}")
            print("   Note: Alpaca options trading may require additional setup")
        
        # Market status
        clock = trading_client.get_clock()
        print(f"\n⏰ Market Status:")
        print(f"   Market Open: {clock.is_open}")
        print(f"   Next Open: {clock.next_open}")
        print(f"   Next Close: {clock.next_close}")
        
        print("\n" + "="*50)
        print("✅ CONNECTION TEST SUCCESSFUL!")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API key in .env file")
        print("2. Ensure you have the secret key (not provided yet)")
        print("3. Verify paper trading is enabled in your account")
        print("4. Check network connectivity")
        
        return False


def check_environment():
    """Check environment setup"""
    print("\n🔍 Checking Environment Variables...")
    
    env_vars = [
        'ALPACA_PAPER_API_KEY',
        'ALPACA_PAPER_SECRET_KEY',
        'ALPACA_PAPER_BASE_URL'
    ]
    
    all_set = True
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var:
                # Mask the key for security
                masked = value[:10] + '...' if len(value) > 10 else value
                print(f"   {var}: {masked}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: ❌ NOT SET")
            all_set = False
    
    if not all_set:
        print("\n⚠️  Some environment variables are missing!")
        print("   Please check your .env file")
    
    return all_set


if __name__ == "__main__":
    import sys
    
    print("🔐 Alpaca Secure Configuration Manager")
    
    # Check environment
    if check_environment():
        
        # Update YAML to use env vars
        try:
            config = AlpacaConfig(paper=True)
            config.update_yaml_config()
        except Exception as e:
            print(f"⚠️  Could not update config: {e}")
        
        # Test connection
        if test_connection():
            print("\n✅ Your Alpaca setup is ready!")
            print("\n⚠️  IMPORTANT REMINDER:")
            print("   Since your API key was exposed in chat,")
            print("   you should regenerate it in your Alpaca dashboard")
            print("   for security best practices.")
        else:
            print("\n❌ Connection test failed")
            print("   You need to add your SECRET KEY to the .env file")
            print("   Get it from: https://app.alpaca.markets/paper/dashboard/overview")
    else:
        print("\n❌ Environment not properly configured")
        print("   Please update your .env file with API credentials")