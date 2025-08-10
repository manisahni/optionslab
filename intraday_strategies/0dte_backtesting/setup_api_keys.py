#!/usr/bin/env python3
"""
API Setup Wizard

Interactive script to help users set up their API keys securely.
"""

import sys
import os
from pathlib import Path
import getpass
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from configuration.api_manager import APIManager


def print_header():
    """Print welcome header"""
    print("\n🚀 0DTE Trading Application - API Setup Wizard")
    print("=" * 60)
    print("This wizard will help you set up your API keys securely.\n")


def get_openai_key() -> Optional[str]:
    """Prompt for OpenAI API key"""
    print("📌 OpenAI API Setup")
    print("-" * 40)
    print("OpenAI API is required for AI-powered trading analysis.\n")
    print("To get your API key:")
    print("1. Go to https://platform.openai.com/api-keys")
    print("2. Sign in or create an account")
    print("3. Click 'Create new secret key'")
    print("4. Copy the key (it won't be shown again!)\n")
    
    # Check if already configured
    current_key = os.getenv("OPENAI_API_KEY")
    if current_key:
        print(f"Current key: {current_key[:4]}...{current_key[-4:]}")
        update = input("Update this key? (y/N): ").lower().strip()
        if update != 'y':
            return None
    
    # Get new key
    while True:
        key = getpass.getpass("Enter your OpenAI API key (hidden): ").strip()
        
        if not key:
            skip = input("Skip OpenAI setup? (y/N): ").lower().strip()
            if skip == 'y':
                return None
            continue
        
        if not key.startswith('sk-'):
            print("❌ OpenAI keys usually start with 'sk-'. Please check your key.")
            retry = input("Try again? (Y/n): ").lower().strip()
            if retry == 'n':
                return None
            continue
        
        # Confirm
        print(f"\nKey preview: {key[:4]}...{key[-4:]}")
        confirm = input("Is this correct? (Y/n): ").lower().strip()
        if confirm != 'n':
            return key


def get_ib_config() -> dict:
    """Prompt for Interactive Brokers configuration"""
    print("\n📌 Interactive Brokers Setup (Optional)")
    print("-" * 40)
    print("IB connection is optional - only needed for downloading market data.\n")
    print("Requirements:")
    print("1. TWS or IB Gateway installed and running")
    print("2. API connections enabled in settings")
    print("3. Socket port configured (4002 for Gateway, 7497 for TWS)\n")
    
    # Check if already configured
    current_host = os.getenv("IB_GATEWAY_HOST")
    if current_host:
        print(f"Current configuration:")
        print(f"  Host: {os.getenv('IB_GATEWAY_HOST', 'localhost')}")
        print(f"  Port: {os.getenv('IB_GATEWAY_PORT', '4002')}")
        print(f"  Client ID: {os.getenv('IB_CLIENT_ID', '1')}")
        update = input("\nUpdate IB configuration? (y/N): ").lower().strip()
        if update != 'y':
            return {}
    
    setup = input("Set up Interactive Brokers connection? (y/N): ").lower().strip()
    if setup != 'y':
        return {}
    
    config = {}
    
    # Host
    host = input("IB Gateway/TWS host (default: localhost): ").strip()
    config['IB_GATEWAY_HOST'] = host or 'localhost'
    
    # Port
    print("\nCommon ports:")
    print("  4002 - IB Gateway (paper trading)")
    print("  4001 - IB Gateway (live trading)")
    print("  7497 - TWS (paper trading)")
    print("  7496 - TWS (live trading)")
    port = input("Port number (default: 4002): ").strip()
    config['IB_GATEWAY_PORT'] = port or '4002'
    
    # Client ID
    client_id = input("Client ID (default: 1): ").strip()
    config['IB_CLIENT_ID'] = client_id or '1'
    
    return config


def main():
    """Main setup function"""
    print_header()
    
    # Initialize API Manager
    api_manager = APIManager()
    
    # Check if .env exists
    if not Path(".env").exists():
        print("📝 Creating new .env file...")
        Path(".env").touch()
        print("✅ Created .env file\n")
    
    # OpenAI setup
    openai_key = get_openai_key()
    if openai_key:
        print("\n🔐 Saving OpenAI API key...")
        if api_manager.set_api_key("OPENAI_API_KEY", openai_key):
            print("✅ OpenAI API key saved successfully")
            
            # Test connection
            print("\n🔍 Testing OpenAI connection...")
            success, message = api_manager.validate_openai_connection()
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
        else:
            print("❌ Failed to save OpenAI API key")
    
    # IB setup
    ib_config = get_ib_config()
    if ib_config:
        print("\n🔐 Saving IB configuration...")
        for key, value in ib_config.items():
            api_manager.set_api_key(key, value)
        print("✅ IB configuration saved")
        
        # Test connection
        print("\n🔍 Testing IB connection...")
        success, message = api_manager.validate_ib_connection()
        if success:
            print(f"✅ {message}")
        else:
            print(f"⚠️  {message}")
            print("   Make sure TWS/IB Gateway is running")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Setup Complete!\n")
    
    print("📋 Current Configuration:")
    configured = api_manager.list_configured_apis()
    for name, value in configured.items():
        print(f"  {name}: {value}")
    
    print("\n🎯 Next Steps:")
    print("1. Run './validate_connections.py' to test all connections")
    print("2. Start the application with 'python start.py'")
    print("\nFor more help, see documentation/setup_guides/api_configuration.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        sys.exit(1)