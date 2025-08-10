#!/usr/bin/env python3
"""
Interactive setup for Alpaca trading system
"""

import os
import sys
from datetime import datetime
from pathlib import Path

def setup_alpaca():
    """Interactive setup for Alpaca credentials"""
    
    print("="*60)
    print("🚀 ALPACA 0DTE TRADING SYSTEM SETUP")
    print("="*60)
    print("\nThis will help you set up your Alpaca credentials securely.\n")
    
    print("📋 You'll need from your Alpaca dashboard:")
    print("   1. API Key (you provided: FkGJZu...)")
    print("   2. Secret Key (still needed)")
    print("   3. Make sure you're using PAPER trading credentials\n")
    
    # Check if .env exists
    env_file = Path('.env')
    if env_file.exists():
        print("⚠️  .env file already exists")
        overwrite = input("Overwrite existing configuration? (y/n): ").lower()
        if overwrite != 'y':
            print("Setup cancelled")
            return
    
    print("\n" + "-"*40)
    print("ENTER YOUR ALPACA CREDENTIALS")
    print("-"*40)
    
    # API Key
    api_key = input("\n1. Enter your Alpaca API Key\n   (or press Enter to use: FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F)\n   > ").strip()
    if not api_key:
        api_key = "FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F"
    
    # Secret Key
    print("\n2. Enter your Alpaca Secret Key")
    print("   (You can find this in your Alpaca dashboard)")
    print("   (It's usually a long string like the API key)")
    secret_key = input("   > ").strip()
    
    if not secret_key:
        print("\n❌ Secret key is required!")
        print("   Please get it from: https://app.alpaca.markets/paper/dashboard/overview")
        return
    
    # Validate format
    if len(api_key) < 20:
        print("❌ API key seems too short. Please check it.")
        return
    
    if len(secret_key) < 20:
        print("❌ Secret key seems too short. Please check it.")
        return
    
    # Show what we'll save (masked)
    print("\n" + "-"*40)
    print("CONFIGURATION SUMMARY")
    print("-"*40)
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Secret: {secret_key[:10]}...{secret_key[-4:]}")
    print(f"Mode: Paper Trading")
    print(f"Endpoint: https://paper-api.alpaca.markets")
    
    # Confirm
    confirm = input("\n✅ Save this configuration? (y/n): ").lower()
    if confirm != 'y':
        print("Setup cancelled")
        return
    
    # Save to .env
    env_content = f"""# Alpaca API Configuration
# Generated: {datetime.now()}
# IMPORTANT: Keep this file secret!

# Paper Trading
ALPACA_PAPER_API_KEY={api_key}
ALPACA_PAPER_SECRET_KEY={secret_key}
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets

# Live Trading (not configured)
ALPACA_LIVE_API_KEY=
ALPACA_LIVE_SECRET_KEY=
ALPACA_LIVE_BASE_URL=https://api.alpaca.markets

# Data endpoints
ALPACA_DATA_URL=https://data.alpaca.markets
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✅ Configuration saved to .env file")
    
    # Test connection
    print("\n" + "-"*40)
    print("TESTING CONNECTION")
    print("-"*40)
    
    test = input("\nTest the connection now? (y/n): ").lower()
    if test == 'y':
        print("\nTesting connection...")
        os.system("python test_alpaca_connection.py")
    
    # Next steps
    print("\n" + "="*60)
    print("📋 NEXT STEPS")
    print("="*60)
    print("\n1. ✅ Configuration saved")
    print("2. 🧪 Test connection: python test_alpaca_connection.py")
    print("3. 📊 Start monitoring: streamlit run live_monitor.py")
    print("4. 🤖 Run paper trading: python alpaca_vega_trader.py --paper")
    print("\n⏰ Remember: Trade only between 3:00-3:30 PM ET for best results!")
    print("\n⚠️  IMPORTANT: Always paper trade for at least 1 week first!")

if __name__ == "__main__":
    try:
        setup_alpaca()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")