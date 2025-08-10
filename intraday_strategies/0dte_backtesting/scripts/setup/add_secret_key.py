#!/usr/bin/env python3
"""
Quick script to add Alpaca secret key and test connection
"""

import os
import getpass
from pathlib import Path

def add_secret_key():
    print("="*60)
    print("🔐 ALPACA SECRET KEY SETUP")
    print("="*60)
    
    print("\nYour API Key is already configured:")
    print("  FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F")
    
    print("\nNow I need your SECRET KEY from Alpaca dashboard")
    print("\nTo get it:")
    print("1. Go to: https://app.alpaca.markets/paper/dashboard/overview")
    print("2. Find your API key in the dashboard")
    print("3. Click 'View' or 'Regenerate' to see the secret key")
    print("4. Copy the entire secret key")
    
    print("\n" + "-"*40)
    secret_key = getpass.getpass("Paste your Alpaca SECRET KEY here: ").strip()
    
    if not secret_key:
        print("\n❌ No secret key entered!")
        return False
    
    if len(secret_key) < 20:
        print("\n❌ Secret key seems too short. Please check it.")
        return False
    
    # Update .env file
    env_content = f"""# Alpaca API Configuration
# IMPORTANT: Regenerate your API key after this since it was exposed!

# Paper Trading
ALPACA_PAPER_API_KEY=FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F
ALPACA_PAPER_SECRET_KEY={secret_key}
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets

# Live Trading (be careful!)
ALPACA_LIVE_API_KEY=
ALPACA_LIVE_SECRET_KEY=
ALPACA_LIVE_BASE_URL=https://api.alpaca.markets

# Data endpoints
ALPACA_DATA_URL=https://data.alpaca.markets
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✅ Secret key saved to .env file")
    print("\nNow testing connection...")
    
    # Test the connection
    os.system("python test_alpaca_connection.py")
    
    return True

if __name__ == "__main__":
    try:
        if add_secret_key():
            print("\n" + "="*60)
            print("✅ Setup complete!")
            print("="*60)
            print("\nNext steps:")
            print("1. Your credentials are saved and tested")
            print("2. Run the vega strategy: python alpaca_vega_trader.py --paper")
            print("3. Monitor trades: streamlit run live_monitor.py")
            print("\n⚠️  SECURITY: Consider regenerating your API key since it was shared in chat")
    except KeyboardInterrupt:
        print("\n\nSetup cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")