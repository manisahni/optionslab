#!/usr/bin/env python3
"""
Verify Alpaca Credentials Format
"""

# The credentials you provided
API_KEY = "PKEOVGPWIH9MQT9ZTWV7"
SECRET_KEY = "nlG6wVZ7mxVEddNh5qn238rOekqmunWghOuh5iPo"

print("="*60)
print("ALPACA CREDENTIALS CHECK")
print("="*60)

print("\n📋 Credentials you provided:")
print(f"\nAPI Key: {API_KEY}")
print(f"  Length: {len(API_KEY)} characters")
print(f"  Format: {'✅ Looks valid' if len(API_KEY) == 20 else '⚠️ Unusual length'}")

print(f"\nSecret Key: {SECRET_KEY}")
print(f"  Length: {len(SECRET_KEY)} characters")  
print(f"  Format: {'✅ Looks valid' if len(SECRET_KEY) == 40 else '⚠️ Unusual length'}")

print("\n" + "-"*60)
print("IMPORTANT QUESTIONS:")
print("-"*60)

print("\n1. Where did you get these credentials from?")
print("   [ ] https://app.alpaca.markets/paper/dashboard/overview (Paper Trading)")
print("   [ ] https://app.alpaca.markets/live/dashboard/overview (Live Trading)")
print("   [ ] Somewhere else")

print("\n2. When you view your API keys on Alpaca:")
print("   - Do you see 'Paper Trading' or 'Live Trading' at the top?")
print("   - Is there a toggle to switch between Paper and Live?")

print("\n3. Did you click 'View' or 'Regenerate' to see the secret key?")

print("\n" + "-"*60)
print("NEXT STEPS:")
print("-"*60)

print("\n1. Go to: https://app.alpaca.markets")
print("2. Make sure you're in the PAPER environment (look for toggle)")
print("3. Go to API Keys section")
print("4. Click 'Regenerate' to create new keys")
print("5. Copy both the KEY ID and SECRET KEY")

print("\n⚠️ Make sure you're copying from Paper Trading, not Live!")
print("\nThe credentials should look like:")
print("  Key ID: 20 characters (like PKEOVGPWIH9MQT9ZTWV7)")
print("  Secret: 40 characters (like nlG6wVZ7mxVEddNh5qn238rOekqmunWghOuh5iPo)")

print("\n" + "="*60)
print("TO UPDATE YOUR CREDENTIALS:")
print("="*60)
print("\nRun: python manage_alpaca_credentials.py")
print("Or:  python alpaca_setup.py")
print("\nThese will let you enter new credentials and test them.")