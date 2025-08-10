#!/usr/bin/env python3
"""
🚀 0DTE Trading Application Launcher

Simple one-command launcher that handles everything:
- API key setup (if needed)
- Connection validation
- Application startup

Usage:
    python launch.py          # Normal launch with checks
    python launch.py --quick  # Skip checks, just run
    python launch.py --setup  # Run setup only
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from configuration.api_manager import APIManager


def print_banner():
    """Print a simple welcome banner"""
    print("\n🎯 0DTE Trading System")
    print("─" * 30)


def check_dependencies():
    """Check if required packages are installed"""
    try:
        import gradio
        import pandas
        import openai
        return True
    except ImportError as e:
        print(f"\n❌ Missing dependencies: {e}")
        print("📦 Install with: pip install -r requirements.txt\n")
        return False


def setup_if_needed():
    """Run setup if API keys are not configured"""
    api_manager = APIManager()
    
    # Check if API key exists
    if not api_manager.get_api_key("OPENAI_API_KEY"):
        print("\n🔧 First time setup needed...")
        print("─" * 30)
        
        # Run setup wizard
        result = subprocess.run([sys.executable, "setup_api_keys.py"])
        if result.returncode != 0:
            print("\n❌ Setup failed. Please run manually: ./setup_api_keys.py")
            return False
        print("\n✅ Setup complete!")
    
    return True


def validate_connections():
    """Quick connection check"""
    api_manager = APIManager()
    
    # Quick validation
    success, message = api_manager.validate_openai_connection()
    
    if success:
        print("✅ API connection verified")
        return True
    else:
        print(f"⚠️  API issue: {message}")
        print("   Run './validate_connections.py --fix' for help")
        return False


def start_application():
    """Start the trading application"""
    print("\n🚀 Starting application...")
    print("📊 Opening at: http://localhost:7866\n")
    
    # Set environment and run
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).parent)
    
    # Run the application
    subprocess.run([sys.executable, "user_interfaces/trading_application.py"], env=env)


def main():
    """Main launcher function"""
    parser = argparse.ArgumentParser(
        description="Launch 0DTE Trading Application",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Skip all checks and launch immediately"
    )
    parser.add_argument(
        "--setup", "-s",
        action="store_true",
        help="Run setup wizard only"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Setup only mode
    if args.setup:
        subprocess.run([sys.executable, "setup_api_keys.py"])
        return
    
    # Quick mode - skip all checks
    if args.quick:
        start_application()
        return
    
    # Normal mode - run checks
    if not check_dependencies():
        sys.exit(1)
    
    if not setup_if_needed():
        sys.exit(1)
    
    # Optional: validate connections (non-blocking)
    validate_connections()
    
    # Start the app
    start_application()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)