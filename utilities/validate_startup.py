#!/usr/bin/env python3
"""
Startup Validation Script for SPY Options Backtester
Performs pre-flight checks to ensure the app can start successfully
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple, List
import socket

class StartupValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []
        
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        min_version = (3, 8)
        current_version = sys.version_info[:2]
        
        if current_version >= min_version:
            self.successes.append(f"✅ Python version {'.'.join(map(str, current_version))} is compatible")
            return True
        else:
            self.errors.append(f"❌ Python version {'.'.join(map(str, current_version))} is too old. Minimum required: {'.'.join(map(str, min_version))}")
            return False
    
    def check_env_file(self) -> bool:
        """Check if .env file exists and is properly configured"""
        env_path = Path(__file__).parent / '.env'
        
        if not env_path.exists():
            self.errors.append("❌ .env file not found. Copy .env.template to .env and configure it.")
            return False
        
        # Check required environment variables
        required_vars = ['DATA_SOURCE', 'SPY_DATA_DIR', 'CLI_BACKTESTER_PATH']
        missing_vars = []
        
        with open(env_path, 'r') as f:
            content = f.read()
            for var in required_vars:
                if f"{var}=" not in content or f"#{var}=" in content:
                    missing_vars.append(var)
        
        if missing_vars:
            self.errors.append(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        self.successes.append("✅ .env file exists and contains required variables")
        return True
    
    def check_data_directory(self) -> bool:
        """Check if data directory exists and contains data"""
        # Load .env file
        env_path = Path(__file__).parent / '.env'
        if not env_path.exists():
            return False
        
        # Parse SPY_DATA_DIR from .env
        spy_data_dir = None
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('SPY_DATA_DIR='):
                    spy_data_dir = line.split('=', 1)[1].strip()
                    break
        
        if not spy_data_dir:
            self.errors.append("❌ SPY_DATA_DIR not configured in .env file")
            return False
        
        # Expand user home directory
        spy_data_dir = os.path.expanduser(spy_data_dir)
        data_path = Path(spy_data_dir)
        
        if not data_path.exists():
            self.errors.append(f"❌ Data directory not found: {spy_data_dir}")
            return False
        
        # Check for parquet files
        parquet_files = list(data_path.glob("*.parquet"))
        if not parquet_files:
            self.errors.append(f"❌ No parquet files found in: {spy_data_dir}")
            return False
        
        self.successes.append(f"✅ Data directory found with {len(parquet_files)} parquet files")
        return True
    
    def check_dependencies(self) -> bool:
        """Check if required Python packages are installed"""
        required_packages = [
            'streamlit',
            'pandas',
            'numpy',
            'plotly',
            'python-dotenv'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                if package == 'python-dotenv':
                    __import__('dotenv')
                else:
                    __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.errors.append(f"❌ Missing required packages: {', '.join(missing_packages)}")
            self.errors.append("   Run: pip install -r requirements.txt")
            return False
        
        self.successes.append("✅ All required packages are installed")
        return True
    
    def check_port_availability(self, port: int = 8520) -> bool:
        """Check if the configured port is available"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                self.warnings.append(f"⚠️  Port {port} is already in use. The app may fail to start.")
                self.warnings.append(f"   Try: lsof -i :{port} to see what's using it")
                return False
            else:
                self.successes.append(f"✅ Port {port} is available")
                return True
        except Exception as e:
            self.warnings.append(f"⚠️  Could not check port availability: {e}")
            return True
    
    def check_streamlit_config(self) -> bool:
        """Check if Streamlit configuration exists"""
        config_path = Path(__file__).parent / '.streamlit' / 'config.toml'
        
        if config_path.exists():
            self.successes.append("✅ Streamlit configuration found")
            return True
        else:
            self.warnings.append("⚠️  Streamlit configuration not found. Using defaults.")
            return True
    
    def check_cli_backtester(self) -> bool:
        """Check if CLI backtester path is valid"""
        env_path = Path(__file__).parent / '.env'
        if not env_path.exists():
            return False
        
        # Parse CLI_BACKTESTER_PATH from .env
        cli_path = None
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('CLI_BACKTESTER_PATH='):
                    cli_path = line.split('=', 1)[1].strip()
                    break
        
        if not cli_path:
            self.warnings.append("⚠️  CLI_BACKTESTER_PATH not configured")
            return True
        
        cli_path = os.path.expanduser(cli_path)
        if Path(cli_path).exists():
            self.successes.append("✅ CLI backtester found")
            return True
        else:
            self.warnings.append(f"⚠️  CLI backtester not found at: {cli_path}")
            return True
    
    def run_all_checks(self) -> bool:
        """Run all validation checks"""
        print("🔍 SPY Options Backtester - Startup Validation")
        print("=" * 50)
        
        checks = [
            self.check_python_version(),
            self.check_env_file(),
            self.check_dependencies(),
            self.check_data_directory(),
            self.check_streamlit_config(),
            self.check_cli_backtester(),
            self.check_port_availability()
        ]
        
        print("\n📋 Validation Results:")
        print("-" * 50)
        
        # Print successes
        for success in self.successes:
            print(success)
        
        # Print warnings
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(warning)
        
        # Print errors
        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(error)
        
        all_passed = all(checks) and not self.errors
        
        print("\n" + "=" * 50)
        if all_passed:
            print("✅ All checks passed! The app should start successfully.")
            print("\nTo start the app, run:")
            print("  streamlit run streamlit_app.py")
        else:
            print("❌ Some checks failed. Please fix the issues above.")
            if self.errors:
                print("\n💡 Quick fixes:")
                if ".env file not found" in str(self.errors):
                    print("  1. Copy .env.template to .env:")
                    print("     cp .env.template .env")
                    print("  2. Edit .env and update the paths")
                if "Missing required packages" in str(self.errors):
                    print("  1. Install dependencies:")
                    print("     pip install -r requirements.txt")
        
        return all_passed

if __name__ == "__main__":
    validator = StartupValidator()
    success = validator.run_all_checks()
    sys.exit(0 if success else 1)