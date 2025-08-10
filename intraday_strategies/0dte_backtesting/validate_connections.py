#!/usr/bin/env python3
"""
Connection Validation Script

Tests all API connections and displays status.
Run this to verify your API keys and connections are working.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from configuration.api_manager import APIManager
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress OpenAI HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


def main():
    """Main function to validate connections"""
    parser = argparse.ArgumentParser(
        description="Validate API connections for 0DTE Trading Application"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix connection issues"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("\n🔌 0DTE Trading Application - Connection Validator\n")
    print("=" * 60)
    
    # Initialize API Manager
    api_manager = APIManager(args.env_file)
    
    # Check if .env file exists
    if not Path(args.env_file).exists():
        print(f"\n❌ No .env file found at '{args.env_file}'")
        print("\n📝 To create one:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your API keys")
        print("   3. Run this script again\n")
        
        if args.fix:
            print("Creating .env file from template...")
            try:
                # Copy .env.example to .env
                import shutil
                shutil.copy(".env.example", args.env_file)
                print(f"✅ Created {args.env_file} from .env.example")
                print("   Please edit it and add your API keys\n")
            except Exception as e:
                print(f"❌ Failed to create .env file: {e}\n")
        
        return 1
    
    # List configured APIs
    print("\n📋 Configured APIs:")
    print("-" * 40)
    
    configured = api_manager.list_configured_apis()
    if configured:
        for name, value in configured.items():
            print(f"  {name}: {value}")
    else:
        print("  No APIs configured")
    
    # Validate connections
    print("\n🔍 Testing Connections:")
    print("-" * 40)
    
    results = api_manager.validate_all_connections()
    
    all_good = True
    for api, (success, message) in results.items():
        if success is None:
            icon = "⚪"
            all_good = False if "openai" in api else all_good  # OpenAI is required
        elif success:
            icon = "✅"
        else:
            icon = "❌"
            all_good = False if "openai" in api else all_good
        
        print(f"\n{icon} {api.replace('_', ' ').title()}")
        print(f"   Status: {message}")
        
        # Provide fix suggestions
        if not success and args.fix:
            if "openai" in api:
                print("\n   💡 To fix:")
                print("   1. Get your OpenAI API key from https://platform.openai.com/api-keys")
                print("   2. Add to .env file: OPENAI_API_KEY=your-key-here")
                print("   3. Run this script again")
            elif "interactive_brokers" in api and success is not None:
                print("\n   💡 To fix:")
                print("   1. Start TWS or IB Gateway")
                print("   2. Enable API connections in TWS/Gateway settings")
                print("   3. Set port to 4002 (Gateway) or 7497 (TWS)")
                print("   4. Run this script again")
    
    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✅ All required connections are working!")
        print("\nYou're ready to run the trading application:")
        print("  python start.py")
    else:
        print("❌ Some connections need attention")
        print("\nPlease fix the issues above before running the application")
        if not args.fix:
            print("\nTip: Run with --fix flag for setup assistance")
    
    print()
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())