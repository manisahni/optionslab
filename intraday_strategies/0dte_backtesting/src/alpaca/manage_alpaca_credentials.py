#!/usr/bin/env python3
"""
Alpaca Credentials Manager - Add, modify, view, and test credentials
"""

import os
import sys
import getpass
from pathlib import Path
from datetime import datetime
import json

class CredentialsManager:
    def __init__(self):
        self.env_file = Path('.env')
        self.credentials = self.load_credentials()
    
    def load_credentials(self):
        """Load existing credentials from .env file"""
        creds = {
            'ALPACA_PAPER_API_KEY': '',
            'ALPACA_PAPER_SECRET_KEY': '',
            'ALPACA_LIVE_API_KEY': '',
            'ALPACA_LIVE_SECRET_KEY': ''
        }
        
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key in creds:
                            creds[key] = value
        
        return creds
    
    def save_credentials(self):
        """Save credentials to .env file"""
        content = f"""# Alpaca API Configuration
# Generated: {datetime.now()}
# IMPORTANT: Keep this file secret!

# Paper Trading
ALPACA_PAPER_API_KEY={self.credentials['ALPACA_PAPER_API_KEY']}
ALPACA_PAPER_SECRET_KEY={self.credentials['ALPACA_PAPER_SECRET_KEY']}
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets

# Live Trading (be careful!)
ALPACA_LIVE_API_KEY={self.credentials['ALPACA_LIVE_API_KEY']}
ALPACA_LIVE_SECRET_KEY={self.credentials['ALPACA_LIVE_SECRET_KEY']}
ALPACA_LIVE_BASE_URL=https://api.alpaca.markets

# Data endpoints
ALPACA_DATA_URL=https://data.alpaca.markets
"""
        
        # Backup existing file
        if self.env_file.exists():
            backup_file = Path(f'.env.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            with open(self.env_file, 'r') as f:
                backup_content = f.read()
            with open(backup_file, 'w') as f:
                f.write(backup_content)
            print(f"✅ Backup created: {backup_file}")
        
        with open(self.env_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Credentials saved to {self.env_file}")
    
    def mask_credential(self, value):
        """Mask credential for display"""
        if not value or len(value) < 10:
            return value
        return f"{value[:8]}...{value[-4:]}"
    
    def display_menu(self):
        """Display main menu"""
        print("\n" + "="*60)
        print("🔐 ALPACA CREDENTIALS MANAGER")
        print("="*60)
        
        print("\n📋 Current Credentials:")
        print("\nPAPER TRADING:")
        api_key = self.credentials['ALPACA_PAPER_API_KEY']
        secret_key = self.credentials['ALPACA_PAPER_SECRET_KEY']
        
        if api_key:
            print(f"  API Key: {self.mask_credential(api_key)}")
        else:
            print(f"  API Key: ❌ Not set")
        
        if secret_key and secret_key != 'YOUR_SECRET_KEY_HERE_FROM_ALPACA_DASHBOARD':
            print(f"  Secret: {self.mask_credential(secret_key)}")
        else:
            print(f"  Secret: ❌ Not set")
        
        print("\nLIVE TRADING:")
        live_api = self.credentials['ALPACA_LIVE_API_KEY']
        live_secret = self.credentials['ALPACA_LIVE_SECRET_KEY']
        
        if live_api:
            print(f"  API Key: {self.mask_credential(live_api)}")
        else:
            print(f"  API Key: Not configured")
        
        if live_secret:
            print(f"  Secret: {self.mask_credential(live_secret)}")
        else:
            print(f"  Secret: Not configured")
        
        print("\n" + "-"*60)
        print("\n🔧 OPTIONS:")
        print("1. Set/Update Paper Trading API Key")
        print("2. Set/Update Paper Trading Secret Key")
        print("3. Set Both Paper Trading Credentials")
        print("4. Set/Update Live Trading Credentials (Advanced)")
        print("5. Test Paper Trading Connection")
        print("6. View Full Credentials (Unmasked)")
        print("7. Export Credentials (JSON)")
        print("8. Import Credentials (JSON)")
        print("9. Clear All Credentials")
        print("0. Exit")
        
        return input("\nSelect option (0-9): ").strip()
    
    def set_paper_api_key(self):
        """Set paper trading API key"""
        print("\n" + "-"*40)
        print("SET PAPER TRADING API KEY")
        print("-"*40)
        
        current = self.credentials['ALPACA_PAPER_API_KEY']
        if current:
            print(f"Current: {self.mask_credential(current)}")
            print("Press Enter to keep current, or enter new key")
        
        api_key = input("\nEnter API Key: ").strip()
        
        if api_key:
            self.credentials['ALPACA_PAPER_API_KEY'] = api_key
            self.save_credentials()
            print("✅ Paper API key updated!")
        elif not current:
            print("❌ No API key provided")
    
    def set_paper_secret_key(self):
        """Set paper trading secret key"""
        print("\n" + "-"*40)
        print("SET PAPER TRADING SECRET KEY")
        print("-"*40)
        
        current = self.credentials['ALPACA_PAPER_SECRET_KEY']
        if current and current != 'YOUR_SECRET_KEY_HERE_FROM_ALPACA_DASHBOARD':
            print(f"Current: {self.mask_credential(current)}")
            print("Press Enter to keep current, or enter new key")
        
        print("\nTo get your secret key:")
        print("1. Go to: https://app.alpaca.markets/paper/dashboard/overview")
        print("2. Click 'View' next to your API key")
        print("3. Copy the secret key")
        
        secret_key = getpass.getpass("\nEnter Secret Key (hidden): ").strip()
        
        if secret_key:
            self.credentials['ALPACA_PAPER_SECRET_KEY'] = secret_key
            self.save_credentials()
            print("✅ Paper secret key updated!")
        elif not current:
            print("❌ No secret key provided")
    
    def set_both_paper(self):
        """Set both paper trading credentials"""
        print("\n" + "-"*40)
        print("SET PAPER TRADING CREDENTIALS")
        print("-"*40)
        
        # API Key
        api_key = input("\n1. Enter API Key (or press Enter for default): ").strip()
        if not api_key:
            api_key = "FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F"
            print(f"   Using default: {self.mask_credential(api_key)}")
        
        # Secret Key
        print("\n2. Enter Secret Key")
        print("   Get it from: https://app.alpaca.markets/paper/dashboard/overview")
        secret_key = getpass.getpass("   Secret Key (hidden): ").strip()
        
        if not secret_key:
            print("❌ Secret key is required!")
            return
        
        # Validate
        if len(api_key) < 20:
            print("❌ API key seems too short")
            return
        
        if len(secret_key) < 20:
            print("❌ Secret key seems too short")
            return
        
        # Save
        self.credentials['ALPACA_PAPER_API_KEY'] = api_key
        self.credentials['ALPACA_PAPER_SECRET_KEY'] = secret_key
        self.save_credentials()
        
        print("\n✅ Both paper trading credentials updated!")
        
        # Offer to test
        test = input("\nTest connection now? (y/n): ").lower()
        if test == 'y':
            self.test_connection()
    
    def set_live_credentials(self):
        """Set live trading credentials"""
        print("\n" + "-"*40)
        print("⚠️  SET LIVE TRADING CREDENTIALS")
        print("-"*40)
        print("\n⚠️  WARNING: Live trading uses real money!")
        
        confirm = input("\nAre you sure you want to configure live trading? (type 'yes'): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return
        
        api_key = input("\nEnter LIVE API Key: ").strip()
        secret_key = getpass.getpass("Enter LIVE Secret Key (hidden): ").strip()
        
        if api_key and secret_key:
            self.credentials['ALPACA_LIVE_API_KEY'] = api_key
            self.credentials['ALPACA_LIVE_SECRET_KEY'] = secret_key
            self.save_credentials()
            print("✅ Live trading credentials updated!")
            print("⚠️  Be very careful with live trading!")
        else:
            print("❌ Both keys required for live trading")
    
    def test_connection(self):
        """Test paper trading connection"""
        print("\n" + "-"*40)
        print("TESTING PAPER TRADING CONNECTION")
        print("-"*40)
        
        api_key = self.credentials['ALPACA_PAPER_API_KEY']
        secret_key = self.credentials['ALPACA_PAPER_SECRET_KEY']
        
        if not api_key or not secret_key:
            print("❌ Paper trading credentials not set!")
            return
        
        try:
            import requests
            
            headers = {
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": secret_key
            }
            
            # Test account endpoint
            response = requests.get(
                "https://paper-api.alpaca.markets/v2/account",
                headers=headers
            )
            
            if response.status_code == 200:
                account = response.json()
                print("\n✅ CONNECTION SUCCESSFUL!")
                print(f"\nAccount Details:")
                print(f"  Account #: {account.get('account_number', 'N/A')}")
                print(f"  Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
                print(f"  Cash: ${float(account.get('cash', 0)):,.2f}")
                print(f"  Equity: ${float(account.get('equity', 0)):,.2f}")
                
                # Check market status
                clock_response = requests.get(
                    "https://paper-api.alpaca.markets/v2/clock",
                    headers=headers
                )
                if clock_response.status_code == 200:
                    clock = clock_response.json()
                    print(f"\nMarket Status:")
                    print(f"  Open: {clock.get('is_open', False)}")
                    if not clock.get('is_open'):
                        print(f"  Next Open: {clock.get('next_open', 'N/A')}")
                
                return True
                
            elif response.status_code == 401:
                print("❌ Authentication failed - check your credentials")
            elif response.status_code == 403:
                print("❌ Access forbidden - secret key may be wrong")
            else:
                print(f"❌ Failed with status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        return False
    
    def view_full_credentials(self):
        """View unmasked credentials"""
        print("\n" + "-"*40)
        print("📋 FULL CREDENTIALS (UNMASKED)")
        print("-"*40)
        
        print("\nPAPER TRADING:")
        print(f"  API Key: {self.credentials['ALPACA_PAPER_API_KEY'] or 'Not set'}")
        print(f"  Secret: {self.credentials['ALPACA_PAPER_SECRET_KEY'] or 'Not set'}")
        
        print("\nLIVE TRADING:")
        print(f"  API Key: {self.credentials['ALPACA_LIVE_API_KEY'] or 'Not set'}")
        print(f"  Secret: {self.credentials['ALPACA_LIVE_SECRET_KEY'] or 'Not set'}")
        
        input("\nPress Enter to continue...")
    
    def export_credentials(self):
        """Export credentials to JSON"""
        print("\n" + "-"*40)
        print("EXPORT CREDENTIALS")
        print("-"*40)
        
        filename = input("Enter filename (default: alpaca_creds.json): ").strip()
        if not filename:
            filename = "alpaca_creds.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        with open(filename, 'w') as f:
            json.dump(self.credentials, f, indent=2)
        
        print(f"✅ Credentials exported to {filename}")
        print("⚠️  Keep this file secure!")
    
    def import_credentials(self):
        """Import credentials from JSON"""
        print("\n" + "-"*40)
        print("IMPORT CREDENTIALS")
        print("-"*40)
        
        filename = input("Enter filename to import: ").strip()
        
        if not Path(filename).exists():
            print(f"❌ File not found: {filename}")
            return
        
        try:
            with open(filename, 'r') as f:
                imported = json.load(f)
            
            # Update credentials
            for key in self.credentials:
                if key in imported:
                    self.credentials[key] = imported[key]
            
            self.save_credentials()
            print(f"✅ Credentials imported from {filename}")
            
        except Exception as e:
            print(f"❌ Error importing: {e}")
    
    def clear_credentials(self):
        """Clear all credentials"""
        print("\n" + "-"*40)
        print("⚠️  CLEAR ALL CREDENTIALS")
        print("-"*40)
        
        confirm = input("\nAre you sure? This will delete all credentials (type 'yes'): ")
        if confirm.lower() == 'yes':
            self.credentials = {
                'ALPACA_PAPER_API_KEY': '',
                'ALPACA_PAPER_SECRET_KEY': '',
                'ALPACA_LIVE_API_KEY': '',
                'ALPACA_LIVE_SECRET_KEY': ''
            }
            self.save_credentials()
            print("✅ All credentials cleared")
        else:
            print("Cancelled")
    
    def run(self):
        """Main loop"""
        while True:
            try:
                choice = self.display_menu()
                
                if choice == '0':
                    print("\n👋 Goodbye!")
                    break
                elif choice == '1':
                    self.set_paper_api_key()
                elif choice == '2':
                    self.set_paper_secret_key()
                elif choice == '3':
                    self.set_both_paper()
                elif choice == '4':
                    self.set_live_credentials()
                elif choice == '5':
                    self.test_connection()
                elif choice == '6':
                    self.view_full_credentials()
                elif choice == '7':
                    self.export_credentials()
                elif choice == '8':
                    self.import_credentials()
                elif choice == '9':
                    self.clear_credentials()
                else:
                    print("❌ Invalid option")
                
                if choice != '0':
                    input("\nPress Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("\nPress Enter to continue...")


def quick_setup():
    """Quick setup for first-time users"""
    print("="*60)
    print("🚀 QUICK ALPACA SETUP")
    print("="*60)
    
    print("\nThis will set up your Alpaca paper trading credentials.")
    print("\nYou'll need:")
    print("1. Your API Key (you provided: FkGJZu...)")
    print("2. Your Secret Key from Alpaca dashboard")
    
    proceed = input("\nContinue with quick setup? (y/n): ").lower()
    if proceed != 'y':
        return False
    
    manager = CredentialsManager()
    
    # API Key
    print("\n" + "-"*40)
    api_key = input("Enter API Key (or press Enter for default): ").strip()
    if not api_key:
        api_key = "FkGJZuDqABc3Ldh0KqhRdn8By7JHNks3N6dacF5F"
        print(f"Using default: {api_key[:10]}...")
    
    # Secret Key
    print("\nGet your secret key from:")
    print("https://app.alpaca.markets/paper/dashboard/overview")
    secret_key = getpass.getpass("\nEnter Secret Key (hidden): ").strip()
    
    if not secret_key:
        print("\n❌ Secret key is required!")
        return False
    
    # Save
    manager.credentials['ALPACA_PAPER_API_KEY'] = api_key
    manager.credentials['ALPACA_PAPER_SECRET_KEY'] = secret_key
    manager.save_credentials()
    
    print("\n✅ Credentials saved!")
    
    # Test
    print("\nTesting connection...")
    if manager.test_connection():
        print("\n" + "="*60)
        print("✅ SETUP COMPLETE!")
        print("="*60)
        print("\nYour Alpaca connection is working!")
        print("\nNext steps:")
        print("1. Run the vega strategy: python alpaca_vega_trader.py --paper")
        print("2. Trade at 3:00-3:30 PM ET for best results")
        return True
    else:
        print("\n❌ Connection test failed")
        print("Run 'python manage_alpaca_credentials.py' to fix")
        return False


if __name__ == "__main__":
    import sys
    
    # Check for quick setup flag
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        if quick_setup():
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Check if this is first run
    env_file = Path('.env')
    if not env_file.exists() or os.path.getsize(env_file) == 0:
        print("🆕 First time setup detected!")
        if quick_setup():
            sys.exit(0)
        print("\nStarting credential manager...")
    
    # Run main manager
    manager = CredentialsManager()
    manager.run()